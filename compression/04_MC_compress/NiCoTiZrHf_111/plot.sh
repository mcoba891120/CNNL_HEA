#!/bin/bash

# 清除上一次的結果檔案
rm -f results.txt

# 遍歷所有符合的目錄
for dir in var8_*; do
    # 獲取 X 和 Y 值
    X=$(echo "$dir" | cut -d'_' -f2)
    Y=$(echo "$dir" | cut -d'_' -f3)

    # 檢查 Y 是否為指定的溫度
    case $Y in
        300|600|900|1200|1500)
            for file in "$dir"/*.txt; do
                # 使用 awk 計算斜率
                slope=$(awk 'NR>1 {x[NR]=$1; y[NR]=$2} END { 
                    n=NR-1; 
                    sum_x=0; sum_y=0; sum_x2=0; sum_xy=0; 
                    for (i=2; i<=NR; i++) { 
                        sum_x+=x[i]; sum_y+=y[i]; 
                        sum_x2+=x[i]*x[i]; sum_xy+=x[i]*y[i]; 
                    } 
                    slope=(n*sum_xy - sum_x*sum_y) / (n*sum_x2 - sum_x*sum_x); 
                    print slope;
                }' "$file")
                # 將結果寫入檔案
                echo "$X $Y $slope" >> results.txt
            done
            ;;
        *)
            # 不符合指定溫度的目錄將被忽略
            ;;
    esac
done

# 使用內嵌的 Python 腳本進行繪圖，並將圖形儲存
python3 - <<EOF
import matplotlib.pyplot as plt
import pandas as pd

# 設定 matplotlib 使用不需要 GUI 的 backend
plt.switch_backend('Agg')

# 讀取結果檔案
data = pd.read_csv('results.txt', delim_whitespace=True, header=None, names=['X', 'Y', 'slope'])

# 繪圖
fig, ax = plt.subplots()
for label, df in data.groupby('X'):
    df_sorted = df.sort_values('Y')
    ax.plot(df_sorted['Y'], df_sorted['slope'], marker='o', label=label)

ax.set_xlabel('Temperature (K)')
ax.set_ylabel("Young's modulus (Gpa)")
ax.set_title("(111) Young's modulus vs. Temperature")
ax.legend()

# 儲存圖形到檔案
plt.savefig('output_plot.png')

print("Plot saved as 'output_plot.png'")
EOF

echo "Script execution completed."
