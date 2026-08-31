#!/usr/bin/env python3
import os
import re
import csv
from pathlib import Path
import matplotlib.pyplot as plt

# -------- config / helpers --------
BASE = Path.cwd()
MIN_DIR = BASE / "minimize"
NEB_DIR_GLOB = "neb_*"
STDOUT_NAME = "STDOUT_min_post_neb"
CSV_OUT = MIN_DIR / "energy_summary.csv"
PNG_OUT = MIN_DIR / "energy_per_length.png"

def detect_mode_from_path(path: Path) -> str:
    """Return 'edge' or 'screw' by scanning path components."""
    parts = [p.lower() for p in path.parts]
    for p in parts[::-1]:
        if p.startswith("edge_"):
            return "edge"
        if p.startswith("screw_"):
            return "screw"
    # fallback: prefer edge if both unknown
    return "edge"

MODE = detect_mode_from_path(BASE)  # 'edge' => divide by yhi; 'screw' => divide by xhi

def parse_stdout(stdout_path: Path):
    """
    Return dict with: neb_name, xhi, yhi, zhi, e_final
    """
    text = stdout_path.read_text(errors="ignore")
    # orthogonal box line
    m_box = re.search(r"orthogonal box = \(\s*0\s+0\s+0\s*\)\s+to\s+\(\s*([0-9eE+.\-]+)\s+([0-9eE+.\-]+)\s+([0-9eE+.\-]+)\s*\)", text)
    if not m_box:
        raise ValueError(f"Cannot find 'orthogonal box' in {stdout_path}")
    xhi = float(m_box.group(1))
    yhi = float(m_box.group(2))
    zhi = float(m_box.group(3))

    # find 'Energy initial, next-to-last, final =' then the next line with three numbers
    m_energy_block = re.search(r"Energy initial, next-to-last, final\s*=\s*\n([^\n]+)", text)
    if not m_energy_block:
        raise ValueError(f"Cannot find final energy block in {stdout_path}")
    nums_line = m_energy_block.group(1)
    # numbers may be separated by spaces; take third as final
    nums = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", nums_line)
    if len(nums) < 3:
        raise ValueError(f"Cannot parse three energies in {stdout_path}: {nums_line}")
    e_final = float(nums[2])

    return xhi, yhi, zhi, e_final

def neb_index_from_name(neb_name: str) -> int:
    m = re.search(r"neb_(\d+)", neb_name)
    return int(m.group(1)) if m else 0

# -------- main --------
def main():
    if not MIN_DIR.exists():
        print(f"[ERR] {MIN_DIR} 不存在。請在含有 minimize/ 的 sample1 目錄執行。")
        return

    rows = []  # (neb_name, idx, xhi, yhi, zhi, e_final, norm)
    for neb_dir in sorted(MIN_DIR.glob(NEB_DIR_GLOB), key=lambda p: neb_index_from_name(p.name)):
        stdout_path = neb_dir / STDOUT_NAME
        if not stdout_path.exists():
            # 跳過沒有結果的
            continue
        try:
            xhi, yhi, zhi, e_final = parse_stdout(stdout_path)
        except Exception as e:
            print(f"[WARN] 解析失敗 {stdout_path}: {e}")
            continue

        if MODE == "edge":
            norm = e_final / yhi
        else:
            norm = e_final / xhi

        rows.append((neb_dir.name, neb_index_from_name(neb_dir.name), xhi, yhi, zhi, e_final, norm))

    if not rows:
        print("[INFO] 沒有可用的 STDOUT_min_post_neb。")
        return

    # 輸出 CSV
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mode", MODE])
        w.writerow(["neb_name", "neb_index", "xhi", "yhi", "zhi", "E_final", "E_final_per_length"])
        for r in rows:
            w.writerow(r)

    # 繪圖（散點 + 連線）
    xs = [r[1] for r in rows]
    ys = [r[6] for r in rows]

    # 計算最大減最小
    y_min = min(ys)
    y_max = max(ys)
    y_range = y_max - y_min

    plt.figure()
    plt.plot(xs, ys, marker='o')  # 連線 + 點
    plt.xlabel("NEB Image Index")
    unit_axis = "yhi" if MODE == "edge" else "xhi"
    plt.ylabel(f"E_final / {unit_axis}")
    plt.title(f"Minimized Energy per length ({MODE})")
    plt.grid(True)
    
    # 在圖上添加最大減最小的標註
    plt.text(0.02, 0.98, f"Max - Min = {y_range:.15g}", 
             transform=plt.gca().transAxes, 
             verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    PNG_OUT.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(PNG_OUT, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"[OK] 已輸出：\n  CSV: {CSV_OUT}\n  圖檔: {PNG_OUT}")

if __name__ == "__main__":
    main()
