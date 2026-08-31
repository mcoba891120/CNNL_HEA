# NEB Workflow Complete Guide

本指南介绍完整的NEB研究流程，包括初始NEB计算、Post-NEB能量分析和Next/Refinement迭代。

---

## 📋 目录

1. [快速开始](#快速开始)
2. [工作流程概览](#工作流程概览)
3. [详细使用说明](#详细使用说明)
4. [配置文件](#配置文件)
5. [输出文件说明](#输出文件说明)
6. [故障排除](#故障排除)

---

## 快速开始

### 1. 初始NEB计算

```bash
# 单个slip system
python3 run_neb_pipeline.py --slip edge_b100_p100_300K --sample sample1

# 所有slip systems (并行6个)
python3 run_neb_pipeline.py --all

# 本地测试
python3 run_neb_pipeline.py --slip edge_b100_p100_300K --sample sample1 --local
```

### 2. Post-NEB Minimize与能量分析

```bash
# 对所有neb_*.data进行minimize并生成能量图
python3 run_neb_pipeline.py --post-minimize \
    --slip edge_b100_p100_300K --sample sample1

# 检查哪些目录需要minimize
python3 run_neb_pipeline.py --check-minimize
```

### 3. Next/Refinement迭代

```bash
# 单个refinement (使用neb_5和neb_7之间做15个loops的NEB)
python3 run_neb_pipeline.py --next \
    --slip edge_b100_p100_300K --sample sample1 \
    --start 5 --end 7 --loops 15

# 批量refinement (从JSON配置)
python3 run_neb_pipeline.py --next-batch next_config.json
```

---

## 工作流程概览

### 完整研究流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    Step 1: 初始NEB计算                           │
│  build → minimize → align → gen_aligned → pre-NEB min → NEB    │
│  输出: neb_1.data, neb_2.data, ..., neb_21.data                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              Step 2: Post-NEB Minimize & 能量分析                │
│  对每个 neb_*.data 进行 minimize                                 │
│  提取 final energy → 归一化 (energy / box_dimension)            │
│  输出: minimize/energy_plot.png                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Step 3: 分析能量曲线                          │
│  查看 energy_plot.png，找出需要refinement的区间                 │
│  例如: neb_5 到 neb_7 之间能量变化大，需要细化                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                 Step 4: Next/Refinement迭代                     │
│  复制 neb_5.data, neb_7.data → next_1/                         │
│  pre-NEB minimize → NEB (15 loops) → post-NEB minimize         │
│  输出: next_1/minimize/energy_plot.png                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              Step 5: 重复refinement (如需要)                     │
│  分析 next_1 的能量曲线，继续细化 → next_2, next_3, ...        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 详细使用说明

### 🔹 初始NEB计算

#### 命令行选项

| 选项 | 说明 | 示例 |
|------|------|------|
| `--slip` | Slip system名称 | `edge_b100_p100_300K` |
| `--sample` | Sample名称 | `sample1` |
| `--account` | SLURM账户 | `MST114385` (默认) |
| `--all` | 运行所有slip systems | - |
| `--local` | 本地运行 (不使用SLURM) | - |
| `--workers` | 并行worker数量 | `6` (默认自动计算) |
| `--skip-build` | 跳过build步骤 | - |

#### 输出目录结构

```
edge_b100_p100_300K/
└── sample1/
    ├── in.build_edge
    ├── in.min
    ├── in.neb
    ├── align_mpi.py
    ├── gen_aligned_structure.py
    ├── neb_1.data        # NEB生成的结构
    ├── neb_2.data
    ├── ...
    └── neb_21.data
```

---

### 🔹 Post-NEB Minimize

#### 功能说明

对所有 `neb_*.data` 文件进行minimize，提取能量并生成可视化图表。

#### 能量归一化

- **Edge类型**: `Energy / yhi` (Y方向盒子尺寸)
- **Screw类型**: `Energy / xhi` (X方向盒子尺寸)

这样可以消除不同体系尺寸的影响，更好地比较能量差异。

#### 命令示例

```bash
# 基本用法
python3 run_neb_pipeline.py --post-minimize \
    --slip edge_b100_p100_300K --sample sample1

# 本地运行
python3 run_neb_pipeline.py --post-minimize \
    --slip edge_b100_p100_300K --sample sample1 --local

# 强制重新minimize (即使已存在minimize目录)
python3 run_neb_pipeline.py --post-minimize \
    --slip edge_b100_p100_300K --sample sample1 --force-reminimize
```

#### 输出目录结构

```
edge_b100_p100_300K/
└── sample1/
    ├── neb_1.data, neb_2.data, ...
    └── minimize/
        ├── neb_1/
        │   ├── neb_1.data       # 复制的输入文件
        │   ├── in.min           # Minimize输入脚本
        │   └── STDOUT_min       # 输出 (包含能量)
        ├── neb_2/
        ├── ...
        └── energy_plot.png      # 能量图 (PNG格式, 300 DPI)
```

#### 能量图说明

- **X轴**: NEB image编号 (1, 2, 3, ...)
- **Y轴**: 归一化能量 (eV/Å)
- **绿色三角**: 最低能量点
- **红色三角**: 最高能量点 (transition state)
- **连线**: 显示能量路径

---

### 🔹 检查Minimize状态

检查哪些slip system/sample已经有minimize目录，哪些还需要处理。

```bash
# 检查所有
python3 run_neb_pipeline.py --check-minimize

# 检查特定slip system
python3 run_neb_pipeline.py --check-minimize --slip edge_b100_p100_300K

# 检查特定sample
python3 run_neb_pipeline.py --check-minimize \
    --slip edge_b100_p100_300K --sample sample1
```

#### 输出示例

```
============================================================
MINIMIZE STATUS CHECK
============================================================

✓ edge_b100_p100_300K/sample1: minimize folder exists
✗ edge_b100_p100_300K/sample2: NO minimize folder
✓ edge_b100_p100_300K/sample1/next_1: minimize folder exists
✗ screw_b111_p110_330K/sample1: NO minimize folder
```

---

### 🔹 Next/Refinement迭代

#### 功能说明

对NEB路径的某一段进行细化，在两个现有的 `neb_X.data` 结构之间重新计算更精细的NEB路径。

#### 单个Next操作

```bash
python3 run_neb_pipeline.py --next \
    --slip edge_b100_p100_300K \
    --sample sample1 \
    --start 5 \           # 使用 neb_5.data 作为初始结构
    --end 7 \             # 使用 neb_7.data 作为最终结构
    --loops 15            # 新NEB计算15个loops
```

#### 流程说明

1. **自动创建目录**: `next_1/` (如果已有next_1，则创建next_2，依此类推)
2. **复制结构**: 
   - `neb_5.data` → `next_1/HEA_init_next1.data`
   - `neb_7.data` → `next_1/HEA_init_next2.data`
3. **Pre-NEB minimize**: 对这两个结构进行minimize
4. **NEB计算**: 在minimize后的结构之间进行NEB (15个loops)
5. **Post-NEB minimize**: 对所有生成的 `neb_*.data` 进行minimize
6. **绘图**: 生成 `next_1/minimize/energy_plot.png`

#### 输出目录结构

```
edge_b100_p100_300K/
└── sample1/
    ├── neb_1.data, ..., neb_21.data
    ├── minimize/
    │   └── energy_plot.png
    └── next_1/
        ├── HEA_init_next1.data
        ├── HEA_init_next2.data
        ├── HEA_opt_next1.data      # Minimized初始结构
        ├── HEA_opt_next2.data      # Minimized最终结构
        ├── final.cfg, final.txt
        ├── in.min, in.neb
        ├── neb_1.data, ..., neb_15.data
        └── minimize/
            ├── neb_1/, neb_2/, ...
            └── energy_plot.png
```

---

### 🔹 批量Next操作

使用JSON配置文件批量处理多个slip system的refinement。

#### 创建配置文件 (`my_next_jobs.json`)

```json
{
  "next_jobs": [
    {
      "slip_system": "edge_b100_p100_300K",
      "sample": "sample1",
      "start": 5,
      "end": 7,
      "loops": 15,
      "account": "MST114385"
    },
    {
      "slip_system": "edge_b100_p110_300K",
      "sample": "sample1",
      "start": 3,
      "end": 8,
      "loops": 12,
      "account": "MST114385"
    },
    {
      "slip_system": "screw_b111_p110_330K",
      "sample": "sample1",
      "start": 10,
      "end": 15,
      "loops": 20,
      "account": "MST114385"
    }
  ]
}
```

#### 运行批量Next

```bash
python3 run_neb_pipeline.py --next-batch my_next_jobs.json

# 本地模式
python3 run_neb_pipeline.py --next-batch my_next_jobs.json --local
```

#### 输出摘要

```
============================================================
Running job 1/3: edge_b100_p100_300K/sample1
  Start: neb_5, End: neb_7, Loops: 15
============================================================
...

============================================================
BATCH NEXT SUMMARY
============================================================
Total jobs: 3
Successful: 2
Failed: 1

✓ SUCCESSFUL:
  edge_b100_p100_300K/sample1
  edge_b100_p110_300K/sample1

✗ FAILED:
  screw_b111_p110_330K/sample1: neb_10.data not found
```

---

## 配置文件

### SLURM配置

脚本会根据核心数自动选择partition：

| Cores | Partition | 说明 |
|-------|-----------|------|
| 1-112 | ct112 | 单节点任务 |
| 113-448 | ct448 | 中等任务 |
| 449-1120 | ct1k | 大型任务 (NEB: 168 cores) |
| 1121-2240 | ct2k | 超大任务 |

### 核心分配

| 步骤 | 核心数 | Partition |
|------|--------|-----------|
| Build | 1 | ct112 |
| Align | 64 | ct112 |
| Gen Aligned | 1 | ct112 |
| Pre-NEB Minimize | 64 | ct112 |
| NEB | 168 | ct1k |
| Post-NEB Minimize | 64 (每个) | ct112 |

---

## 输出文件说明

### 能量图 (`energy_plot.png`)

- **格式**: PNG
- **分辨率**: 300 DPI
- **内容**:
  - 蓝色圆点+连线: 完整能量路径
  - 绿色下三角: 最低能量点 (稳定态)
  - 红色上三角: 最高能量点 (过渡态)
  - 图例显示min/max的具体能量值

### STDOUT文件

#### `STDOUT_min` (Post-NEB Minimize)

关键信息：
```
Energy initial, next-to-last, final = 
   -1301827.88045953  -1301838.65309953  -1301838.65344395
```
- 第三个值 (`-1301838.65344395`) 是最终能量
- 脚本会自动提取并归一化

#### `STDOUT_neb`

关键信息：
```
Total wall time: 0:05:23
```
- 用于判断NEB是否完成

---

## 故障排除

### 问题1: matplotlib未安装

**错误**:
```
Error: matplotlib not available
```

**解决**:
```bash
pip install matplotlib
```

### 问题2: Minimize目录已存在

**错误**:
```
Minimize directory already exists: .../minimize
Skipping post-NEB minimize
```

**解决**:
```bash
# 删除旧的minimize目录
rm -rf edge_b100_p100_300K/sample1/minimize

# 或使用 --force-reminimize
python3 run_neb_pipeline.py --post-minimize \
    --slip edge_b100_p100_300K --sample sample1 --force-reminimize
```

### 问题3: 找不到neb_*.data文件

**错误**:
```
Error: .../neb_5.data not found
```

**解决**:
- 确认NEB计算已完成
- 检查文件名是否正确 (应该是 `neb_5.data` 而不是 `neb_05.data`)

### 问题4: 能量提取失败

**错误**:
```
Warning: Could not extract energy for neb_5
```

**解决**:
- 检查 `STDOUT_min` 是否包含 "Energy initial, next-to-last, final"
- 确认minimize是否完成 (可能提前终止)

### 问题5: SLURM作业失败

**症状**: 作业提交后立即失败

**检查**:
```bash
# 查看SLURM错误日志
cat edge_b100_p100_300K/sample1/minimize/neb_5/job-*.err

# 查看SLURM输出日志
cat edge_b100_p100_300K/sample1/minimize/neb_5/job-*.out
```

---

## 高级用法

### 自定义工作流

#### 只做minimize，不绘图

修改代码或手动运行：
```bash
cd edge_b100_p100_300K/sample1/minimize/neb_5
sbatch submit_min_neb_5.sh
```

#### 重新绘图 (不重新minimize)

```python
from pathlib import Path
from run_neb_pipeline import collect_neb_energies, plot_energy_path

minimize_dir = Path("edge_b100_p100_300K/sample1/minimize")
slip_type = "edge"

energies = collect_neb_energies(minimize_dir, slip_type)
plot_energy_path(energies, minimize_dir / "energy_plot_custom.png", 
                "edge_b100_p100_300K", "sample1", slip_type)
```

### 提取所有能量到CSV

```python
import csv
from run_neb_pipeline import collect_neb_energies
from pathlib import Path

minimize_dir = Path("edge_b100_p100_300K/sample1/minimize")
energies = collect_neb_energies(minimize_dir, "edge")

with open("energies.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["NEB_Number", "Raw_Energy", "Normalized_Energy"])
    for neb_num, (raw, norm) in sorted(energies.items()):
        writer.writerow([neb_num, raw, norm])
```

---

## 总结

完整的NEB研究流程：

1. ✅ **初始NEB**: `--all` 或 `--slip ... --sample ...`
2. ✅ **Post-NEB Minimize**: `--post-minimize`
3. ✅ **分析能量图**: 查看 `minimize/energy_plot.png`
4. ✅ **Refinement**: `--next --start X --end Y --loops Z`
5. ✅ **重复**: 根据需要继续refinement

所有步骤都支持SLURM和本地模式，自动化程度高，只需简单的命令行即可完成复杂的计算流程！



