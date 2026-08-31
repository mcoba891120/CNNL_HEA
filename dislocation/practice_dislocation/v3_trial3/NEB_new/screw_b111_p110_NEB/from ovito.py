from ovito.io import import_file
from ovito.modifiers import DislocationAnalysisModifier

# 讀取 dump.neb 檔案
pipeline = import_file("dump.neb.11")  # 請替換為你的檔案名稱

# 套用 DXA modifier
dxa = DislocationAnalysisModifier(input_crystal_structure=DislocationAnalysisModifier.Lattice.B2)
pipeline.modifiers.append(dxa)

# 計算數據
data = pipeline.compute()

# 檢查是否有 Dislocation Segments
if hasattr(data, 'dislocations'):
    print(f"Dislocation Segments number: {len(data.dislocations.segments)}")
    print(f"Dislocation Segments: {data.dislocations.segments}")
else:
    print("No dislocations detected in the system.")

