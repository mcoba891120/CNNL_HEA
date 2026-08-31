from ovito.io import import_file
import WarrenCowleyParameters as wc

pipeline = import_file("after_relax.data")
mod = wc.WarrenCowleyParameters(nneigh=[0, 8, 14], only_selected=False)
pipeline.modifiers.append(mod)
data = pipeline.compute()

# 獲取 Warren-Cowley 參數
wc_for_shells = data.attributes["Warren-Cowley parameters"]

# 將結果寫入 txt 檔案
with open("warren_cowley_parameters_after_relax.txt", "w") as file:
    file.write(f"1NN Warren-Cowley parameters: \n{wc_for_shells[0]}\n")
    file.write(f"2NN Warren-Cowley parameters: \n{wc_for_shells[1]}\n")

print("Warren-Cowley parameters have been written to 'warren_cowley_parameters_after_relax.txt'.")