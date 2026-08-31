import numpy as np
from ovito.io import import_file
from ovito.modifiers import DislocationAnalysisModifier

# 讀取 data 檔案
pipeline = import_file("neb_7.data")  # 替換成你的檔案名稱

# 套用 DXA modifier，設置為 B2 結構（B2 屬於 BCC lattice）
dxa = DislocationAnalysisModifier(input_crystal_structure=DislocationAnalysisModifier.Lattice.BCC, neighborhood_radius=1.2) # 調整鄰域路徑
pipeline.modifiers.append(dxa)

# 執行計算
data = pipeline.compute()

# 檢查是否有 DXA 結果
if hasattr(data, 'dislocations') and len(data.dislocations.segments) > 0:
    print(f"Dislocation Segments number: {len(data.dislocations.segments)}")

    # 假設目前只有一條位錯線
    line = data.dislocations.segments[0]

    # 提取節點座標
    coordinates = line.points  # Vec3 型別的列表

    # 計算每個中間節點的曲率
    curvatures = []
    for i in range(1, len(coordinates) - 1):  # 避開首尾
        p1 = np.array(coordinates[i-1])
        p2 = np.array(coordinates[i])
        p3 = np.array(coordinates[i+1])

        v1 = p2 - p1
        v2 = p3 - p2

        if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
            curvatures.append(0.0)
            continue

        angle = np.arccos(np.clip(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)), -1.0, 1.0))
        curvature = angle / np.linalg.norm(v2)
        curvatures.append(curvature)

    # 找到最大曲率段
    max_curvature = max(curvatures)
    max_curvature_index = curvatures.index(max_curvature)

    print(f"The most curved segment is between node {max_curvature_index} and node {max_curvature_index + 1}")
    print(f"Max curvature value: {max_curvature}")

    p_start = coordinates[max_curvature_index]
    p_end = coordinates[max_curvature_index + 1]

    print("Coordinates of max curvature segment:")
    print(f"Start point: {p_start[0]}, {p_start[1]}, {p_start[2]}")
    print(f"End point:   {p_end[0]}, {p_end[1]}, {p_end[2]}")

    # 匯出成 POSCAR 格式，或 XYZ 格式也可
    with open("high_curvature_segment.POSCAR", "w") as f:
        f.write("2\n")
        f.write("Most curved dislocation segment endpoints\n")
        f.write(f"X {p_start[0]} {p_start[1]} {p_start[2]}\n")
        f.write(f"X {p_end[0]} {p_end[1]} {p_end[2]}\n")

else:
    print("No dislocations detected in the system.")





