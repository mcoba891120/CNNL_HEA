from ovito.io import import_file
import WarrenCowleyParameters as wc

pipeline = import_file("after_relax_bulk.data")
mod = wc.WarrenCowleyParameters(nneigh=[0, 14], only_selected=False)
pipeline.modifiers.append(mod)
data = pipeline.compute()

wc_for_shells = data.attributes["Warren-Cowley parameters"]
print(f"1NN Warren-Cowley parameters: \n {wc_for_shells[0]}")
