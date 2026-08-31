#!/bin/bash
# --------------------------------------------------
# 功能：
#   在當前資料夾底下建立 minimize/
#   把所有 neb_*.data 各自放進 minimize/neb_* 資料夾
#   產生 in.min_post_neb 並加入執行佇列
# --------------------------------------------------

set -euo pipefail

current_dir=$(pwd)
minimize_dir="$current_dir/minimize"
LAMMPS_BIN=~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100
SNAP_COEFF="../../../potentials/HEA_v3_trial3.snapcoeff"
SNAP_PARAM="../../../potentials/HEA_v3_trial3.snapparam"
TEMPLATE_PATH="$current_dir/../../templates/in.min.post_neb"
MAX_PROCESSES=8

#---------------------------------------------------
# 內部工具
#---------------------------------------------------
find_available_gpu() {
    echo "[find_available_gpu] 檢查 GPU 狀態" >&2
    csv=$(nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader,nounits 2>/dev/null || true)
    [[ -z "$csv" ]] && { echo 0; return; }

    local best_gpu="" best_mem=99999999
    while IFS=',' read -r idx mem util; do
        idx="${idx//[[:space:]]/}"
        mem="${mem//[[:space:]]/}"
        util="${util//[[:space:]]/}"
        [[ "$util" =~ ^[0-9]+$ ]] || util=100
        [[ "$mem"  =~ ^[0-9]+$ ]] || mem=99999999
        if (( util < 5 )) && (( mem < best_mem )); then
            best_mem="$mem"
            best_gpu="$idx"
        fi
    done <<< "$csv"

    [[ -n "$best_gpu" ]] || best_gpu=0
    echo "$best_gpu"
}

check_max_processes() {
    local alive
    alive=$(pgrep -f "lmp_kokkos_cuda_v100" | wc -l)
    echo "[check] 現在有 $alive 個 LAMMPS 工作（上限 $MAX_PROCESSES）"
    (( alive < MAX_PROCESSES ))
}

__sed_escape() {
    printf '%s' "$1" | sed -e 's/[&]/\\&/g'
}

launch_minimize_task() {
    local neb_file="$1"
    local neb_name
    neb_name=$(basename "$neb_file" .data)
    local neb_dir="$minimize_dir/$neb_name"
    mkdir -p "$neb_dir"

    ln -sf "$neb_file" "$neb_dir/$neb_name.data"

    local esc_neb esc_coeff esc_param
    esc_neb="$(__sed_escape "$neb_name")"
    esc_coeff="$(__sed_escape "$SNAP_COEFF")"
    esc_param="$(__sed_escape "$SNAP_PARAM")"

    sed -e "s|\${neb_name}|${esc_neb}|g" \
        -e "s|\${snap_coeff}|${esc_coeff}|g" \
        -e "s|\${snap_param}|${esc_param}|g" \
        "$TEMPLATE_PATH" > "$neb_dir/in.min_post_neb"

    local gpu_id
    gpu_id="$(find_available_gpu)"
    echo "[launch] 執行 $neb_name (GPU=$gpu_id)"
    (
        cd "$neb_dir"
        export CUDA_VISIBLE_DEVICES="$gpu_id"
        nohup mpirun -np 1 -cpu-set "$gpu_id" \
            "$LAMMPS_BIN" -k on g 1 -sf kk -pk kokkos newton on neigh half -log none \
            -in in.min_post_neb > STDOUT_min_post_neb 2>&1 &
        echo $! > .pid
    )
}

#---------------------------------------------------
# 主流程
#---------------------------------------------------
echo "[main] 當前目錄：$current_dir"
mkdir -p "$minimize_dir"

mapfile -t neb_files < <(find "$current_dir" -maxdepth 1 -type f -name "neb_*.data" | sort)
echo "[main] 找到 ${#neb_files[@]} 個 neb_*.data 檔案"

for neb_file in "${neb_files[@]}"; do
    while ! check_max_processes; do
        sleep 5
    done
    launch_minimize_task "$neb_file"
    sleep 2
done

echo "[main] 所有任務已提交。"
