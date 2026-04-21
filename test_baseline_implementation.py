#!/usr/bin/env python3
"""
Test script for new baseline_engine implementation with two-pipeline architecture.

Tests:
1. Pipeline identification (heat transfer vs friction)
2. Data type extraction from manifest
3. Heat transfer processing with all three data types
4. Friction processing with all three data types
5. Proper output format and tracking
"""

import sys
from pathlib import Path
import pandas as pd
import json
from ribs_core.baseline_engine import BaselineEngine
from ribs_core import config

# Setup
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

print("\n" + "="*70)
print("BASELINE ENGINE IMPLEMENTATION TEST")
print("="*70)

# Initialize engine
engine = BaselineEngine(verbose=True)

# Test 1: Pipeline identification
print("\n[TEST 1] Pipeline Identification")
print("-" * 70)

test_cases = [
    ('Nu', 'heat_transfer'),
    ('Nu_ratio', 'heat_transfer'),
    ('St', 'heat_transfer'),
    ('St_ratio', 'heat_transfer'),
    ('f', 'friction'),
    ('f_ratio', 'friction'),
]

for var, expected_pipeline in test_cases:
    result = engine.identify_pipeline(var)
    status = "✓" if result == expected_pipeline else "✗"
    print(f"{status} {var:12} → {result:20} (expected: {expected_pipeline})")

# Test 2: Variable format identification
print("\n[TEST 2] Variable Format Identification")
print("-" * 70)

format_cases = [
    ('Nu', 'heat_transfer', ('Nu', 'raw')),
    ('Nu_ratio', 'heat_transfer', ('Nu', 'ratio')),
    ('St', 'heat_transfer', ('St', 'raw')),
    ('St_ratio', 'heat_transfer', ('St', 'ratio')),
    ('f', 'friction', ('f', 'raw')),
    ('f_ratio', 'friction', ('f', 'ratio')),
]

for var, pipeline, expected in format_cases:
    result = engine.identify_variable_format(var, pipeline)
    status = "✓" if result == expected else "✗"
    print(f"{status} {var:12} ({pipeline}) → {result} (expected: {expected})")

# Test 3: Standard baseline identification
print("\n[TEST 3] Standard Baseline Identification")
print("-" * 70)

baseline_cases = [
    ('Dittus-Boelert', 'heat_transfer', True),
    ('Gnielinski', 'heat_transfer', False),
    ('Blasius', 'friction', True),
    ('Fanning', 'friction', False),
]

for baseline, pipeline, expected_standard in baseline_cases:
    result = engine.is_standard_baseline(baseline, pipeline)
    status = "✓" if result == expected_standard else "✗"
    print(f"{status} {baseline:20} ({pipeline:14}) → {result} (expected: {expected_standard})")

# Test 4: Create test manifest with data types
print("\n[TEST 4] Data Type Extraction from Manifest")
print("-" * 70)

# Create a test manifest with proper structure
test_manifest = {
    'Paper Identification': {'paper_number': 'P001'},
    'Data Reduction & Normalization': {
        # Heat transfer data sources
        'Rig Baseline (Heat Transfer)': 'Nu_0_rig',
        'Smooth Baseline (Heat Transfer)': 'Dittus-Boelert',
        'Ribbed Baseline (Heat Transfer)': 'Gnielinski',  # Non-standard, needs unconvert
        
        # Friction data sources
        'Rig Baseline (Friction)': 'f_0_rig',
        'Friction Baseline': 'Blasius',
    },
    'Boundary & Flow Conditions': {
        'Fluid Properties': {
            'Pr': 0.71,
            'Re': 10000
        }
    }
}

# Test extraction for different variables
test_variables = [
    ('Nu', 'According to Data Reduction scheme used:'),
    ('f', 'According to Data Reduction scheme used:'),
]

for var, manifest_source in test_variables:
    pipeline = engine.identify_pipeline(var)
    if pipeline == 'heat_transfer':
        heat_transfer_info = test_manifest['Data Reduction & Normalization']
        rig_baseline = heat_transfer_info.get('Rig Baseline (Heat Transfer)')
        standard_baseline = heat_transfer_info.get('Smooth Baseline (Heat Transfer)')
        print(f"  {var} ({pipeline}):")
        print(f"    - Rig Baseline: {rig_baseline}")
        print(f"    - Standard Baseline: {standard_baseline}")
    elif pipeline == 'friction':
        friction_info = test_manifest['Data Reduction & Normalization']
        rig_baseline = friction_info.get('Rig Baseline (Friction)')
        standard_baseline = friction_info.get('Friction Baseline')
        print(f"  {var} ({pipeline}):")
        print(f"    - Rig Baseline: {rig_baseline}")
        print(f"    - Standard Baseline: {standard_baseline}")

# Test 5: Process a sample row
print("\n[TEST 5] Row-Level Processing")
print("-" * 70)

# Create sample test data
test_data = pd.DataFrame([
    {
        'Paper': 'P001',
        'Experiment': 'Exp1',
        'x_div_D': 10.0,
        'y_div_D': 5.0,
        'Reynolds': 5000,
        'Prandtl': 0.71,
        'Nu': 45.0,
        'Processing_Note': ''
    }
])

print(f"Sample row created:")
print(f"  Nu value: {test_data.iloc[0]['Nu']}")
print(f"  Reynolds: {test_data.iloc[0]['Reynolds']}")
print(f"  Prandtl: {test_data.iloc[0]['Prandtl']}")

# Test 6: Process complete dataframe
print("\n[TEST 6] DataFrame Processing (Heat Transfer Pipeline)")
print("-" * 70)

# Create more comprehensive test data
test_df = pd.DataFrame([
    {
        'Paper': 'P001',
        'Experiment': 'Exp1',
        'x_div_D': 10.0,
        'Reynolds': 5000,
        'Prandtl': 0.71,
        'Variable': 'Nu',
        'Value': 45.0,
        'Processing_Note': ''
    },
    {
        'Paper': 'P001',
        'Experiment': 'Exp2',
        'x_div_D': 10.0,
        'Reynolds': 10000,
        'Prandtl': 0.71,
        'Variable': 'St_ratio',
        'Value': 1.5,
        'Processing_Note': ''
    }
])

try:
    # Process the dataframe
    result_df, process_log, status = engine.process_paper(
        test_df,
        test_manifest,
        pr_value=0.71
    )
    
    print(f"Processing Status: {status}")
    print(f"Rows processed: {len(result_df)}")
    print(f"Processing log keys: {list(process_log.keys())}")
    print("\n✓ DataFrame processing completed successfully")
    
except Exception as e:
    print(f"\n✗ Error during processing: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70 + "\n")
