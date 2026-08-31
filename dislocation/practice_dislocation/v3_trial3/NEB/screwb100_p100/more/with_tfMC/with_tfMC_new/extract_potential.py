import re

# 設定你的STDOUT檔案名稱
filename = "STDOUT"

# 用來存取每一步的 PotEng 值
steps = []
potentials = []

with open(filename, "r") as f:
    for line in f:
        # 搜尋包含 Step 與 PotEng 的資料列
        if re.match(r"^\s*\d+", line) and "PotEng" not in line:
            parts = line.split()
            if len(parts) >= 3:  # 確保有足夠的欄位數
                try:
                    step = int(parts[0])
                    pot = float(parts[1])  # PotEng通常是第2欄，依照你log格式可能需要調整
                    steps.append(step)
                    potentials.append(pot)
                except ValueError:
                    continue

# 儲存成文字檔
with open("pot_vs_step.txt", "w") as out:
    out.write("Step Pot\n")
    for step, pot in zip(steps, potentials):
        out.write(f"{step} {pot:.6f}\n")

print("已成功將每一步的Pot能儲存到 pot_vs_step.txt")

