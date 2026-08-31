# Energy Analysis Scripts

這組腳本可以幫你分析多個資料夾中的screen文件，提取Energy final值並生成比較圖表。

## 文件說明

### 主要腳本
- `multi_folder_energy_analysis.py` - 完整的多資料夾分析腳本
- `run_energy_analysis.py` - 簡化版腳本，使用配置文件
- `folder_list_config.py` - 配置文件，定義要分析的資料夾列表

### 單一資料夾腳本
- `extract_energy_en.py` - 分析單一資料夾的腳本

## 使用方法

### 方法1：使用配置文件（推薦）

1. 編輯 `folder_list_config.py` 文件，修改 `FOLDER_PATHS` 列表：

```python
FOLDER_PATHS = [
    os.path.join(BASE_PATH, "change_ratio_12_5_300K"),
    os.path.join(BASE_PATH, "change_ratio_20_300K"),
    os.path.join(BASE_PATH, "change_ratio_25_300K"),
    os.path.join(BASE_PATH, "change_ratio_12_5_300K", "next1"),
    # 添加更多資料夾...
]
```

2. 運行分析腳本：

```bash
python3 run_energy_analysis.py
```

### 方法2：直接修改主腳本

編輯 `multi_folder_energy_analysis.py` 中的 `folder_paths` 列表，然後運行：

```bash
python3 multi_folder_energy_analysis.py
```

### 方法3：分析單一資料夾

```bash
python3 extract_energy_en.py
```

## 輸出結果

所有結果會保存在 `energy_analysis_results/` 資料夾中：

### 圖表文件
- `energy_vs_screen_[hierarchical_name].png` - 每個資料夾的個別圖表
  - 主資料夾：`energy_vs_screen_change_ratio_12_5_300K.png`
  - 子資料夾：`energy_vs_screen_change_ratio_12_5_300K_next1.png`

### 數據文件
- `energy_data_summary.csv` - 所有數據的CSV摘要
- `energy_data_[hierarchical_name].txt` - 每個資料夾的詳細數據

## 配置選項

在 `folder_list_config.py` 中可以調整：

- `FOLDER_PATHS` - 要分析的資料夾列表
- `MAX_SCREEN` - 最大screen編號（預設8）
- `OUTPUT_FOLDER_NAME` - 輸出資料夾名稱
- `PLOT_SETTINGS` - 圖表設定
- `PLOT_COLORS` - 圖表顏色

## 範例資料夾結構

```
your_project/
├── change_ratio_12_5_300K/
│   ├── screen.0
│   ├── screen.1
│   ├── ...
│   ├── screen.8
│   └── next1/
│       ├── screen.0
│       ├── screen.1
│       └── ...
├── change_ratio_20_300K/
│   ├── screen.0
│   └── ...
└── energy_analysis_results/
    ├── energy_vs_screen_change_ratio_12_5_300K.png
    ├── energy_vs_screen_change_ratio_12_5_300K_next1.png
    ├── energy_data_summary.csv
    └── ...
```

## 注意事項

1. 確保每個資料夾都包含 `screen.0` 到 `screen.8` 文件
2. screen文件必須包含 "Energy initial, next-to-last, final" 格式的數據
3. 腳本會自動跳過不存在的資料夾或文件
4. 結果會覆蓋現有的 `energy_analysis_results` 資料夾

## 故障排除

如果遇到問題：

1. 檢查資料夾路徑是否正確
2. 確認screen文件格式是否正確
3. 檢查Python依賴套件是否已安裝（matplotlib, pandas, numpy）
4. 查看終端輸出的錯誤訊息
