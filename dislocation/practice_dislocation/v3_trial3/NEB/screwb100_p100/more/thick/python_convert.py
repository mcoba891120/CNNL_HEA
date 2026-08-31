def convert_lammps_data_to_simple_format(input_file, output_file):
    """
    讀取 LAMMPS data 檔案，提取原子數和 Atoms 區塊 (ID, x, y, z)，並轉換為指定格式輸出。

    參數:
    input_file (str): LAMMPS data 檔案路徑
    output_file (str): 轉換後的輸出檔案路徑
    """
    with open(input_file, "r") as file:
        lines = file.readlines()

    # 1️⃣ 取得原子數 (atoms)
    atom_count = None
    atoms_start = None
    for i, line in enumerate(lines):
        if "atoms" in line:
            atom_count = int(line.split()[0])  # 提取原子數
        if "Atoms" in line:
            atoms_start = i + 2  # "Atoms" 下一行是數據開始
            break

    if atom_count is None or atoms_start is None:
        raise ValueError("檔案格式錯誤，未找到 atoms 或 Atoms 區塊")

    # 2️⃣ 解析 Atoms 區塊 (提取 ID, x, y, z)
    atoms_data = []
    for line in lines[atoms_start:]:
        parts = line.split()
        if len(parts) >= 5:  # 確保至少有 ID, type, x, y, z
            atom_id = int(parts[0])
            x, y, z = map(float, parts[2:5])  # 只取 x, y, z
            atoms_data.append((atom_id, x, y, z))

    # 3️⃣ 按 ID 排序
    atoms_data_sorted = sorted(atoms_data, key=lambda x: x[0])

    # 4️⃣ 寫入輸出檔案
    with open(output_file, "w") as file:
        file.write(f"{atom_count}\n")  # 第一行寫入原子數
        for atom_id, x, y, z in atoms_data_sorted:
            file.write(f"{atom_id} {x:.6f} {y:.6f} {z:.6f}\n")  # 輸出固定小數點格式

    print(f"✅ 轉換完成！輸出檔案：{output_file}")

# 🛠 使用範例
input_file = "HEA_opt_screw2.data"  # 替換為你的 LAMMPS data 檔案
output_file = "final.txt"  # 轉換後的輸出檔案
convert_lammps_data_to_simple_format(input_file, output_file)