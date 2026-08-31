#!/bin/bash

# 設定錯誤處理
set -e  # 遇到錯誤即停止執行
set -u  # 使用未定義的變量時報錯

# 定義全局變量
cd ..
USER_DIR=$(pwd)
cd dislocation_fix
LAMMPS_PATH=~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100

# 函數：顯示使用方法
show_usage() {
    echo "使用方法：$0"
    echo "這個腳本用於設置和運行分子動力學模擬。"
}

# 函數：驗證輸入
validate_input() {
    local dislocation_type=$1
    local b=$2
    local p=$3
    
    # 驗證位錯類型
    if [[ ! "$dislocation_type" =~ ^(edge|screw)$ ]]; then
        echo "錯誤：位錯類型必須是 edge 或 screw"
        exit 1
    fi
    
    # 驗證 b 和 p 值
    if [[ ! "$b" =~ ^(100|110|111)$ ]] || [[ ! "$p" =~ ^(100|110|111)$ ]]; then
        echo "錯誤：b 和 p 必須是 100、110 或 111"
        exit 1
    fi
}

# 函數：計算原子數量和方向
calculate_orientation() {
    local dislocation_type=$1
    local b=$2
    local p=$3
    local x=$4
    local y=$5
    local z=$6

    case "${dislocation_type}_${b}_${p}" in
        "edge_100_100"|"screw_100_100")
            TOTAL_ATOM=$((x*y*z*2))
            ORIENTATION_STRING="[100] [010] [001]"
            ;;
        "edge_110_100"|"screw_110_100")
            TOTAL_ATOM=$((x*y*z*4))
            ORIENTATION_STRING="[1-10] [110] [001]"
            ;;
        "edge_110_110")
            TOTAL_ATOM=$((x*y*z*4))
            ORIENTATION_STRING="[101] [010] [10-1]"
            ;;
        "edge_100_110")
            TOTAL_ATOM=$((x*y*z*4))
            ORIENTATION_STRING="[100] [01-1] [011]"
            ;;
        "screw_100_110")
            TOTAL_ATOM=$((x*y*z*4))
            ORIENTATION_STRING="[10-1] [010] [101]"
            ;;
        "screw_110_110")
            TOTAL_ATOM=$((x*y*z*4))
            ORIENTATION_STRING="[100] [011] [01-1]"
            ;;
        "edge_111_110")
            TOTAL_ATOM=$((x*y*z*12))
            ORIENTATION_STRING="[111] [2-1-1] [0-11]"
            ;;
        "screw_111_110")
            TOTAL_ATOM=$((x*y*z*12))
            ORIENTATION_STRING="[2-1-1] [111] [0-11]"
            ;;
        *)
            echo "錯誤：無效的方向組合"
            exit 1
            ;;
    esac
}

# 函數：設置模擬目錄
setup_simulation_directory() {
    local session_name=$1
    local temperature=$2
    local structure_path=$3
    local var_num=$4
    local run=$5
    local alloy=$6
    local x_duplication=$7
    local y_duplication=$8
    local duplicated_structure_path=$9
    
    mkdir -p "MD_${temperature}K_relax"
    local dir_name="MD_${temperature}K_relax"
    # 替換配置文件中的變量
    sed -e "s|{{structure_path}}|$structure_path|g" \
        -e "s|{{var_num}}|$var_num|g" \
        -e "s|{{run}}|$run|g" \
        -e "s|{{temperature}}|$temperature|g" \
        -e "s|{{alloy}}|$alloy|g" \
        -e "s|{{user_dir}}|$USER_DIR|g" \
        "in.relax_bulk" > "${dir_name}/in.relax_bulk"
    

    if [ "$DISLOCATION_TYPE" = "edge" ]; then
        sed -e "s|{{structure_path}}|$duplicated_structure_path|g" \
            -e "s|{{x_duplication}}|$x_duplication|g"\
            "in.build_edge" > "${dir_name}/in.build_edge"
    else
        sed -e "s|{{structure_path}}|$duplicated_structure_path|g" \
            -e "s|{{y_duplication}}|$y_duplication|g"\
            "in.build_screw" > "${dir_name}/in.build_screw"
    fi
    
    echo "目錄設置完成：$dir_name"
}


# 主程序開始
# 讀取使用者輸入
read -p "Enter the simulation version: " SIMULATION_VERSION

DEFAULT_ALLOY="NiCoTiZrHf"
read -p "Enter the alloy (default: $DEFAULT_ALLOY): " ALLOY
ALLOY=${ALLOY:-$DEFAULT_ALLOY}

DEFAULT_DISLOCATION_TYPE="edge"
read -p "Enter the dislocation type (edge, screw): " DISLOCATION_TYPE
DISLOCATION_TYPE=${DISLOCATION_TYPE:-$DEFAULT_DISLOCATION_TYPE}

read -p "Enter the b(100, 110, 111): " B
DEFAULT_B=100
B=${B:-$DEFAULT_B}

read -p "Enter the p (100, 110, 111): " P
DEFAULT_P=100
P=${P:-$DEFAULT_P}

DEFAULT_TEMPERATURE="300"
read -p "Enter the temperature(default: $DEFAULT_TEMPERATURE k): " TEMPERATURE
TEMPERATURE=${TEMPERATURE:-$DEFAULT_TEMPERATURE}

read -p "Enter the number of runs: " RUN
read -p "Enter the PE number: " VAR_NUM
read -p "nter the core to use: " CORE

# 驗證輸入
validate_input "$DISLOCATION_TYPE" "$B" "$P"

# 創建模擬版本目錄
mkdir -p "$SIMULATION_VERSION"
cd "$SIMULATION_VERSION" || exit 1

# 讀取複製參數
read -p "Enter the duplication of X, Y, Z: " X Y Z
D_X=$((X * 3))
D_Z=$((Z * 3))
# 計算方向和原子數
calculate_orientation "$DISLOCATION_TYPE" "$B" "$P" "$X" "$Y" "$Z"

# 設置會話名稱和結構名稱
SESSION_NAME="${DISLOCATION_TYPE}_b${B}_p${P}"
STRUCTURE_NAME="${ALLOY}_${DISLOCATION_TYPE}_${TOTAL_ATOM}"

# 創建必要的目錄
mkdir -p structure "$SESSION_NAME"
# 生成結構
if [ -f "POSCAR" ]; then
    rm POSCAR
fi

echo "y" | atomsk --create CsCl 3.0 Ni Ti orient $ORIENTATION_STRING -duplicate $X $Y $Z pos
echo "Renaming POSCAR to ${STRUCTURE_NAME}.pos..."

echo "Copying POSCAR to ${STRUCTURE_NAME}.pos..."
if ! cp -v POSCAR "${STRUCTURE_NAME}.pos"; then
    echo "ERROR: Failed to copy POSCAR"
    exit 1
fi

echo "Removing original POSCAR..."
rm -f POSCAR

echo "Copying ${STRUCTURE_NAME}.pos to structure directory..."
if ! cp -v "${STRUCTURE_NAME}.pos" "structure/${STRUCTURE_NAME}.pos"; then
    echo "ERROR: Failed to copy to structure directory"
    exit 1
fi

echo "Removing original .pos file..."
rm -f "${STRUCTURE_NAME}.pos"

# 確認文件複製是否成功
if [ ! -f "structure/${STRUCTURE_NAME}.pos" ]; then
    echo "ERROR: File not found in structure directory after copy"
    ls -l structure/
    exit 1
fi


# 運行 Python 腳本
echo "Running Python script..."
if ! python "$USER_DIR/HEA_gen.py" "$STRUCTURE_NAME" "$TOTAL_ATOM"; then
    echo "ERROR: Python script execution failed"
    exit 1
fi

echo "Copying ${STRUCTURE_NAME}.lmp to structure directory..."
echo "1" | atomsk "${STRUCTURE_NAME}.lmp" -duplicate 3 1 3 "duplicated_${STRUCTURE_NAME}.lmp"
if ! cp -v "${STRUCTURE_NAME}.lmp" "structure/${STRUCTURE_NAME}.lmp"; then
    echo "ERROR: Failed to copy to structure directory"
    exit 1
fi
if ! cp -v "duplicated_${STRUCTURE_NAME}.lmp" "structure/duplicated_${STRUCTURE_NAME}.lmp"; then
    echo "ERROR: Failed to copy the duplicated file to structure directory"
    exit 1
fi

echo "Removing original .lmp file..."
rm -f "${STRUCTURE_NAME}.lmp"
rm -f "duplicated_${STRUCTURE_NAME}.lmp"

# 確認文件複製是否成功
if [ ! -f "structure/${STRUCTURE_NAME}.lmp" ]; then
    echo "ERROR: File not found in structure directory after copy"
    ls -l structure/
    exit 1
fi

# 清理和設置
cd structure
rm -f "$STRUCTURE_NAME.pos"
cd ..

echo "結構生成完成並移動到 structure/ 目錄"

# 進入會話目錄
cd "$SESSION_NAME" || exit 1

# 複製必要文件
for file in build_slab.sh build_slab_ref.sh in.build_slab in.relax_bulk in.relax_slab; do
    if [ -f "$USER_DIR/dislocation_fix/$file" ]; then
        echo "copy $file"
        cp "$USER_DIR/dislocation_fix/$file" .
    fi
done
if [ "$DISLOCATION_TYPE" = "edge" ]; then
    file="in.build_edge"
else
    file="in.build_screw"
fi

if [ -f "$USER_DIR/dislocation_fix/build_dislocation_in_template/$SESSION_NAME/$file" ]; then
    echo "copy different build dislocation input file"
    cp "$USER_DIR/dislocation_fix/build_dislocation_in_template/$SESSION_NAME/$file" .
fi

# 根據主機名執行不同的操作
case "$(hostname)" in
   "amd01")
       # AMD01 特定操作
       RELAX_DIR="MD_${TEMPERATURE}K_relax"
       
       if [ ! -f "$RELAX_DIR/after_relax_bulk.data" ] ; then
           setup_simulation_directory "$SESSION_NAME" "$TEMPERATURE" "../../structure/$STRUCTURE_NAME.lmp" "$VAR_NUM" "$RUN" "$ALLOY" "$D_X" "$Y" "../../structure/duplicated_${STRUCTURE_NAME}.lmp"
           cd "MD_${TEMPERATURE}K_relax" || exit 1
           
           nohup mpirun -np $CORE $LAMMPS_PATH -in in.relax_bulk > STDOUT &
           ps aux | grep mpirun
           
           if [ "$DISLOCATION_TYPE" = "edge" ]; then
               echo "-------------------build edge----------------------"
               mpirun -np 1 $LAMMPS_PATH -in in.build_edge
               echo "check the edge structure"
           else
               echo "-------------------build screw----------------------"
               mpirun -np 1 $LAMMPS_PATH -in in.build_screw
               echo "check the screw structure"
           fi
       else
           relax_mode="md"
           current_path=$(pwd)
           if [ "$DISLOCATION_TYPE" = "edge" ]; then
               input_file="$RELAX_DIR/HEA_init_edge.data"

           else
               input_file="$RELAX_DIR/HEA_init_screw.data"

           fi
           ref_input_file="../structure/duplicated_$STRUCTURE_NAME.lmp"
           dir_name="${relax_mode}_${TEMPERATURE}K_slip"
           ref_dir_name="${relax_mode}_300K_slip_ref"

           mkdir -p ${dir_name}
           mkdir -p ${ref_dir_name}
           relax_file="$RELAX_DIR/after_relax_bulk.data"
           lx=$(sed -n "6,6p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')
           ly=$(sed -n "7,7p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')
           lz=$(sed -n "8,8p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')
           d_lx=$(echo "$lx * 3" | bc)
           d_lz=$(echo "$lz * 3" | bc)           
           echo "------------slab-----------"
           mpirun -np 1 $LAMMPS_PATH -var input_file $input_file -var newlx $d_lx -var newly $ly -var newlz $d_lz -in in.build_slab
           cp tmp_slab.data ${dir_name}/init_slab.data
           sed  -e "s/currtemp/$TEMPERATURE/g" \
                -e "s|{{var_num}}|$VAR_NUM|g" \
                -e "s|{{run}}|$RUN|g" \
                -e "s|{{temperature}}|$TEMPERATURE|g" \
                -e "s|{{user_dir}}|$USER_DIR|g" \
                "in.relax_slab" > "${dir_name}/in.relax_slab"
           cd ${dir_name}
           nohup mpirun -np $CORE $LAMMPS_PATH -in in.relax_slab > STDOUT &
           ps aux | grep mpirun
           echo "------------ref slab-----------"
           cd ..
           mpirun -np 1 $LAMMPS_PATH -var input_file $ref_input_file -var newlx $d_lx -var newly $ly -var newlz $d_lz -in in.build_slab
           cp tmp_slab.data ${ref_dir_name}/init_slab.data
           sed  -e "s/currtemp/$TEMPERATURE/g" \
                -e "s|{{var_num}}|$VAR_NUM|g" \
                -e "s|{{run}}|$RUN|g" \
                -e "s|{{temperature}}|$TEMPERATURE|g" \
                -e "s|{{user_dir}}|$USER_DIR|g" \
                "in.relax_slab" > "${ref_dir_name}/in.relax_slab"
           cd ${ref_dir_name}
           nohup mpirun -np $CORE $LAMMPS_PATH -in in.relax_slab > STDOUT &
           ps aux | grep mpirun
           echo "-------------------------------"
       fi
       ;;
    "gpu04")
       # GPU04 特定操作
       RELAX_DIR="MD_${TEMPERATURE}K_relax"
       
       if [ ! -f "$RELAX_DIR/after_relax_bulk.data" ]; then
           read -p "Enter the number of core to use (gpu): " GPU_CORE
           export CUDA_VISIBLE_DEVICES=$GPU_CORE
           setup_simulation_directory "$SESSION_NAME" "$TEMPERATURE" "../../structure/$STRUCTURE_NAME.lmp" "$VAR_NUM" "$RUN" "$ALLOY" "$D_X" "$Y" "../../structure/duplicated_${STRUCTURE_NAME}.lmp"
           cd "MD_${TEMPERATURE}K_relax" || exit 1
           nohup mpirun -np 1 -cpu-set $GPU_CORE $LAMMPS_PATH -k on g 1 -sf kk -pk kokkos newton on neigh half -in in.relax_bulk > STDOUT &
           ps aux | grep mpirun

           if [ "$DISLOCATION_TYPE" = "edge" ]; then
               echo "-------------------build edge----------------------"
               mpirun -np 1 $LAMMPS_PATH -in in.build_edge
               echo "check the edge structure"
           else
               echo "-------------------build screw----------------------"
               mpirun -np 1 $LAMMPS_PATH -in in.build_screw
               echo "check the screw structure"
           fi
       else
           read -p "Enter the number of core to use (gpu): " GPU_CORE
           export CUDA_VISIBLE_DEVICES=$GPU_CORE
           relax_mode="md"
           if [ "$DISLOCATION_TYPE" = "edge" ]; then
               input_file="$RELAX_DIR/HEA_init_edge.data"

           else
               input_file="$RELAX_DIR/HEA_init_screw.data"

           fi
           ref_input_file="../structure/duplicated_$STRUCTURE_NAME.lmp"
           dir_name="${relax_mode}_${TEMPERATURE}K_slip"
           ref_dir_name="${relax_mode}_300K_slip_ref"

           mkdir -p ${dir_name}
           mkdir -p ${ref_dir_name}
           
          

           relax_file="$RELAX_DIR/after_relax_bulk.data"
           lx=$(sed -n "6,6p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')
           ly=$(sed -n "7,7p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')
           lz=$(sed -n "8,8p" $relax_file | awk '{print $2}'| awk '{printf("%f",$0)}')
           d_lx=$(echo "$lx * 3" | bc)
           d_lz=$(echo "$lz * 3" | bc)  
           
            
        #    echo "------------slab-----------"
        #    mpirun -np 1 $LAMMPS_PATH -var input_file $input_file -var newlx $d_lx -var newly $ly -var newlz $d_lz -in in.build_slab
        #    cp tmp_slab.data ${dir_name}/init_slab.data
        #    sed  -e "s/currtemp/$TEMPERATURE/g" \
        #         -e "s|{{var_num}}|$VAR_NUM|g" \
        #         -e "s|{{run}}|$RUN|g" \
        #         -e "s|{{temperature}}|$TEMPERATURE|g" \
        #         -e "s|{{user_dir}}|$USER_DIR|g" \
        #         "in.relax_slab" > "${dir_name}/in.relax_slab"
        #    cd ${dir_name}
        #    nohup mpirun -np 1 -cpu-set $GPU_CORE $LAMMPS_PATH -k on g 1 -sf kk -pk kokkos newton on neigh half \
        #        -in in.relax_slab > STDOUT &
        #    ps aux | grep mpirun
           echo "------------ref slab-----------"
           mpirun -np 1 $LAMMPS_PATH -var input_file $ref_input_file -var newlx $d_lx -var newly $ly -var newlz $d_lz -in in.build_slab
           cp tmp_slab.data ${ref_dir_name}/init_slab.data
           sed  -e "s/currtemp/$TEMPERATURE/g" \
                -e "s|{{var_num}}|$VAR_NUM|g" \
                -e "s|{{run}}|$RUN|g" \
                -e "s|{{temperature}}|$TEMPERATURE|g" \
                -e "s|{{user_dir}}|$USER_DIR|g" \
                "in.relax_slab" > "${ref_dir_name}/in.relax_slab"
           cd ${ref_dir_name}
           nohup mpirun -np 1 -cpu-set $GPU_CORE $LAMMPS_PATH -k on g 1 -sf kk -pk kokkos newton on neigh half \
               -in in.relax_slab > STDOUT &
           ps aux | grep mpirun
           echo "-------------------------------"
       fi
       ;;
   *)
       echo "不支持的主機名：$(hostname)"
       exit 1
       ;;
esac

exit 0
