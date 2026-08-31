#!/bin/bash

# 設定腳本名稱
SCRIPT_NAME=$(basename "$0")

# 顯示使用方法
usage() {
    echo "用法: $SCRIPT_NAME -i <輸入文件> -o <輸出文件> -l <del_xlo位置> -h <del_xhi位置> [-w <del寬度>]"
    echo ""
    echo "參數說明:"
    echo "  -i, --input         輸入的LAMMPS腳本文件"
    echo "  -o, --output        輸出的LAMMPS腳本文件"
    echo "  -l, --xlo           del_xlo的位置 (以full_bg為單位，正數為中軸右側，負數為中軸左側)"
    echo "  -h, --xhi           del_xhi的位置 (以full_bg為單位，正數為中軸右側，負數為中軸左側)"
    echo "  -w, --width         切除區域的寬度 (以full_bg為單位，可選，若指定則會忽略xhi值)"
    echo ""
    echo "例如:"
    echo "  $SCRIPT_NAME -i in.edge -o in.edge.modified -l -2.5 -h -1.5"
    echo "  $SCRIPT_NAME -i in.edge -o in.edge.modified -l 1.5 -w 1.0"
    echo ""
    echo "注意:"
    echo "  - 接受小數點後一位的輸入"
    echo "  - 位置是相對於中軸 ($(lx)*0.5) 的偏移量，以full_bg為單位"
    echo "  - 如果指定寬度，則del_xhi會自動設置為del_xlo + 寬度"
    exit 1
}

# 初始化變數
INPUT_FILE=""
OUTPUT_FILE=""
DEL_XLO_POS=""
DEL_XHI_POS=""
DEL_WIDTH=""

# 解析命令行參數
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--input)
            INPUT_FILE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -l|--xlo)
            DEL_XLO_POS="$2"
            shift 2
            ;;
        -h|--xhi)
            DEL_XHI_POS="$2"
            shift 2
            ;;
        -w|--width)
            DEL_WIDTH="$2"
            shift 2
            ;;
        *)
            echo "錯誤: 未知參數 $1"
            usage
            ;;
    esac
done

# 檢查必要參數
if [[ -z "$INPUT_FILE" || -z "$OUTPUT_FILE" || -z "$DEL_XLO_POS" ]]; then
    echo "錯誤: 缺少必要參數"
    usage
fi

# 如果設置了寬度但沒有設置xhi，則計算xhi
if [[ -n "$DEL_WIDTH" && -z "$DEL_XHI_POS" ]]; then
    # 使用bc進行浮點數計算
    DEL_XHI_POS=$(echo "$DEL_XLO_POS + $DEL_WIDTH" | bc)
    echo "根據指定寬度 $DEL_WIDTH，計算出del_xhi位置為: $DEL_XHI_POS"
elif [[ -z "$DEL_XHI_POS" && -z "$DEL_WIDTH" ]]; then
    echo "錯誤: 必須指定del_xhi位置或切除區域寬度"
    usage
fi

# 檢查輸入文件是否存在
if [[ ! -f "$INPUT_FILE" ]]; then
    echo "錯誤: 輸入文件 '$INPUT_FILE' 不存在"
    exit 1
fi

# 建立臨時文件
TMP_FILE=$(mktemp)

# 根據指定的位置生成修改表達式
generate_expression() {
    local pos=$1
    local sign=""
    
    # 處理正負號
    if (( $(echo "$pos < 0" | bc -l) )); then
        sign="-"
        pos=$(echo "$pos * -1" | bc) # 轉為正數處理
    else
        sign="+"
    fi
    
    # 將位置轉換為full_bg和half_bg的組合
    local full_bg_count=$(echo "$pos / 1" | bc)
    local half_bg_count=0
    
    # 處理小數部分
    local decimal_part=$(echo "$pos - $full_bg_count" | bc)
    if (( $(echo "$decimal_part >= 0.5" | bc -l) )); then
        half_bg_count=1
        full_bg_count=$(echo "$full_bg_count - 0.5" | bc)
    fi
    
    # 構建表達式
    local expr="\$(lx)*0.5"
    
    if [[ "$full_bg_count" != "0" ]]; then
        expr="${expr} ${sign} \${full_bg}*$full_bg_count"
    fi
    
    if [[ "$half_bg_count" == "1" ]]; then
        if [[ "$full_bg_count" == "0" ]]; then
            expr="${expr} ${sign} \${half_bg}"
        else
            expr="${expr} ${sign} \${half_bg}"
        fi
    fi
    
    # 添加調整值
    expr="${expr}+0.1"
    
    echo "$expr"
}

# 生成表達式
XLO_EXPR=$(generate_expression "$DEL_XLO_POS")
XHI_EXPR=$(generate_expression "$DEL_XHI_POS")

# 替換第一個腳本部分
echo "處理第一個腳本部分..."
awk -v xlo_expr="$XLO_EXPR" -v xhi_expr="$XHI_EXPR" '
BEGIN { in_first_part = 1; found_first = 0; found_second = 0 }

/variable.*del_xlo.*equal/ && in_first_part && !found_first {
    print "variable \tdel_xlo equal " xlo_expr;
    found_first = 1;
    next;
}

/variable.*del_xhi.*equal/ && in_first_part && !found_second {
    print "variable \tdel_xhi equal " xhi_expr;
    found_second = 1;
    next;
}

/clear/ { in_first_part = 0 }

{ print }
' "$INPUT_FILE" > "$TMP_FILE"

# 確認第二個腳本開始位置
START_LINE=$(grep -n "^###" "$TMP_FILE" | cut -d: -f1)
if [[ -z "$START_LINE" ]]; then
    echo "警告: 找不到第二個腳本部分的開始標記 (###)"
    # 嘗試用clear命令尋找
    START_LINE=$(grep -n "^clear" "$TMP_FILE" | cut -d: -f1)
    if [[ -z "$START_LINE" ]]; then
        echo "錯誤: 無法找到第二個腳本部分"
        rm "$TMP_FILE"
        exit 1
    fi
fi

# 處理第二個腳本部分
echo "處理第二個腳本部分..."
awk -v start="$START_LINE" -v xlo_expr="$XLO_EXPR" -v xhi_expr="$XHI_EXPR" '
NR < start { print; next }
NR == start { print; in_second_part = 1; next }

/variable.*del_xlo.*equal/ && in_second_part && !found_first {
    print "variable \tdel_xlo equal " xlo_expr;
    found_first = 1;
    next;
}

/variable.*del_xhi.*equal/ && in_second_part && !found_second {
    print "variable \tdel_xhi equal " xhi_expr;
    found_second = 1;
    next;
}

{ print }
' "$TMP_FILE" > "$OUTPUT_FILE"

# 清理臨時文件
rm "$TMP_FILE"

echo "修改完成！已將del_xlo和del_xhi的位置設置為:"
echo "  del_xlo = $XLO_EXPR"
echo "  del_xhi = $XHI_EXPR"
echo "結果已保存到: $OUTPUT_FILE"

# 顯示設置概要
echo ""
echo "設置概要:"
echo "  位置單位: full_bg = \$(lx)/51"
echo "  del_xlo位置: $DEL_XLO_POS (以full_bg為單位，相對於中軸)"
echo "  del_xhi位置: $DEL_XHI_POS (以full_bg為單位，相對於中軸)"
if [[ -n "$DEL_WIDTH" ]]; then
    echo "  切除區域寬度: $DEL_WIDTH (以full_bg為單位)"
else
    WIDTH=$(echo "$DEL_XHI_POS - $DEL_XLO_POS" | bc)
    echo "  切除區域寬度: $WIDTH (以full_bg為單位)"
fi