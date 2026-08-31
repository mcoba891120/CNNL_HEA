# NEB Pipeline - Quick Reference

## 📋 常用命令速查

### 🔹 初始NEB计算

```bash
# 单个slip system
python3 run_neb_pipeline.py --slip edge_b100_p100_300K --sample sample1

# 所有slip systems (6个并行)
python3 run_neb_pipeline.py --all

# 本地测试
python3 run_neb_pipeline.py --slip edge_b100_p100_300K --sample sample1 --local
```

### 🔹 Post-NEB Minimize

```bash
# 单个slip system
python3 run_neb_pipeline.py --post-minimize \
    --slip edge_b100_p100_300K --sample sample1

# 所有slip systems (一次性处理)
python3 run_neb_pipeline.py --post-minimize-all

# 检查minimize状态
python3 run_neb_pipeline.py --check-minimize

# 强制重新minimize所有
python3 run_neb_pipeline.py --post-minimize-all --force-reminimize
```

### 🔹 Next/Refinement

```bash
# 单个refinement
python3 run_neb_pipeline.py --next \
    --slip edge_b100_p100_300K --sample sample1 \
    --start 5 --end 7 --loops 15

# 批量refinement
python3 run_neb_pipeline.py --next-batch config.json
```

---

## 📁 输出文件位置

```
slip_system/
└── sample/
    ├── neb_1.data, neb_2.data, ...           # NEB生成的结构
    ├── minimize/                              # Post-NEB minimize
    │   ├── neb_1/, neb_2/, ...
    │   └── energy_plot.png                   # ← 能量图在这里
    └── next_1/                                # Refinement
        ├── neb_1.data, neb_2.data, ...
        └── minimize/
            └── energy_plot.png               # ← Next的能量图
```

---

## 🎯 典型工作流

### 方式1: 单个slip system
```bash
# 1. 运行初始NEB
python3 run_neb_pipeline.py --slip edge_b100_p100_300K --sample sample1

# 2. Post-NEB minimize并绘图
python3 run_neb_pipeline.py --post-minimize \
    --slip edge_b100_p100_300K --sample sample1

# 3. 查看能量图 (找到需要refinement的区间)
# 打开: edge_b100_p100_300K/sample1/minimize/energy_plot.png

# 4. Refinement (假设neb_5到neb_7能量变化大)
python3 run_neb_pipeline.py --next \
    --slip edge_b100_p100_300K --sample sample1 \
    --start 5 --end 7 --loops 15

# 5. 查看refinement结果
# 打开: edge_b100_p100_300K/sample1/next_1/minimize/energy_plot.png
```

### 方式2: 批量处理 (推荐)
```bash
# 1. 所有slip systems的初始NEB
python3 run_neb_pipeline.py --all

# 2. 检查状态
python3 run_neb_pipeline.py --check-minimize

# 3. 一次性Post-NEB minimize所有
python3 run_neb_pipeline.py --post-minimize-all

# 4. 查看所有能量图，决定哪些需要refinement
# edge_b100_p100_300K/sample1/minimize/energy_plot.png
# edge_b100_p110_300K/sample1/minimize/energy_plot.png
# ...

# 5. 批量refinement (使用JSON配置)
python3 run_neb_pipeline.py --next-batch my_config.json
```

---

## 🔧 JSON配置示例

`my_config.json`:
```json
{
  "next_jobs": [
    {
      "slip_system": "edge_b100_p100_300K",
      "sample": "sample1",
      "start": 5,
      "end": 7,
      "loops": 15
    }
  ]
}
```

运行:
```bash
python3 run_neb_pipeline.py --next-batch my_config.json
```

---

## 📊 能量归一化

- **Edge类型**: Energy / yhi (Y方向盒子尺寸)
- **Screw类型**: Energy / xhi (X方向盒子尺寸)

能量图的Y轴单位: `eV/Å`

---

## ⚙️ 核心配置

### 核心数分配

| 步骤 | 核心数 | Partition |
|------|--------|-----------|
| Build | 1 | ct112 |
| Align | 64 | ct112 |
| Pre-NEB Minimize | 64 | ct112 |
| NEB | 168 | ct1k |
| Post-NEB Minimize | 64 | ct112 |

### LAMMPS可执行文件

- **SLURM**: `/home/u6710794/lammps-stable_29Aug2024_update3/src/lmp_intel_cpu_intelmpi`
- **Local**: `~/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100`

---

## 🐛 常见问题

### 问题: matplotlib未安装
```bash
pip install matplotlib
```

### 问题: Minimize目录已存在
```bash
# 删除旧目录
rm -rf slip_system/sample/minimize

# 或使用 --force-reminimize
python3 run_neb_pipeline.py --post-minimize ... --force-reminimize
```

### 问题: 找不到neb_*.data
- 确认NEB已完成
- 检查文件名 (应为 `neb_5.data` 而非 `neb_05.data`)

---

## 📚 详细文档

- `NEB_WORKFLOW_GUIDE.md`: 完整工作流程指南
- `IMPLEMENTATION_SUMMARY.md`: 实施总结
- `README_pipeline.md`: 原始pipeline文档

---

## 🆘 获取帮助

```bash
python3 run_neb_pipeline.py --help
```

---

## 📝 文件清单

### 模板文件
- `templates/in.min.post_neb`: Post-NEB minimize模板
- `templates/in.min.next`: Next Pre-NEB minimize模板
- `templates/in.neb.next`: Next NEB模板

### 配置文件
- `next_config_example.json`: JSON配置示例

### 脚本
- `run_neb_pipeline.py`: 主脚本 (已扩展)

### 文档
- `NEB_WORKFLOW_GUIDE.md`: 工作流程指南
- `IMPLEMENTATION_SUMMARY.md`: 实施总结
- `QUICK_REFERENCE.md`: 本文件

