#!/usr/bin/env python3
"""
Process P002 through the complete preprocessing pipeline.

Mimics the main preprocessor but runs on P002 only.
Outputs:
- P002_clean_data.csv (main output with schema and values)
- P002_clean_data_log.csv (source tracking and processing metadata)

This matches the output format of the main MetaAnalysisPreprocessor.
"""

import sys
from pathlib import Path
import pandas as pd
import json
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ribs_core.geometric_engine import GeometricEngine
from ribs_core.baseline_engine import BaselineEngine
from ribs_core.stitching_engine import StitchingEngine
from ribs_core import config

print("\n" + "="*80)
print("P002 FULL PREPROCESSING PIPELINE (Geometric + Baseline + Stitching)")
print("="*80)

# Paths
paper_dir = PROJECT_ROOT / 'Staging' / 'P002'
output_dir = Path(__file__).parent  # testing folder

print(f"\nInput : {paper_dir}")
print(f"Output: {output_dir}")

if not paper_dir.exists():
    print(f"✗ Paper directory not found: {paper_dir}")
    sys.exit(1)

if not output_dir.exists():
    print(f"✗ Output directory not found: {output_dir}")
    sys.exit(1)

try:
    print(f"\n[STEP 1] Geometric Processing...")
    print("-" * 80)
    
    # Initialize engines
    geo_engine = GeometricEngine(verbose=True)
    base_engine = BaselineEngine(verbose=True)
    stitch_engine = StitchingEngine(verbose=True)
    
    # Geometric processing
    df, geo_log = geo_engine.process_paper(paper_dir)
    print(f"✓ Geometric: Processed {len(df)} rows, {len(df.columns)} columns")
    
    # Load manifest for baseline
    manifest_path = paper_dir / 'manifest.json'
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    print(f"\n[STEP 2] Baseline Normalization...")
    print("-" * 80)
    
    # Get Prandtl number
    pr_value = None
    boundary = manifest.get('Boundary & Flow Conditions', {})
    fluid_props = boundary.get('Fluid Properties', {})
    if isinstance(fluid_props, dict):
        pr_value = fluid_props.get('Pr')
    
    if pr_value is None:
        pr_value = config.PREPROCESSOR_PRANDTL_DEFAULT
    
    df['Prandtl'] = pr_value
    
    # Baseline processing
    df, base_log, status = base_engine.process_paper(df, manifest, pr_value)
    print(f"✓ Baseline: Processed {len(df)} rows")
    
    print(f"\n[STEP 3] Stitching (Schema Standardization)...")
    print("-" * 80)
    
    # Stitch/standardize data
    main_df, log_df = stitch_engine.stitch_paper(df, paper_dir)
    print(f"✓ Stitched: {len(main_df)} rows in main, {len(log_df)} rows in log")
    
    print(f"\n[STEP 4] Saving Output CSVs...")
    print("-" * 80)
    
    # Save main CSV to testing directory
    main_output = output_dir / 'P002_clean_data.csv'
    main_df.to_csv(main_output, index=False)
    print(f"✓ Saved main: {main_output.name}")
    print(f"  Rows: {len(main_df)}, Columns: {len(main_df.columns)}")
    print(f"  Columns: {', '.join(main_df.columns[:5])}...")
    
    # Save log CSV to testing directory
    log_output = output_dir / 'P002_clean_data_log.csv'
    log_df.to_csv(log_output, index=False)
    print(f"✓ Saved log: {log_output.name}")
    print(f"  Rows: {len(log_df)}, Columns: {len(log_df.columns)}")
    print(f"  Columns: {', '.join(log_df.columns[:5])}...")
    
    print(f"\n[STEP 5] Analyzing Source Tracking...")
    print("-" * 80)
    
    # Analyze source columns for WARNING flags
    source_columns = ['P/e_Source', 'e/D_Source', 'Alpha_Source', 'Geometry_Source', 'Aspect_Ratio_Source']
    warning_found = False
    
    for src_col in source_columns:
        if src_col in log_df.columns:
            warning_count = (log_df[src_col] == 'WARNING').sum()
            if warning_count > 0:
                warning_found = True
                print(f"\n  ⚠ {src_col}: {warning_count} rows marked WARNING")
                # Show sample rows with WARNING
                warning_rows = log_df[log_df[src_col] == 'WARNING']
                print(f"    Sample rows with WARNING:")
                for idx, row in warning_rows.head(2).iterrows():
                    print(f"      Row {idx}: {row.get('Point ID', 'N/A')}")
    
    if not warning_found:
        print(f"\n  ✓ No WARNING flags found (multi-value manifest entries detected properly)")
    
    print(f"\n[SUMMARY]")
    print("-" * 80)
    print(f"✓ Pipeline Complete!")
    print(f"  Main CSV  : {main_output.name} ({len(main_df)} rows × {len(main_df.columns)} cols)")
    print(f"  Log CSV   : {log_output.name} ({len(log_df)} rows × {len(log_df.columns)} cols)")
    
    # Show source distribution
    if 'P/e_Source' in log_df.columns:
        print(f"\n  Source Distribution (P/e_Source):")
        source_dist = log_df['P/e_Source'].value_counts()
        for source, count in source_dist.items():
            pct = (count / len(log_df)) * 100
            print(f"    {source:12} : {count:4} rows ({pct:5.1f}%)")
    
    print(f"\n✓ TEST COMPLETE - Outputs in {output_dir.name}/")
    
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
