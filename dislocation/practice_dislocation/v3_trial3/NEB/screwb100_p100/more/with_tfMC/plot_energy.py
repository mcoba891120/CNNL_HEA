import matplotlib.pyplot as plt

# 讀取資料檔案
filename = 'pot_vs_step.txt'  # 把這裡換成你的實際檔名
steps = []
energies = []

with open(filename, 'r') as file:
    for line in file:
        parts = line.strip().split()
        # 濾掉空行與非數值行
        if len(parts) == 2:
            try:
                step = int(float(parts[0]))
                energy = float(parts[1])
                steps.append(step)
                energies.append(energy)
            except ValueError:
                continue  # 如果遇到非數字行，就跳過

# 畫圖
plt.figure(figsize=(10, 6))
plt.plot(steps, energies, marker='o', linestyle='-', color='blue')
plt.xlabel('Step')
plt.ylabel('Potential Energy')
plt.title('Energy vs Step')
plt.grid(True)
plt.tight_layout()
plt.savefig('energy_trend.png', dpi=300)  # 存成圖片
plt.show()
