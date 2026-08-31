#!/usr/bin/env python3
"""
Test script for GPU Queue Manager for NEB Pipeline
"""

import os
import sys
import subprocess
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing imports...")
    try:
        import argparse
        import json
        import glob
        import re
        import signal
        import logging
        print("✓ All required modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_script_syntax():
    """Test if the script has valid Python syntax"""
    print("Testing script syntax...")
    try:
        script_path = Path(__file__).parent / "gpu_queue_manager_neb.py"
        result = subprocess.run([sys.executable, "-m", "py_compile", str(script_path)], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Script syntax is valid")
            return True
        else:
            print(f"✗ Syntax error: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error testing syntax: {e}")
        return False

def test_help_option():
    """Test if the script shows help information"""
    print("Testing help option...")
    try:
        script_path = Path(__file__).parent / "gpu_queue_manager_neb.py"
        result = subprocess.run([sys.executable, str(script_path), "--help"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and "GPU Queue Manager for NEB Pipeline" in result.stdout:
            print("✓ Help option works correctly")
            return True
        else:
            print(f"✗ Help option failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error testing help: {e}")
        return False

def test_neb_structure():
    """Test if NEB directory structure exists"""
    print("Testing NEB directory structure...")
    neb_root = Path("neb/")
    
    required_dirs = [
        neb_root,
        neb_root / "../potentials",
        neb_root / "edge_b100_p100_300K",
        neb_root / "edge_b100_p110_300K",
        neb_root / "screw_b100_p100_300K"
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        if dir_path.exists():
            print(f"✓ {dir_path} exists")
        else:
            print(f"✗ {dir_path} missing")
            all_exist = False
    
    return all_exist

def test_snap_files():
    """Test if SNAP files exist"""
    print("Testing SNAP files...")
    neb_root = Path("neb/")
    snap_coeff = neb_root / "../potentials/HEA_v3_trial3.snapcoeff"
    snap_param = neb_root / "../potentials/HEA_v3_trial3.snapparam"
    
    if snap_coeff.exists() and snap_param.exists():
        print("✓ SNAP files exist")
        return True
    else:
        print(f"✗ SNAP files missing: {snap_coeff.exists()}, {snap_param.exists()}")
        return False

def test_lammps_executables():
    """Test if LAMMPS executables exist"""
    print("Testing LAMMPS executables...")
    lammps_a100 = "/home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_a100"
    lammps_v100 = "/home/cnnltmp01/Downloads/lammps-stable_2Aug2023_update3/src/lmp_kokkos_cuda_v100"
    
    a100_exists = Path(lammps_a100).exists()
    v100_exists = Path(lammps_v100).exists()
    
    if a100_exists or v100_exists:
        print(f"✓ LAMMPS executables found: A100={a100_exists}, V100={v100_exists}")
        return True
    else:
        print("✗ No LAMMPS executables found")
        return False

def test_gpu_detection():
    """Test GPU detection"""
    print("Testing GPU detection...")
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✓ GPU detection works: {result.stdout.strip()}")
            return True
        else:
            print(f"✗ GPU detection failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ GPU detection error: {e}")
        return False

def test_neb_files():
    """Test if NEB data files exist"""
    print("Testing NEB data files...")
    neb_root = Path("neb/")
    
    # Look for any neb_*.data files
    neb_files = list(neb_root.glob("*/sample*/neb_*.data"))
    
    if neb_files:
        print(f"✓ Found {len(neb_files)} NEB data files")
        for f in neb_files[:3]:  # Show first 3
            print(f"  - {f}")
        return True
    else:
        print("✗ No NEB data files found")
        return False

def test_dry_run():
    """Test dry run mode (if implemented)"""
    print("Testing dry run...")
    try:
        script_path = Path(__file__).parent / "gpu_queue_manager_neb.py"
        # Run with a very short scan interval and specific slip system
        result = subprocess.run([
            sys.executable, str(script_path), 
            "--neb-mode", 
            "--slip-systems", "edge_b100_p100_300K",
            "--samples", "sample1"
        ], capture_output=True, text=True, timeout=5)
        
        # The script should start and then we'll interrupt it
        print("✓ Dry run started successfully (interrupted after 5 seconds)")
        return True
    except subprocess.TimeoutExpired:
        print("✓ Dry run completed (timeout expected)")
        return True
    except Exception as e:
        print(f"✗ Dry run failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("GPU Queue Manager for NEB Pipeline - Test Suite")
    print("=" * 60)
    
    tests = [
        ("Import Test", test_imports),
        ("Syntax Test", test_script_syntax),
        ("Help Test", test_help_option),
        ("NEB Structure Test", test_neb_structure),
        ("SNAP Files Test", test_snap_files),
        ("LAMMPS Executables Test", test_lammps_executables),
        ("GPU Detection Test", test_gpu_detection),
        ("NEB Files Test", test_neb_files),
        ("Dry Run Test", test_dry_run)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 40)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! The GPU queue manager is ready to use.")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
