from ase.io import read

# 讀取 .lmp 文件
filename = "NiCoTiZrHf_69120.lmp"
atoms = read(filename, format='lammps-data', style='atomic')

# 檢查原子結構的化學符號及數量
atom_symbols = atoms.get_chemical_symbols()
unique_symbols = set(atom_symbols)
symbol_counts = {symbol: atom_symbols.count(symbol) for symbol in unique_symbols}

print("Unique symbols:", unique_symbols)
print("Symbol counts:", symbol_counts)
