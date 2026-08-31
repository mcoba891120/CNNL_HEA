#!/usr/bin/env python3
import os, re, sys
import numpy as np

LOG_CANDIDATES = ["log.lammps.{r}", "log.neb.{r}", "log.{r}"]
NEB_KEYWORD, NEXTLINE_COL = "next-to-last", 3   # 取關鍵字下一行的第3欄
REPLICAS = range(0, 10)                         # 影像數量：依你的 in.neb 設定調整

def read_lines(p):
    with open(p, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().splitlines()

def find_log(step_dir, r):
    for pat in LOG_CANDIDATES:
        p = os.path.join(step_dir, pat.format(r=r))
        if os.path.isfile(p):
            return p
    return None

def parse_final_energy(lines):
    # 1) 先找 'next-to-last'，用它下一行第 NEXTLINE_COL 欄
    last = None
    for i, ln in enumerate(lines):
        if NEB_KEYWORD in ln:
            last = i
    if last is not None and last + 1 < len(lines):
        parts = lines[last + 1].split()
        if len(parts) >= NEXTLINE_COL:
            try:
                return float(parts[NEXTLINE_COL - 1])
            except ValueError:
                pass
    # 2) 回退策略：從檔尾往前找最後一個浮點數
    mfloat = re.compile(r'([\-+]?\d+(?:\.\d+)?(?:[eE][\-+]?\d+)?)')
    for ln in reversed(lines):
        ms = mfloat.findall(ln)
        if ms:
            v = ms[-1][0] if isinstance(ms[-1], tuple) else ms[-1]
            try:
                return float(v)
            except ValueError:
                continue
    return float("nan")

def main(step_dir="."):
    energies = []
    for r in REPLICAS:
        lp = find_log(step_dir, r)
        if not lp:
            energies.append(np.nan)
            continue
        e = parse_final_energy(read_lines(lp))
        energies.append(e)
    arr = np.array(energies, float)
    if not np.isfinite(arr).any():
        sys.stderr.write("[WARN] 找不到任何影像能量；沒有輸出。\n")
        sys.exit(1)
    np.savetxt(os.path.join(step_dir, "NEB_energy.txt"), arr[np.newaxis, :], fmt="%.10f")
    # 上面寫成「一行 N 欄」。若你偏好一列一行，改成：arr.reshape(-1,1)
    print(f"[OK] 寫出 {os.path.join(step_dir, 'NEB_energy.txt')}，影像數={arr.size}")

if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "."
    main(step)