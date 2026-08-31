#!/bin/bash
#
# NEB minimize pipeline launcher
# 功能：
# 1. 掃描研究案例資料夾底下的所有 neb_*.data
# 2. 每個 neb_* 建立 minimize/neb_* 子資料夾
# 3. 在子資料夾內生成 in.min_post_neb 並執行 minimize
#

current_dir=$(pwd)

#------------------------------------
# 可修改設定區
#------------------------------------
LAMMPS_BIN=~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100
../potentials/HEA_v3_trial3.snapcoeff
../potentials/HEA_v3_trial3.snapparam
TEMPLATE_PATH=$current_dir/templates/in.min.post_neb
MAX_PROCESSES=8   # 同時允許的最大 LAMMPS 工作數量
#------------------------------------

task_wait_list=()

#------------------------------------
# GPU 狀態檢查
#------------------------------------
find_available_gpu() {
    echo "[find_available_gpu] 檢查 GPU 狀態" >&2
    used_gpus=$(nvidia-smi | awk '/Processes:/{flag=1} /\+--/{flag=0} flag && !/===/{print $2}' | grep -E '^[0-9]+$')
    total_gpus=$(nvidia-smi --list-gpus | wc -l)
    echo "[find_available_gpu] 已使用 $used_gpus 個 GPU" >&2
    echo "[find_available_gpu] 總共有 $total_gpus 個 GPU" >&2
    available_gpu=""
    min_memory=32768
    for gpu_id in $(seq 0 $((total_gpus - 1))); do
        if ! echo "$used_gpus" | grep -q "^$gpu_id$"; then
            memory_info=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i $gpu_id)
            memory_used=$(echo "$memory_info" | tr -d ' ')
            if [ "$memory_used" -lt "$min_memory" ]; then
                min_memory="$memory_used"
                available_gpu="$gpu_id"
            fi
        fi
    done
    echo "$available_gpu"
}

check_max_processes() {
    local current_processes
    current_processes=$(pgrep "lmp_kokkos_cuda_v100" | wc -l)
    echo "[check] 目前有 $current_processes 個 LAMMPS 工作"
    echo "[check] 最大工作數量：$MAX_PROCESSES"
    echo "[check] 是否達到最大工作數量：$([ "$current_processes" -ge "$MAX_PROCESSES" ] && echo "是" || echo "否")"
    if [ "$current_processes" -ge "$MAX_PROCESSES" ]; then
        return 1
        echo "[check] 達到最大工作數量，等待中..."
    else
        return 0
        echo "[check] 還有空閒工作數量，可以繼續執行..."
    fi
}


#------------------------------------
# 掃描所有 neb_*.data 並加入任務列表
#------------------------------------
queue_neb_minimize_targets() {
    local base_dir="${1:-$PWD}"
    task_wait_list=()
    echo "[queue] 掃描目錄：$base_dir"

    while IFS= read -r -d '' data_file; do
        echo "[queue] 找到檔案：$data_file"
        local dir_path file_name neb_name
        dir_path="$(dirname "$data_file")"
        file_name="$(basename "$data_file")"
        neb_name="${file_name%.data}"
        task_wait_list+=("${dir_path}|${neb_name}")
    done < <(find "$base_dir" \
                -type d \( -name "edge_*" -o -name "screw_*" \) -prune \
                -exec find {} -type f -name 'neb_*.data' -print0 \;)

    echo "[queue] 已加入 ${#task_wait_list[@]} 個任務"
}

#------------------------------------
# 內部工具：讓 sed 安全處理字串
#------------------------------------
__sed_escape() {
    printf '%s' "$1" | sed -e 's/[&]/\\&/g'
}

#------------------------------------
# 執行單一任務
#------------------------------------
launch_neb_minimize_task() {
    local task_entry="$1"
    local gpu_id="${2:-}"
    local snap_coeff="${3:-$SNAP_COEFF}"
    local snap_param="${4:-$SNAP_PARAM}"
    local template_path="${5:-$TEMPLATE_PATH}"

    if [[ -z "$task_entry" ]]; then
        echo "[launch] 請提供任務字串 'dir|neb_name'"
        return 1
    fi

    local folder_name neb_name
    IFS='|' read -r folder_name neb_name <<< "$task_entry"

    [[ -d "$folder_name" ]] || { echo "[launch] 目錄不存在：$folder_name"; return 1; }
    [[ -f "$folder_name/${neb_name}.data" ]] || { echo "[launch] 找不到：$folder_name/${neb_name}.data"; return 1; }
    [[ -f "$snap_coeff" && -f "$snap_param" ]] || {
        echo "[launch] SNAP 檔缺失："; echo "  coeff=$snap_coeff"; echo "  param=$snap_param"; return 1; }
    [[ -f "$template_path" ]] || { echo "[launch] 模板不存在：$template_path"; return 1; }
    # 選 GPU
    printf "[launch] 選 GPU：$gpu_id\n"
    if [[ -z "$gpu_id" ]]; then
        echo "[launch] 選 GPU"
        gpu_id="$(find_available_gpu)"
        [[ -n "$gpu_id" ]] || { echo "[launch] 找不到可用 GPU"; return 1; }
    fi

    # 建立 minimize/neb_* 目錄
    local run_dir="$folder_name/minimize/$neb_name"
    mkdir -p "$run_dir"
    ln -sf "${folder_name}/${neb_name}.data" "$run_dir/${neb_name}.data"

    # 渲染模板
    local out_input="$run_dir/in.min_post_neb"
    local esc_neb esc_coeff esc_param
    esc_neb="$(__sed_escape "$neb_name")"
    esc_coeff="$(__sed_escape "$snap_coeff")"
    esc_param="$(__sed_escape "$snap_param")"

    sed -e "s|\${neb_name}|${esc_neb}|g" \
        -e "s|\${snap_coeff}|${esc_coeff}|g" \
        -e "s|\${snap_param}|${esc_param}|g" \
        "$template_path" > "$out_input"

    # 執行
    echo "[launch] 執行：$run_dir (CUDA_VISIBLE_DEVICES=$gpu_id, cpu-set=$gpu_id)"
    (
        cd "$run_dir" || exit 1
        export CUDA_VISIBLE_DEVICES="$gpu_id"
        # 乾淨一下舊檔
        : > STDOUT_min_post_neb
        : > STDERR_min_post_neb

        nohup mpirun -np 1 -cpu-set "$gpu_id" \
            "$LAMMPS_BIN" -k on g 1 -sf kk -pk kokkos newton on neigh half -log none \
            -in in.min_post_neb > STDOUT_min_post_neb 2> STDERR_min_post_neb &

        echo $! > .mpirun.pid
    )
    if [[ -f "$run_dir/.mpirun.pid" ]]; then
        pid=$(cat "$run_dir/.mpirun.pid")
        if kill -0 "$pid" 2>/dev/null; then
            echo "[launch] 已提交 PID=$pid 到背景"
        else
            echo "[launch] 投遞後立刻結束，請查看："
            echo "         $run_dir/STDERR_min_post_neb"
            echo "         $run_dir/STDOUT_min_post_neb"
        fi
    else
        echo "[launch] 沒寫出 .mpirun.pid，疑似 nohup/mpirun 未啟動"
    fi

}

#------------------------------------
# 主流程：掃描並依序啟動任務
#------------------------------------
main() {
    local base_dir="${1:-$PWD}"
    queue_neb_minimize_targets "$base_dir"

    for task in "${task_wait_list[@]}"; do
        # 等待可用 GPU / Process slot
        while ! check_max_processes; do
            sleep 5
        done
        echo "[main] 等待可用 GPU / Process slot 完成"
        launch_neb_minimize_task "$task"
        sleep 3  # 避免同時太多任務搶 GPU
    done

    echo "[main] 所有任務已提交。"
}

main "$@"
