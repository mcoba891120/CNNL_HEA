#!/usr/bin/env python3

import os
import re
import glob
import numpy as np
import pandas as pd
from scipy.stats import linregress
from pathlib import Path
import logging
from datetime import datetime

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def calculate_youngs_modulus(file_path, loop):
    """計算楊氏模數"""
    try:
        data = np.loadtxt(file_path, skiprows=1)
        strain = data[:loop, 0]
        stress = data[:loop, 1]
        slope, _, _, _, _ = linregress(strain, stress)
        return slope
    except Exception as e:
        logger.error(f"計算楊氏模數時發生錯誤 {file_path}: {e}")
        return None

def read_snap_with_regex(filename):
    """使用正則表達式讀取元素參數"""
    element_params = {}

    try:
        with open(filename, 'r') as f:
            content = f.read()
        
        # 正則表達式匹配元素行
        pattern = r'^([A-Z][a-z]?)\s+(\d+\.?\d*)\s+(\d+\.?\d*)$'
        
        for line in content.split('\n'):
            match = re.match(pattern, line.strip())
            if match:
                element = match.group(1)
                param1 = float(match.group(2))
                param2 = float(match.group(3))
                element_params[element] = [param1, param2]
        
        return element_params
    except Exception as e:
        logger.error(f"讀取SNAP參數時發生錯誤 {filename}: {e}")
        return {}

def extract_loop_from_compress_file(file_path):
    """從in.compress文件中提取loop值"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # 查找 variable comp_loop loop 數字
        pattern = r'variable\s+comp_loop\s+loop\s+(\d+)'
        match = re.search(pattern, content)
        
        if match:
            return int(match.group(1))
        else:
            logger.warning(f"未找到loop值在文件 {file_path}")
            return None
    except Exception as e:
        logger.error(f"讀取compress文件時發生錯誤 {file_path}: {e}")
        return None

def extract_snapcoeff_path(file_path):
    """從文件中提取snapcoeff路徑"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # 查找pair_coeff行
        pattern = r'pair_coeff\s+\*\s+\*\s+([^\s]+\.snapcoeff)'
        match = re.search(pattern, content)
        
        if match:
            return match.group(1)
        else:
            logger.warning(f"未找到snapcoeff路徑在文件 {file_path}")
            return None
    except Exception as e:
        logger.error(f"讀取文件時發生錯誤 {file_path}: {e}")
        return None

def process_directory(base_dir):
    """處理主目錄"""
    results = []
    
    # 目標資料夾列表 - Type 1
    target_dirs_type1 = ['NiCoTiZr_100', 'NiCoTiZr_111', 'NiCoTiZrHf_100', 'NiCoTiZrHf_111']
    
    for target_dir in target_dirs_type1:
        dir_path = os.path.join(base_dir, target_dir)
        if not os.path.exists(dir_path):
            logger.warning(f"目錄不存在: {dir_path}")
            continue
            
        # 確定是_100還是_111
        x_dir = '100' if target_dir.endswith('_100') else '111'
        logger.info(f"處理目錄: {target_dir}, x_dir = {x_dir}")
        
        # 查找_300k資料夾
        temp_dirs = glob.glob(os.path.join(dir_path, '*_300k*'))
        
        for temp_dir in temp_dirs:
            logger.info(f"處理溫度目錄: {temp_dir}")
            result = process_temperature_directory(temp_dir, x_dir, type_num='1')
            if result:
                results.append(result)
    
    # 新增處理 NiCoTiZrHf_110 - Type 2
    target_dir_110 = 'NiCoTiZrHf_110'
    dir_path_110 = os.path.join(base_dir, target_dir_110)
    
    if os.path.exists(dir_path_110):
        logger.info(f"處理目錄: {target_dir_110}, Type = 2")
        
        # 進入5quinary資料夾
        quinary_dir = os.path.join(dir_path_110, '5quinary')
        if os.path.exists(quinary_dir):
            logger.info(f"進入5quinary目錄: {quinary_dir}")
            
            # 查找版號資料夾 (v3_trial3等)
            version_dirs = glob.glob(os.path.join(quinary_dir, 'v*_trial*'))
            
            for version_dir in version_dirs:
                logger.info(f"處理版本目錄: {version_dir}")
                version_results = process_version_directory(version_dir)
                if version_results:
                    results.extend(version_results)
        else:
            logger.warning(f"5quinary目錄不存在: {quinary_dir}")
    else:
        logger.warning(f"目錄不存在: {dir_path_110}")
    
    return results

def extract_version_from_dirname(dirname):
    """從目錄名稱提取版本號"""
    # 例如: v3_trial3 -> v3_trial3
    basename = os.path.basename(dirname)
    match = re.match(r'(v\d+_trial\d+)', basename)
    if match:
        return match.group(1)
    return None

def find_snapcoeff_by_version(version):
    """根據版本號在 potentials/ 中尋找對應的snapcoeff文件"""
    pe_dir = 'potentials'
    
    # 構建snapcoeff文件路徑
    snapcoeff_file = os.path.join(pe_dir, f'HEA_{version}.snapcoeff')
    
    if os.path.exists(snapcoeff_file):
        logger.info(f"找到snapcoeff文件: {snapcoeff_file}")
        return snapcoeff_file
    else:
        logger.warning(f"snapcoeff文件不存在: {snapcoeff_file}")
        return None

def determine_x_dir_from_dirname(dirname):
    """根據目錄名稱確定x_dir"""
    basename = os.path.basename(dirname)
    
    if basename.endswith('b100p110'):
        return '100'
    elif basename.endswith('b111p110'):
        return '111'
    else:
        logger.warning(f"無法從目錄名稱確定x_dir: {basename}")
        return None

def process_version_directory(version_dir):
    """處理版本目錄 (Type 2)"""
    results = []
    
    # 提取版本號
    version = extract_version_from_dirname(version_dir)
    if not version:
        logger.error(f"無法提取版本號從目錄: {version_dir}")
        return results
    
    logger.info(f"提取到版本號: {version}")
    
    # 根據版本號尋找snapcoeff文件
    snapcoeff_path = find_snapcoeff_by_version(version)
    if not snapcoeff_path:
        logger.error(f"無法找到對應的snapcoeff文件: {version}")
        return results
    
    # 查找_300k_資料夾
    temp_dirs = glob.glob(os.path.join(version_dir, '*_300k_*'))
    
    for temp_dir in temp_dirs:
        logger.info(f"處理溫度目錄: {temp_dir}")
        
        # 根據目錄名稱確定x_dir
        x_dir = determine_x_dir_from_dirname(temp_dir)
        if not x_dir:
            logger.error(f"無法確定x_dir從目錄: {temp_dir}")
            continue
        
        logger.info(f"確定x_dir: {x_dir}")
        
        result = process_temperature_directory_type2(temp_dir, x_dir, snapcoeff_path)
        if result:
            results.append(result)
    
    return results

def process_temperature_directory_type2(temp_dir, x_dir, snapcoeff_path):
    """處理Type 2的溫度目錄"""
    result = {'Type': '2', 'x_dir': x_dir, 'temp_dir': temp_dir}
    
    # 1. 查找SS_curve文件並計算楊氏模數 (使用固定loop值21)
    ss_curve_files = glob.glob(os.path.join(temp_dir, '*SS_curve*'))
    
    if not ss_curve_files:
        logger.error(f"未找到SS_curve文件在目錄 {temp_dir}")
        return None
    
    # Type 2使用固定的loop值21
    loop = 21
    elas = calculate_youngs_modulus(ss_curve_files[0], loop)
    if elas is None:
        logger.error(f"無法計算楊氏模數在目錄 {temp_dir}")
        return None
    
    # 根據x_dir設定對應的Elas變數
    result[f'Elas_{x_dir}'] = elas
    logger.info(f"計算得到 Elas_{x_dir} = {elas}")
    
    # 2. 讀取SNAP參數
    element_params = read_snap_with_regex(snapcoeff_path)
    
    if not element_params:
        logger.error(f"無法讀取SNAP參數從 {snapcoeff_path}")
        return None
    
    # 3. 設定元素參數
    elements = ['Ni', 'Co', 'Ti', 'Zr', 'Hf']
    for element in elements:
        if element in element_params:
            result[f'Rad_{element}'] = element_params[element][0]
            result[f'Ew_{element}'] = element_params[element][1]
        else:
            result[f'Rad_{element}'] = None
            result[f'Ew_{element}'] = None
    
    return result
def process_temperature_directory(temp_dir, x_dir, type_num='1'):
    """處理單個溫度目錄 (Type 1)"""
    result = {'Type': type_num, 'x_dir': x_dir, 'temp_dir': temp_dir}
    
    # 1. 查找不帶有.var.的in.compress文件並提取loop和snapcoeff路徑
    compress_files = glob.glob(os.path.join(temp_dir, '*in.compress*'))
    # 過濾掉檔名中包含 .var. 的文件（注意是 .var. 不是 var）
    compress_files = [f for f in compress_files if '.var.' not in os.path.basename(f)]
    
    loop = None
    for compress_file in compress_files:
        loop = extract_loop_from_compress_file(compress_file)
        if loop:
            break
    
    if not loop:
        logger.error(f"未找到loop值在目錄 {temp_dir}")
        return None
    
    logger.info(f"找到loop值: {loop}")

    snapcoeff_path = None
    for compress_file in compress_files:
        snapcoeff_path = extract_snapcoeff_path(compress_file)
        if snapcoeff_path:
            break
    
    if not snapcoeff_path:
        logger.error(f"未找到snapcoeff路徑在目錄 {temp_dir}")
        return None
    
    logger.info(f"找到snapcoeff路徑: {snapcoeff_path}")
    
    # 2. 查找SS_curve文件並計算楊氏模數
    ss_curve_files = glob.glob(os.path.join(temp_dir, '*SS_curve*'))
    
    if not ss_curve_files:
        logger.error(f"未找到SS_curve文件在目錄 {temp_dir}")
        return None
    
    elas = calculate_youngs_modulus(ss_curve_files[0], loop)
    if elas is None:
        logger.error(f"無法計算楊氏模數在目錄 {temp_dir}")
        return None
    
    # 根據x_dir設定對應的Elas變數
    result[f'Elas_{x_dir}'] = elas
    logger.info(f"計算得到 Elas_{x_dir} = {elas}")
    
    # 3. 讀取SNAP參數
    element_params = read_snap_with_regex(snapcoeff_path)
    
    if not element_params:
        logger.error(f"無法讀取SNAP參數從 {snapcoeff_path}")
        return None
    
    # 4. 設定元素參數
    elements = ['Ni', 'Co', 'Ti', 'Zr', 'Hf']
    for element in elements:
        if element in element_params:
            result[f'Rad_{element}'] = element_params[element][0]
            result[f'Ew_{element}'] = element_params[element][1]
        else:
            result[f'Rad_{element}'] = None
            result[f'Ew_{element}'] = None
    
    return result

def check_and_update_database(results, db_file='hea_database.csv'):
    """檢查並更新數據庫"""
    duplicate_log = []
    
    # 讀取現有數據庫，如果不存在則創建
    try:
        df = pd.read_csv(db_file)
    except FileNotFoundError:
        logger.info(f"數據庫文件 {db_file} 不存在，將創建新文件")
        df = pd.DataFrame()
    
    # 定義用於比較的欄位（除了Elas_100和Elas_111）
    compare_columns = ['Type', 'Rad_Ni', 'Rad_Co', 'Rad_Ti', 'Rad_Zr', 'Rad_Hf', 
                      'Ew_Ni', 'Ew_Co', 'Ew_Ti', 'Ew_Zr', 'Ew_Hf']
    
    for result in results:
        x_dir = result['x_dir']
        elas_column = f'Elas_{x_dir}'
        
        # 檢查是否有相同參數的行
        if not df.empty:
            # 創建比較條件
            mask = pd.Series([True] * len(df))
            for col in compare_columns:
                if col in df.columns and result[col] is not None:
                    mask &= (df[col] == result[col])
            
            matching_rows = df[mask]
            
            if not matching_rows.empty:
                # 找到匹配的行
                for idx, row in matching_rows.iterrows():
                    if pd.notna(row.get(elas_column)):
                        # Elas值已存在，記錄到log
                        log_entry = {
                            'timestamp': datetime.now().isoformat(),
                            'directory': result['temp_dir'],
                            'x_dir': x_dir,
                            'existing_elas': row[elas_column],
                            'new_elas': result[elas_column],
                            'action': 'duplicate_found'
                        }
                        duplicate_log.append(log_entry)
                        logger.warning(f"發現重複數據: {result['temp_dir']}")
                    else:
                        # Elas值不存在，更新
                        df.at[idx, elas_column] = result[elas_column]
                        logger.info(f"更新現有行的 {elas_column}: {result[elas_column]}")
                continue
        
        # 沒有找到匹配的行，添加新行
        new_row = {col: result.get(col) for col in compare_columns}
        new_row[elas_column] = result[elas_column]
        
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        logger.info(f"添加新行: {result['temp_dir']}")
    
    # 保存數據庫
    df.to_csv(db_file, index=False)
    logger.info(f"數據庫已保存到 {db_file}")
    
    # 寫入重複記錄日誌
    if duplicate_log:
        log_df = pd.DataFrame(duplicate_log)
        log_file = f'duplicate_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        log_df.to_csv(log_file, index=False)
        logger.info(f"重複記錄已保存到 {log_file}")
    
    return df, duplicate_log

def main():
    """主函數"""
    base_dir = './compress'  # 修改為您的實際路徑
    
    if not os.path.exists(base_dir):
        logger.error(f"基礎目錄不存在: {base_dir}")
        return
    
    logger.info("開始處理數據...")
    
    # 處理所有目錄
    results = process_directory(base_dir)
    
    if not results:
        logger.error("沒有找到任何有效的結果")
        return
    
    logger.info(f"成功處理 {len(results)} 個目錄")
    
    # 檢查並更新數據庫
    df, duplicate_log = check_and_update_database(results)
    
    logger.info("處理完成!")
    logger.info(f"數據庫總行數: {len(df)}")
    logger.info(f"發現重複項目: {len(duplicate_log)}")

if __name__ == "__main__":
    main()