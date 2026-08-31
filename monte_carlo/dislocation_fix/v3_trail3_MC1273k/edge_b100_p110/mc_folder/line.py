#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import matplotlib
matplotlib.use("Agg")          # 重要：無頭模式
import matplotlib.pyplot as plt

x, y = [], []

# 讀同資料夾的 MC_record.txt
with open("MC_record.txt", "r") as f:
    for line in f:
        parts = line.split()
        if len(parts) >= 2:
            x.append(int(parts[0]))      # 第一欄
            y.append(float(parts[1]))    # 第二欄

plt.figure()
plt.plot(x, y, linewidth=1)
plt.xlabel("Index (Column 1)")
plt.ylabel("Energy (Column 2)")
plt.title("Column 1 vs Column 2 (MC_record.txt)")
plt.tight_layout()

out = "MC_record_col1_col2.png"
plt.savefig(out, dpi=200)
print("Saved:", out)