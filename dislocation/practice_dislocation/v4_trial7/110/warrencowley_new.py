from ovito.io import import_file
import WarrenCowleyParameters as wc

pipeline = import_file("after_relax.data")
mod = wc.WarrenCowleyParameters(nneigh=[0, 14], only_selected=False)
pipeline.modifiers.append(mod)
data = pipeline.compute()

# 獲取 Warren-Cowley 參數
wc_combined = data.attributes["Warren-Cowley parameters"]

# 將結果寫入 txt 檔案
with open("warren_cowley_parameters_after_relax_v2.txt", "w") as file:
    file.write(f"Combined Warren-Cowley parameters (within 2NN range): \n{wc_combined[0]}\n")

print("Warren-Cowley parameters have been written to 'warren_cowley_parameters_after_relax_v2.txt'.")