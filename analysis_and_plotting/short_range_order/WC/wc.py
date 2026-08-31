from ovito.io import import_file
import WarrenCowleyParameters as wc
import pandas as pd
import numpy as np

orientation_range = {'100':4000,'110':4200,'111':4032}
trial_num = [3, 5]
results = []

for t in trial_num:
    for o, value in orientation_range.items():
        pipeline = import_file(f"relaxation/NiCoTiZrHf_{o}/var{t}_{value}_900k/md_npt_dump_var{t}_{value}_900k.cfg")
        mod = wc.WarrenCowleyParameters(nneigh=[0, 8, 14], only_selected=False)
        pipeline.modifiers.append(mod)
        data = pipeline.compute()

        wc_for_shells = data.attributes["Warren-Cowley parameters"]
        
        # 假設 wc_for_shells 是一個包含兩個二維矩陣的列表
        wc_1nn = pd.DataFrame(wc_for_shells[0], columns=['Ni', 'Co', 'Ti', 'Zr'])
        wc_2nn = pd.DataFrame(wc_for_shells[1], columns=['Ni', 'Co', 'Ti', 'Zr'])
        
        wc_1nn.index = ['Ni', 'Co', 'Ti', 'Zr']
        wc_2nn.index = ['Ni', 'Co', 'Ti', 'Zr']
        
        results.append({
            "Trial": t,
            "Orientation": o,
            "Value": value,
            "1NN Parameter": wc_1nn,
            "2NN Parameter": wc_2nn
        })

        print(f"1NN Warren-Cowley parameters for var{t}_{value}_900k before MC:")
        print(wc_1nn)
        print(f"\n2NN Warren-Cowley parameters for var{t}_{value}_900k before MC:")
        print(wc_2nn)
        print("\n")

# 保存為CSV文件
for i, result in enumerate(results):
    wc_1nn = result["1NN Parameter"]
    wc_2nn = result["2NN Parameter"]
    
    filename_1nn = f'./warren_cowley_1nn_var{result["Trial"]}_{result["Value"]}_900k.csv'
    filename_2nn = f'./warren_cowley_2nn_var{result["Trial"]}_{result["Value"]}_900k.csv'
    
    wc_1nn.to_csv(filename_1nn)
    wc_2nn.to_csv(filename_2nn)
    
    print(f"Results for var{result['Trial']}_{result['Value']}_900k have been saved to {filename_1nn} and {filename_2nn}")