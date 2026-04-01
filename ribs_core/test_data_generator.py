"""
Test Data Generator for Preprocessor Testing

Generates synthetic test papers with controlled data for validation.
Includes:
- Test paper with heat transfer data (Nu)
- Test paper with friction factor data (f)
- Test paper with varied parameters (Safety Trigger test)

Author: Meta-Analysis Preprocessor Testing
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path


def create_test_paper_heat_transfer(staging_dir: Path) -> Path:
    """
    Create test paper: Heat Transfer Analysis.
    
    Features:
    - Nu data (raw values and ratios)
    - Constant geometric parameters (W=20, H=10, e=0.5)
    - Dittus-Boelert baseline normalization
    
    Args:
        staging_dir: Staging directory path
        
    Returns:
        Path to test paper directory
    """
    paper_dir = staging_dir / 'test_paper_heat_transfer'
    paper_dir.mkdir(parents=True, exist_ok=True)
    
    # Create raw_data.csv
    raw_data = {
        'Paper Title': [
            'Test Heat Transfer Study',
        ] * 10,
        'Figure Number': [1] * 5 + [2] * 5,
        'Point ID': [f'P{i}' for i in range(10)],
        'Variable': ['Nu'] * 5 + ['Nu/Nu0'] * 5,
        'Value': [
            15.2, 18.5, 22.3, 28.7, 35.6,  # Raw Nu values
            1.2, 1.3, 1.35, 1.4, 1.45,  # Nu/Nu0 ratios
        ],
        'Reynolds number (Re)': [
            1000, 2000, 4000, 8000, 10000,  # Figure 1: Varying Re
            1000, 2000, 4000, 8000, 10000,  # Figure 2: Same Re range
        ],
        'Geometry': ['Rectangular'] * 10,
        'P/e': [5.2, 5.2, 5.2, 5.2, 5.2, 5.2, 5.2, 5.2, 5.2, 5.2],
        'e/D': ['N/A'] * 10,  # To be derived from manifest
        'Alpha': [45, 45, 45, 45, 45, 45, 45, 45, 45, 45],
        'Aspect ratio': ['N/A'] * 10,  # To be derived from manifest
        'Number of ribbed walls': [2] * 10,
        'Reading on': ['Ribbed'] * 10,
        'Constant factor': [1.0] * 10,
        'Dittus-Boelter Value': [12.5, 14.2, 16.5, 19.8, 24.6, 12.5, 14.2, 16.5, 19.8, 24.6],
    }
    
    df_raw = pd.DataFrame(raw_data)
    df_raw.to_csv(paper_dir / 'raw_data.csv', index=False)
    
    # Create manifest.json
    manifest = {
        "Paper Identification": {
            "Title": "Test Heat Transfer Study",
            "Authors/Year": "Test Author 2024",
            "Study Objective": "Test data for preprocessor validation"
        },
        "Experimental Apparatus & Dimensions": {
            "Channel Geometry": ["Rectangular Duct"],
            "Channel Dimensions": {
                "Width": [20],  # mm
                "Height": [10],  # mm
                "Length": [200]  # mm
            },
            "Hydraulic Diameter (Dh)": [None],
            "Aspect Ratio (W/H)": [None],  # To be derived: 20/10 = 2.0
            "Rib Dimensions": {
                "Width": [0.8],  # mm
                "Height": [0.5],  # mm - this is 'e'
                "Pitch": [2.6]  # mm - this is 'P'
            },
            "e/Dh": [None],  # To be derived
            "P/e": [5.2],
            "Angle of attack": [45]
        },
        "Boundary & Flow Conditions": {
            "Reynolds Number Range": [[1000, 10000]],
            "Fluid Properties": {"Pr": 0.71},
            "Thermal Boundary Condition": "Constant Heat Flux",
            "Heating Setup": "Electric heater",
            "Number of Ribbed Walls": [2],
            "Surface Curvature": "Flat"
        },
        "Data Reduction & Normalization": {
            "Smooth Baseline (Heat Transfer)": "Dittus-Boelert",
            "Smooth Baseline (Friction)": "Blasius",
            "Reported Dependent Variables": ["Nu", "Nu/Nu0"],
            "Uncertainty": "±5%"
        },
        "Figures of Interest": [1, 2]
    }
    
    with open(paper_dir / 'manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2)
    
    return paper_dir


def create_test_paper_friction(staging_dir: Path) -> Path:
    """
    Create test paper: Friction Factor Analysis.
    
    Features:
    - f data (friction factor)
    - Varied Alpha parameter (Safety Trigger test)
    - Blasius baseline normalization
    
    Args:
        staging_dir: Staging directory path
        
    Returns:
        Path to test paper directory
    """
    paper_dir = staging_dir / 'test_paper_friction'
    paper_dir.mkdir(parents=True, exist_ok=True)
    
    # Create raw_data.csv
    raw_data = {
        'Paper Title': ['Test Friction Study'] * 9,
        'Figure Number': [1] * 9,
        'Point ID': [f'P{i}' for i in range(9)],
        'Variable': ['f'] * 9,
        'Value': [
            0.032, 0.028, 0.024, 0.021, 0.019,  # Friction factor values
            0.031, 0.029, 0.025, 0.022
        ],
        'Reynolds number (Re)': [
            1000, 2000, 4000, 8000, 10000,
            1000, 2000, 4000, 8000
        ],
        'Geometry': ['Rectangular'] * 9,
        'P/e': [5.2] * 9,
        'e/D': [0.02] * 9,
        'Alpha': [
            30, 30, 30, 30, 30,  # First set: Alpha=30
            45, 45, 45, 45  # Second set: Alpha=45 (varied)
        ],
        'Aspect ratio': [2.0] * 9,
        'Number of ribbed walls': [2] * 9,
        'Reading on': ['Ribbed'] * 9,
        'Constant factor': [1.0] * 9,
        'Dittus-Boelter Value': ['N/A'] * 9,
    }
    
    df_raw = pd.DataFrame(raw_data)
    df_raw.to_csv(paper_dir / 'raw_data.csv', index=False)
    
    # Create manifest.json
    manifest = {
        "Paper Identification": {
            "Title": "Test Friction Study",
            "Authors/Year": "Test Author 2024",
            "Study Objective": "Test data with varied parameters"
        },
        "Experimental Apparatus & Dimensions": {
            "Channel Geometry": ["Rectangular Duct"],
            "Channel Dimensions": {
                "Width": [22],
                "Height": [11],
                "Length": [200]
            },
            "Hydraulic Diameter (Dh)": [14.67],  # Provided directly
            "Aspect Ratio (W/H)": [2.0],
            "Rib Dimensions": {
                "Width": [0.9],
                "Height": [0.6],
                "Pitch": [3.1]
            },
            "e/Dh": [0.041],
            "P/e": [5.167],
            "Angle of attack": [30, 45]  # VARIED - Safety Trigger test
        },
        "Boundary & Flow Conditions": {
            "Reynolds Number Range": [[1000, 10000]],
            "Fluid Properties": {"Pr": 0.71},
            "Thermal Boundary Condition": "Constant Temperature",
            "Heating Setup": "Water jacket",
            "Number of Ribbed Walls": [2],
            "Surface Curvature": "Flat"
        },
        "Data Reduction & Normalization": {
            "Smooth Baseline (Heat Transfer)": "Dittus-Boelert",
            "Smooth Baseline (Friction)": "Blasius",
            "Reported Dependent Variables": ["f"],
            "Uncertainty": "±3%"
        },
        "Figures of Interest": [1]
    }
    
    with open(paper_dir / 'manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2)
    
    return paper_dir


def create_test_paper_stanton(staging_dir: Path) -> Path:
    """
    Create test paper: Stanton Number (conversion test).
    
    Features:
    - St data (Stanton number, to be converted to Nu)
    - All geometric parameters provided
    - Tests Stanton→Nusselt conversion
    
    Args:
        staging_dir: Staging directory path
        
    Returns:
        Path to test paper directory
    """
    paper_dir = staging_dir / 'test_paper_stanton'
    paper_dir.mkdir(parents=True, exist_ok=True)
    
    # Create raw_data.csv
    raw_data = {
        'Paper Title': ['Test Stanton Study'] * 6,
        'Figure Number': [1] * 6,
        'Point ID': [f'P{i}' for i in range(6)],
        'Variable': ['St'] * 6,
        'Value': [
            0.0108, 0.0095, 0.0078, 0.0062, 0.0050, 0.0041
        ],
        'Reynolds number (Re)': [
            1000, 2000, 4000, 8000, 16000, 20000
        ],
        'Geometry': ['Triangular'] * 6,
        'P/e': [4.5] * 6,
        'e/D': [0.018] * 6,
        'Alpha': [60] * 6,
        'Aspect ratio': [1.5] * 6,
        'Number of ribbed walls': [1] * 6,
        'Reading on': ['Ribbed Side'] * 6,
        'Constant factor': [1.0] * 6,
        'Dittus-Boelter Value': ['N/A'] * 6,
    }
    
    df_raw = pd.DataFrame(raw_data)
    df_raw.to_csv(paper_dir / 'raw_data.csv', index=False)
    
    # Create manifest.json
    manifest = {
        "Paper Identification": {
            "Title": "Test Stanton Study",
            "Authors/Year": "Test Author 2024",
            "Study Objective": "Test Stanton to Nusselt conversion"
        },
        "Experimental Apparatus & Dimensions": {
            "Channel Geometry": ["Triangular"],
            "Channel Dimensions": {
                "Width": [25],
                "Height": [16.67],
                "Length": [250]
            },
            "Hydraulic Diameter (Dh)": [19.2],
            "Aspect Ratio (W/H)": [1.5],
            "Rib Dimensions": {
                "Width": [0.7],
                "Height": [0.35],
                "Pitch": [1.575]
            },
            "e/Dh": [0.018],
            "P/e": [4.5],
            "Angle of attack": [60]
        },
        "Boundary & Flow Conditions": {
            "Reynolds Number Range": [[1000, 20000]],
            "Fluid Properties": {"Pr": 0.71},
            "Thermal Boundary Condition": "Constant Heat Flux",
            "Heating Setup": "Nichrome wire",
            "Number of Ribbed Walls": [1],
            "Surface Curvature": "Flat"
        },
        "Data Reduction & Normalization": {
            "Smooth Baseline (Heat Transfer)": "Dittus-Boelert",
            "Smooth Baseline (Friction)": "Blasius",
            "Reported Dependent Variables": ["St"],
            "Uncertainty": "±4%"
        },
        "Figures of Interest": [1]
    }
    
    with open(paper_dir / 'manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2)
    
    return paper_dir


def setup_test_papers(staging_dir: Path) -> list:
    """
    Create all test papers.
    
    Args:
        staging_dir: Staging directory path
        
    Returns:
        List of created test paper directories
    """
    test_dirs = [
        create_test_paper_heat_transfer(staging_dir),
        create_test_paper_friction(staging_dir),
        create_test_paper_stanton(staging_dir),
    ]
    
    print(f"✓ Created {len(test_dirs)} test papers:")
    for test_dir in test_dirs:
        print(f"  - {test_dir.name}")
    
    return test_dirs


def cleanup_test_papers(test_dirs: list):
    """
    Delete all test paper directories and files.
    
    Args:
        test_dirs: List of test paper directories to delete
    """
    import shutil
    
    for test_dir in test_dirs:
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print(f"✓ Deleted {test_dir.name}")
    
    print(f"✓ Cleaned up {len(test_dirs)} test paper(s)")


if __name__ == '__main__':
    staging_dir = Path('./Staging')
    test_dirs = setup_test_papers(staging_dir)
    print(f"\nTest data created in: {staging_dir}")
    print(f"Total test papers: {len(test_dirs)}")
