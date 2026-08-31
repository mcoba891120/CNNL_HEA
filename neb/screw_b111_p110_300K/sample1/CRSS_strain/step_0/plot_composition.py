#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import csv
from pathlib import Path

# ====== 強制使用無 GUI 後端，避免 Qt/xcb 錯誤（一定要在 pyplot 之前） ======
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ====== type -> element（需要時自行改） ======
TYPE_TO_ELEM = {1: "Ni", 2: "Co", 3: "Ti", 4: "Zr", 5: "Hf"}
ELEMS = ["Ni", "Co", "Ti", "Zr", "Hf"]

# ====== 你指定的兩個子集合 ======
SUB1 = ["Ni", "Co"]
SUB2 = ["Ti", "Zr", "Hf"]


def _extract_suffix_int(path: Path) -> int:
    """從檔名抓 _數字 作排序依據：numBCC_sb100p100_6.data -> 6"""
    m = re.search(r"_(\d+)", path.stem)  # stem 不含副檔名
    return int(m.group(1)) if m else 10**9


def parse_type_counts_from_lammps_data(file_path: Path) -> dict[int, int]:
    """
    讀 LAMMPS data 檔 Atoms section，統計 type 次數。
    支援常見格式：
      Atoms
      <blank>
      id type x y z ...
    或
      id type q x y z ...
    （我們只取第2欄作 type）
    """
    lines = file_path.read_text(errors="ignore").splitlines()

    in_atoms = False
    atoms_started = False
    counts: dict[int, int] = {}

    for line in lines:
        s = line.strip()

        # 進入 Atoms 區段
        if (not in_atoms) and s.startswith("Atoms"):
            in_atoms = True
            atoms_started = False
            continue

        # 跳過 Atoms 後的空行直到資料開始
        if in_atoms and (not atoms_started):
            if s == "":
                atoms_started = True
            continue

        # 解析 Atoms 區內資料
        if in_atoms and atoms_started:
            # 空行或下一個 section 開頭就結束
            if s == "" or re.match(r"^[A-Za-z]", s):
                break

            parts = s.split()
            if len(parts) < 2:
                continue

            # 第一欄必須是 id（數字）
            if not parts[0].lstrip("+-").isdigit():
                continue

            # 第二欄是 type
            try:
                t = int(float(parts[1]))
            except ValueError:
                continue

            counts[t] = counts.get(t, 0) + 1

    return counts


def main():
    # 讀取檔案：優先 *.data
    files = sorted(Path(".").glob("configureD_numBCC_sb111p110_*.data"), key=_extract_suffix_int)
    if not files:
        files = sorted(Path(".").glob("configureD_numBCC_sb111p110_*"), key=_extract_suffix_int)
    if not files:
        raise FileNotFoundError("找不到 configureD_numBCC_sb111p110_* 檔案。請確認腳本與檔案在同資料夾。")

    records = []
    for fp in files:
        counts_type = parse_type_counts_from_lammps_data(fp)

        # 轉成元素計數
        counts_elem = {e: 0 for e in ELEMS}
        for t, c in counts_type.items():
            e = TYPE_TO_ELEM.get(t)
            if e in counts_elem:
                counts_elem[e] += c

        total = sum(counts_elem.values())
        frac_global = {e: (counts_elem[e] / total if total else 0.0) for e in ELEMS}

        # sub1 / sub2 內部正規化（你要的平均）
        sub1_total = sum(counts_elem[e] for e in SUB1)
        sub2_total = sum(counts_elem[e] for e in SUB2)

        subfrac = {e: 0.0 for e in ELEMS}
        for e in SUB1:
            subfrac[e] = counts_elem[e] / sub1_total if sub1_total else 0.0
        for e in SUB2:
            subfrac[e] = counts_elem[e] / sub2_total if sub2_total else 0.0

        records.append({
            "file": fp.name,
            "idx": _extract_suffix_int(fp),
            "total": total,
            "sub1_total(Ni+Co)": sub1_total,
            "sub2_total(Ti+Zr+Hf)": sub2_total,
            **{f"count_{e}": counts_elem[e] for e in ELEMS},
            **{f"frac_global_{e}": frac_global[e] for e in ELEMS},
            **{f"subfrac_{e}": subfrac[e] for e in ELEMS},
        })

    # 依 idx 排序
    records = sorted(records, key=lambda r: r["idx"])

    # ====== 輸出 CSV ======
    out_csv = "composition_summary.csv"
    fieldnames = (
        ["file", "idx", "total", "sub1_total(Ni+Co)", "sub2_total(Ti+Zr+Hf)"] +
        [f"count_{e}" for e in ELEMS] +
        [f"frac_global_{e}" for e in ELEMS] +
        [f"subfrac_{e}" for e in ELEMS]
    )

    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(records)

    # ====== 畫圖：x 軸是檔名（類別軸），y 軸是 subfrac ======
    labels = [r["file"] for r in records]
    x = list(range(len(labels)))

    plt.figure(figsize=(10, 5))
    for e in ELEMS:
        y = [r[f"subfrac_{e}"] for r in records]
        plt.plot(x, y, marker="o", linewidth=1.8, label=e)

    plt.xticks(x, labels, rotation=30, ha="right")
    plt.xlabel("File name")
    plt.ylabel("Subgroup-normalized fraction (mean within sub1/sub2)")
    plt.title("Composition: Ni-Co normalized in sub1; Ti-Zr-Hf normalized in sub2")
    plt.ylim(0, 1.0)
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig("composition_5lines.png", dpi=300)
    plt.close()

    # ====== 終端機列印一個精簡表 ======
    print("file, idx, subfrac_Ni, subfrac_Co, subfrac_Ti, subfrac_Zr, subfrac_Hf")
    for r in records:
        print(f"{r['file']}, {r['idx']}, "
              f"{r['subfrac_Ni']:.6f}, {r['subfrac_Co']:.6f}, "
              f"{r['subfrac_Ti']:.6f}, {r['subfrac_Zr']:.6f}, {r['subfrac_Hf']:.6f}")

    print("\n輸出完成：composition_summary.csv、composition_5lines.png")


if __name__ == "__main__":
    main()