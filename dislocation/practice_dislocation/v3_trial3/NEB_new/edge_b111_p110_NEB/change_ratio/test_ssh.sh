ssh amd01 << 'EOF'
cd dislocation/practice_dislocation/v3_trial3/NEB_new/edge_b111_p110_NEB/change_ratio
echo "start running"

# 載入 conda 環境
source /home/jhenyu/anaconda3/etc/profile.d/conda.sh
conda activate base

# 驗證 Python 環境
echo "Using Python: $(which python)"
python -c "import ase; print('ASE imported successfully')" || echo "ASE import failed"

nohup mpirun -np 64 python align_mpi.py > stdout_test_align &
echo "end running"
EOF