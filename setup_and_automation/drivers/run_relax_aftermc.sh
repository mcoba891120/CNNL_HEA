#!/bin/bash
# 本腳本會依序處理兩個基底目錄下各個 edge 資料夾內的 emin.data，
# 使用 atomsk 以 -duplicate 2 1 1 產生 stretched.lmp，
# 並針對 300K、600K、900K 三種溫度建立 relax 模擬的 session，
# 每個 session 的命名格式為：
#   v3_trial3_9792_${TEMP}k_${BASE_ID}_${EDGE_ID}
# 其中 BASE_ID 由基底目錄 (例如 MC300k) 轉成小寫，
# EDGE_ID 則是將 edge 資料夾名稱 (例如 edge_b100_p110) 去除 "edge_" 與底線變成 b100p110。
#
# 最後，每個 session 目錄都會移動到 relaxation/NiCoTiZrHf_110 下進行 relax 模擬，
# 並在處理完該 edge 後刪除 mc_folder 裡的 stretched.lmp。

############################
# 參數與目錄設定
############################

# 基底目錄列表
BASE_DIRS=(
  "monte_carlo/dislocation_fix/v3_trail3_MC300k"
  "monte_carlo/dislocation_fix/v3_trail3_MC1273k"
)

# 每個基底目錄下的 edge 資料夾名稱
EDGE_DIRS=("edge_b100_p110" "edge_b110_p110")

# relax 模擬溫度列表（單位 K）
TEMPERATURES=(300 600 900)

# 固定總原子數（duplicate 後必須為 9792，因此 emin.data 應包含 4896 個原子）
TOTAL_ATOM=9792
VAR_NUM=3
RUN=100000

# relax 模擬輸入模板檔（必須放在此腳本目錄中）
TEMPLATE_FILE="in.relax.var.NiCoTiZrHf"
if [ ! -f "$TEMPLATE_FILE" ]; then
  echo "找不到模板檔案 $TEMPLATE_FILE，請確認後再執行。"
  exit 1
fi

# 目前使用者工作目錄（模板檔與本腳本所在目錄）
USER_DIR=$(pwd)

# relax 模擬最終 session 目錄的基底
RELAX_BASE="relaxation/NiCoTiZrHf_110"
mkdir -p "$RELAX_BASE"

# 根據目前所在主機預先取得所需參數（例如核心數或 GPU 編號）
HOSTNAME=$(hostname)
if [ "$HOSTNAME" = "amd01" ]; then
  read -p "請輸入在 amd01 使用的核心數: " CORE
elif [ "$HOSTNAME" = "gpu04" ]; then
  read -p "請輸入在 gpu04 使用的 GPU 編號: " NUM_GPU
elif [ "$HOSTNAME" = "gpu03" ]; then
  read -p "請輸入在 gpu03 使用的 GPU 編號: " NUM_GPU
fi

############################
# 主程式：遍歷各個基底與 edge 目錄
############################

for BASE in "${BASE_DIRS[@]}"; do
  if [ ! -d "$BASE" ]; then
    echo "基底目錄 $BASE 不存在，跳過。"
    continue
  fi

  # 例如：v3_trail3_MC300k 取最後一段 "MC300k"，轉小寫成 "mc300k"
  BASE_NAME=$(basename "$BASE")
  BASE_ID=$(echo "$BASE_NAME" | awk -F'_' '{print $NF}' | tr '[:upper:]' '[:lower:]')

  for EDGE in "${EDGE_DIRS[@]}"; do
    EDGE_PATH="$BASE/$EDGE"
    if [ ! -d "$EDGE_PATH" ]; then
      echo "edge 目錄 $EDGE_PATH 不存在，跳過。"
      continue
    fi

    MC_FOLDER="$EDGE_PATH/mc_folder"
    if [ ! -d "$MC_FOLDER" ]; then
      echo "在 $EDGE_PATH 中找不到 mc_folder，跳過。"
      continue
    fi

    EMIN_FILE="$MC_FOLDER/emin.data"
    if [ ! -f "$EMIN_FILE" ]; then
      echo "在 $MC_FOLDER 中找不到 emin.data，跳過。"
      continue
    fi

    echo "處理檔案： $EMIN_FILE"
    # 使用 atomsk 以 -duplicate 2 1 1 產生 stretched.lmp
    STRETCHED_FILE="$MC_FOLDER/stretched.lmp"
    atomsk "$EMIN_FILE" -duplicate 2 1 1 "$STRETCHED_FILE"
    if [ $? -ne 0 ]; then
      echo "atomsk 對 $EMIN_FILE 進行 duplicate 失敗，跳過此目錄。"
      continue
    fi
    echo "已產生拉伸後檔案： $STRETCHED_FILE"

    # 處理 edge 識別碼：例如 edge_b100_p110 → 去除 "edge_" 並移除底線，變為 b100p110
    EDGE_ID=$(echo "$EDGE" | sed 's/^edge_//' | sed 's/_//g')

    # 針對每個溫度建立 relax session
    for TEMP in "${TEMPERATURES[@]}"; do
      # session 名稱格式：v3_trial3_9792_${TEMP}k_${BASE_ID}_${EDGE_ID}
      SESSION_NAME="v3_trial3_${TOTAL_ATOM}_${TEMP}k_${BASE_ID}_${EDGE_ID}"
      # 注意：這裡將 session 目錄建立在 RELAX_BASE 底下
      SESSION_DIR="$RELAX_BASE/$SESSION_NAME"
      mkdir -p "$SESSION_DIR/structure"

      # 複製 stretched.lmp 至 session 目錄的 structure 子目錄中
      cp "$STRETCHED_FILE" "$SESSION_DIR/structure/"
      STRUCTURE_PATH="$SESSION_DIR/structure/$(basename "$STRETCHED_FILE")"

      # 從模板檔產生 relax input 檔，替換佔位符
      INPUT_FILE="$SESSION_DIR/in.relax.${SESSION_NAME}"
      sed -e "s|{{structure_path}}|$STRUCTURE_PATH|g" \
          -e "s|{{temperature}}|$TEMP|g" \
          -e "s|{{session_name}}|$SESSION_NAME|g" \
          -e "s|{{user_dir}}|$USER_DIR|g" \
          -e "s|{{var_num}}|$VAR_NUM|g"\
          -e "s|{{run}}|$RUN|g"\
          "$TEMPLATE_FILE" > "$INPUT_FILE"
      echo "已建立 relax input 檔： $INPUT_FILE"

      ############################
      # 啟動 relax 模擬：根據主機自動呼叫 mpirun
      ############################
      pushd "$SESSION_DIR" > /dev/null

      if [ "$HOSTNAME" = "amd01" ]; then
          nohup mpirun -np "$CORE" /home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 \
              -in "$(basename "$INPUT_FILE")" > STDOUT &
          echo "在 amd01 以 $CORE 核心啟動 relax 模擬： $SESSION_NAME"
          echo "-----------------------------------------"
          echo "Info of this session: "
          ps aux | grep "$(basename "$INPUT_FILE")"
          echo "-----------------------------------------"
          echo "Info of all session: "
          ps aux | grep mpirun
      elif [ "$HOSTNAME" = "sophon" ]; then
          echo "在 sophon 請 ssh 至 amd01 並執行以下指令以啟動 relax 模擬 (目錄： $SESSION_DIR)："
          echo "nohup mpirun -np \$CORE /home/cnnltmp02/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 -in $(basename "$INPUT_FILE") > STDOUT &"
      elif [ "$HOSTNAME" = "gpu04" ]; then
          nohup mpirun -np 1 -cpu-set "$NUM_GPU" ~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100 \
              -k on g 1 -sf kk -pk kokkos newton on neigh half \
              -in "$(basename "$INPUT_FILE")" > STDOUT &
          echo "在 gpu04 使用 GPU $NUM_GPU 啟動 relax 模擬： $SESSION_NAME"
      elif [ "$HOSTNAME" = "gpu03" ]; then
          nohup mpirun -np 1 -cpu-set "$NUM_GPU" /home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_p100 \
              -k on g 1 -sf kk -pk kokkos newton on neigh half \
              -in "$(basename "$INPUT_FILE")" > STDOUT &
          echo "在 gpu03 使用 GPU $NUM_GPU 啟動 relax 模擬： $SESSION_NAME"
      else
          echo "未知主機 ($HOSTNAME)。請手動至 $SESSION_DIR 啟動 relax 模擬。"
      fi

      popd > /dev/null
    done  # 結束對各溫度的處理

    # 刪除 mc_folder 中的 stretched.lmp（避免重複使用）
    rm -f "$STRETCHED_FILE"
    echo "已刪除 $MC_FOLDER 中的 stretched.lmp"

  done  # 結束對 edge 目錄的處理

done  # 結束對基底目錄的處理

exit 0
