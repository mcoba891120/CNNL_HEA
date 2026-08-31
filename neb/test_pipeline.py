#!/usr/bin/env python3
"""
Test script for NEB pipeline without actually submitting SLURM jobs
"""

import sys
from pathlib import Path
from run_neb_pipeline import (
    read_lattice_params, modify_build_file, modify_in_min, modify_in_neb,
    process_final_cfg, setup_work_directory, SLIP_SYSTEM_MAPPING
)

def test_pipeline_setup():
    """Test the pipeline setup for a specific slip system and sample."""
    
    slip_system = "edge_b100_p100_300K"
    sample = "sample1"
    
    print(f"Testing pipeline setup for {slip_system}/{sample}")
    print("=" * 50)
    
    # Get slip system info
    if slip_system not in SLIP_SYSTEM_MAPPING:
        print(f"ERROR: Unknown slip system: {slip_system}")
        return False
    
    dislocation_type, orientation = SLIP_SYSTEM_MAPPING[slip_system]
    print(f"Dislocation type: {dislocation_type}")
    print(f"Orientation: {orientation}")
    
    try:
        # Setup directories
        work_dir, standard_model_path, after_relax_path = setup_work_directory(
            slip_system, sample, dislocation_type, orientation
        )
        print(f"Work directory: {work_dir}")
        print(f"Standard model: {standard_model_path}")
        print(f"After relax: {after_relax_path}")
        
        # Read lattice parameters
        bulk_lx, bulk_ly, bulk_lz = read_lattice_params(after_relax_path)
        print(f"Lattice parameters: lx={bulk_lx:.6f}, ly={bulk_ly:.6f}, lz={bulk_lz:.6f}")
        
        # Test build file modification
        build_file = f"in.build_{dislocation_type}"
        template_build = Path("in.build_edge")  # Use existing template
        output_build = work_dir / build_file
        
        modify_build_file(
            template_build, output_build, standard_model_path,
            bulk_lx, bulk_ly, bulk_lz, dislocation_type
        )
        print(f"Build file created: {output_build}")
        
        # Test in.min modification
        template_min = Path("in.min")
        output_min = work_dir / "in.min"
        modify_in_min(template_min, output_min)
        print(f"in.min created: {output_min}")
        
        # Test in.neb modification
        template_neb = Path("in.neb")
        output_neb = work_dir / "in.neb"
        modify_in_neb(template_neb, output_neb, u_value=21)
        print(f"in.neb created: {output_neb}")
        
        # Check if all required files exist
        required_files = [
            "align_mpi_edge.py", "align_mpi_screw.py", "gen_aligned_structure.py",
            "../potentials/HEA_v3_trial3.snapcoeff", "../potentials/HEA_v3_trial3.snapparam"
        ]
        
        print("\nChecking required files:")
        all_files_exist = True
        for file_path in required_files:
            if Path(file_path).exists():
                print(f"✓ {file_path}")
            else:
                print(f"✗ {file_path}")
                all_files_exist = False
        
        if all_files_exist:
            print("\n✓ All required files found!")
            return True
        else:
            print("\n✗ Some required files missing!")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_all_slip_systems():
    """Test setup for all slip systems."""
    
    print("Testing all slip systems:")
    print("=" * 50)
    
    for slip_system in SLIP_SYSTEM_MAPPING.keys():
        print(f"\nTesting {slip_system}...")
        try:
            dislocation_type, orientation = SLIP_SYSTEM_MAPPING[slip_system]
            work_dir, standard_model_path, after_relax_path = setup_work_directory(
                slip_system, "sample1", dislocation_type, orientation
            )
            print(f"  ✓ {slip_system} -> {dislocation_type}/{orientation}")
        except Exception as e:
            print(f"  ✗ {slip_system}: {e}")

if __name__ == "__main__":
    print("NEB Pipeline Test Script")
    print("=" * 50)
    
    # Test basic setup
    success = test_pipeline_setup()
    
    if success:
        print("\n" + "=" * 50)
        test_all_slip_systems()
        print("\n✓ Pipeline test completed successfully!")
    else:
        print("\n✗ Pipeline test failed!")
        sys.exit(1)



