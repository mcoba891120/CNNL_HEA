#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, math, csv, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import hsv_to_rgb

# ====== 你已知的外加應變對應 ======
STRAIN_PCT_PER_STEP = 0.0951  # 每一步的工程剪應變（百分比 %）
# 若需顯示到第2位小數，legend 會顯示 round(k*0.2367, 2)%

# ====== 其他設定 ======
REPLICAS  = range(0, 7)                         # 0..6
STEP_DIRS = [f"step_{i}" for i in range(0, 10)] # step_0..step_13
DIVISOR   = 54.148
NEB_KEYWORD = "next-to-last"
NEXTLINE_COL = 3
LOG_NAME_CANDIDATES = ["log.lammps.{r}", "log.neb.{r}", "log.{r}"]

def read_lines(p):
    with open(p, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().splitlines()

def parse_energy(lines):
    # A) 找最後一次 'next-to-last'，取下一行第 3 欄
    last = None
    for i, line in enumerate(lines):
        if NEB_KEYWORD in line:
            last = i
    if last is not None and last + 1 < len(lines):
        parts = lines[last + 1].split()
        if len(parts) >= NEXTLINE_COL:
            try:
                return float(parts[NEXTLINE_COL - 1])
            except ValueError:
                pass
    # B) 備援：從檔尾往上找最後一個浮點數
    float_re = re.compile(r'([\-+]?\d+(?:\.\d+)?(?:[eE][\-+]?\d+)?)')
    for i in range(len(lines) - 1, -1, -1):
        m = float_re.findall(lines[i])
        if m:
            try:
                val = m[-1][0] if isinstance(m[-1], tuple) else m[-1]
                return float(val)
            except ValueError:
                continue
    return math.nan

def find_log(step_dir, r):
    for pat in LOG_NAME_CANDIDATES:
        p = os.path.join(step_dir, pat.format(r=r))
        if os.path.isfile(p):
            return p
    return None

def progressive_shaded_spectrum(n,
                                h_start=0.00,
                                h_end=5/6,
                                s=0.95,
                                v_triplet=(0.45, 0.72, 0.96)):
    groups = math.ceil(n / 3)
    colors = []
    for g in range(groups):
        t = 0.0 if groups == 1 else g / (groups - 1)
        hue = h_start + (h_end - h_start) * t
        for v in v_triplet:
            colors.append(tuple(hsv_to_rgb((hue, s, v))))
            if len(colors) >= n:
                return colors
    return colors

# ====== 收集 NEB 能量 ======
all_norm, all_raw, missing = [], [], []

for sd in STEP_DIRS:
    if not os.path.isdir(sd):
        print(f"[WARN] 缺少目錄：{sd}（跳過此步）")
        all_norm.append([math.nan]*len(REPLICAS))
        all_raw.append([math.nan]*len(REPLICAS))
        continue

    raw_vals = []
    for r in REPLICAS:
        logp = find_log(sd, r)
        if logp is None:
            raw_vals.append(math.nan)
            missing.append(f"{sd}/log.*.{r} 不存在")
            continue
        e = parse_energy(read_lines(logp))
        raw_vals.append(e)

    raw_arr = np.array(raw_vals, dtype=float)
    all_raw.append(raw_vals)

    # 步內正規化：先除，再扣該步 replica_0
    norm = raw_arr / DIVISOR
    if np.isfinite(norm).any():
        base = norm[0]
        norm = norm - base
    all_norm.append(norm.tolist())

all_norm = np.array(all_norm, dtype=float)
all_raw  = np.array(all_raw,  dtype=float)

# ====== 輸出 CSV ======
# 1) 能量曲線
with open("neb_final_energy_norm10.csv", "w", newline="") as f:
    w = csv.writer(f)
    header = ["step"] + [f"replica_{r}" for r in REPLICAS]
    w.writerow(header)
    for idx, sd in enumerate(STEP_DIRS):
        step_num = int(sd.split("_")[1])
        w.writerow([step_num] + list(all_norm[idx]))
print("[INFO] 已輸出 CSV：neb_final_energy_norm10.csv")

# 2) step → γ(%) 對照（固定 0.2367%/step）
with open("step_to_gamma.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["step", "gamma_percent"])
    for sd in STEP_DIRS:
        k = int(sd.split("_")[1])
        g_pct = k * STRAIN_PCT_PER_STEP
        w.writerow([k, f"{g_pct:.4f}"])
print("[INFO] 已輸出 CSV：step_to_gamma.csv  （每步 +0.2367%）")

if missing:
    print("[WARN] 找不到的 log 檔：")
    for m in missing:
        print("  -", m)

# ====== 畫圖：legend 直接顯示 γ = xx.xx% ======
x = list(REPLICAS)
plt.figure(figsize=(12, 7))
colors = progressive_shaded_spectrum(len(STEP_DIRS),
                                     h_start=0.00,
                                     h_end=5/6,
                                     s=0.95,
                                     v_triplet=(0.45, 0.72, 0.96))

plotted = 0
for idx, sd in enumerate(STEP_DIRS):
    y = all_norm[idx]
    if not np.isfinite(y).any():
        print(f"[WARN] {sd} 沒有可用數據（皆 NaN），略過畫圖")
        continue
    k = int(sd.split("_")[1])
    g_pct = k * STRAIN_PCT_PER_STEP
    label_txt = f"ε = {g_pct:.2f}%"  # 小數第二位
    plt.plot(x, y, marker='o', markersize=3.0, linewidth=1.2,
             color=colors[idx], label=label_txt, alpha=0.98)
    plotted += 1

plt.xlabel("Coordinate")
plt.ylabel("Normalized Relative Energy (eV/Å)")
plt.title("Screw_{010}<100>  (Legend shows γ per step)")
plt.grid(True, linestyle=":", linewidth=0.6)

plt.legend(loc="lower left", ncol=5, fontsize=12,
           frameon=True, framealpha=0.75,
           borderpad=0.3, labelspacing=0.25,
           handlelength=1.0, handletextpad=0.4, markerscale=0.8)

plt.tight_layout()
plt.savefig("neb_final_energy_norm10.png", dpi=200)
print("[INFO] 已輸出圖檔：neb_final_energy_norm10.png")

if plotted == 0:
    print("[ERROR] 沒有任何曲線被畫出，請檢查 log 檔與關鍵字。", file=sys.stderr)
    sys.exit(2)