"""
Example usage and test data generator for research_data_visualizer.py

This file demonstrates how to use the visualization script and provides
sample data for testing.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from research_data_visualizer import process_research_data


def create_sample_data(output_file: str = 'master_research_data.xlsx') -> str:
    """
    Create sample research data Excel file for testing.
    
    Args:
        output_file: Filename for the generated Excel file
        
    Returns:
        Path to the created file
    """
    # Sample data representing experimental results
    data = {
        'Paper Title': [
            'Flow Dynamics in Ribbed Channels',
            'Flow Dynamics in Ribbed Channels',
            'Flow Dynamics in Ribbed Channels',
            'Flow Dynamics in Ribbed Channels',
            'Heat Transfer Enhancement Study',
            'Heat Transfer Enhancement Study',
            'Heat Transfer Enhancement Study',
            'Heat Transfer Enhancement Study',
            'Heat Transfer Enhancement Study',
            'Heat Transfer Enhancement Study',
            'Pressure Drop Analysis',
            'Pressure Drop Analysis',
            'Pressure Drop Analysis',
            'Pressure Drop Analysis',
        ],
        'Figure Number': [
            1, 1, 1, 1,
            2, 2, 2, 2, 2, 2,
            3, 3, 3, 3,
        ],
        'Point ID': [
            'P1', 'P2', 'P3', 'P4',
            'P1', 'P2', 'P3', 'P4', 'P5', 'P6',
            'P1', 'P2', 'P3', 'P4',
        ],
        'Variable': [
            'Nu', 'Nu', 'Nu', 'Nu',
            'Nu', 'Nu', 'f', 'f', 'f', 'f',
            'f', 'f', 'St', 'St',
        ],
        'Value': [
            15.2, 18.5, 22.3, 25.8,
            12.1, 14.5, 0.032, 0.028, 0.025, 0.021,
            0.035, 0.029, 0.0045, 0.0038,
        ],
        'Reynolds number (Re)': [
            1000, 5000, 10000, 20000,
            1000, 5000, 1000, 5000, 10000, 20000,
            10000, 20000, 10000, 20000,
        ],
        'Geometry': [
            'Rectangular', 'Rectangular', 'Rectangular', 'Rectangular',
            'Trapezoidal', 'Trapezoidal', 'Trapezoidal', 'Trapezoidal', 'Trapezoidal', 'Trapezoidal',
            'Rectangular', 'Rectangular', 'Rectangular', 'Rectangular',
        ],
        'P/e': [
            10, 10, 10, 10,
            8, 8, 8, 8, 8, 8,
            12, 12, 12, 12,
        ],
        'e/D': [
            0.1, 0.1, 0.1, 0.1,
            0.15, 0.15, 0.15, 0.15, 0.15, 0.15,
            'N/A', 'N/A', 'N/A', 'N/A',
        ],
        'Alpha': [
            45, 45, 45, 45,
            'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
            45, 45, 45, 45,
        ],
        'Aspect ratio': [
            2, 2, 2, 2,
            2, 4, 4, 4, 4, 4,
            2, 2, 2, 2,
        ],
        'Number of ribbed walls': [
            1, 1, 1, 1,
            2, 2, 2, 2, 2, 2,
            1, 1, 1, 1,
        ],
        'Reading on': [
            'Wall 1', 'Wall 1', 'Wall 1', 'Wall 1',
            'Wall 2', 'Wall 2', 'Wall 2', 'Wall 2', 'Wall 2', 'Wall 2',
            'Wall 1', 'Wall 1', 'Wall 1', 'Wall 1',
        ],
        'Constant factor': [
            1.0, 1.0, 1.0, 1.0,
            1.1, 1.1, 1.1, 1.1, 1.1, 1.1,
            1.0, 1.0, 1.0, 1.0,
        ],
        'Dittus-Boelter Value': [
            12.5, 15.2, 18.8, 23.0,
            'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
            'N/A', 'N/A', 'N/A', 'N/A',
        ],
    }
    
    df = pd.DataFrame(data)
    df.to_excel(output_file, index=False)
    
    print(f"Sample data created: {output_file}")
    print(f"\nDataFrame shape: {df.shape}")
    print(f"\nFirst few rows:")
    print(df.head(10))
    
    return output_file


def demonstrate_script():
    """
    Demonstrate the visualization script with sample data.
    """
    print("\n" + "="*70)
    print("Verification Tool - DEMONSTRATION")
    print("="*70)
    
    # Create sample data
    print("\n[Step 1] Creating sample research data...")
    sample_file = create_sample_data('master_research_data.xlsx')
    
    # Process the data
    print("\n[Step 2] Processing data and generating plots...")
    process_research_data(sample_file, output_directory='./plots')
    
    print("\n[Step 3] Check the ./plots/ directory for generated PNG files")
    
    # Display summary
    plots_dir = Path('./plots')
    if plots_dir.exists():
        plot_files = list(plots_dir.glob('*.png'))
        print(f"\nGenerated {len(plot_files)} plot file(s):")
        for f in sorted(plot_files):
            print(f"  - {f.name}")


def demonstrate_with_custom_data():
    """
    Example showing how to use the script with custom data.
    """
    print("\n" + "="*70)
    print("USING WITH YOUR OWN DATA")
    print("="*70)
    print("""
    To use this script with your own data:
    
    1. Ensure your Excel file has these columns:
       - Paper Title
       - Figure Number
       - Point ID
       - Variable
       - Value
       - Reynolds number (Re)
       - Geometry
       - P/e
       - e/D
       - Alpha
       - Aspect ratio
       - Number of ribbed walls
       - Reading on
       - Constant factor
       - Dittus-Boelter Value
       
    2. Use N/A for missing parameter values (or leave cells empty)
    
    3. Call the function:
       from research_data_visualizer import process_research_data
       process_research_data('your_file.xlsx', 'output_folder')
    
    The script will:
    ✓ Automatically detect which parameters vary per figure
    ✓ Select the best X-axis (most variable parameter)
    ✓ Select the best legend parameter (second-most variable)
    ✓ Apply log-log scaling if needed
    ✓ Generate publication-quality PNG files
    """)


if __name__ == '__main__':
    # Run the demonstration
    demonstrate_script()
    demonstrate_with_custom_data()
