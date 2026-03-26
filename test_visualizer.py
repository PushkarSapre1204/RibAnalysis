"""
Unit tests and validation examples for Verification.py

Run tests with:
    python test_visualizer.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import unittest
from Verification import (
    analyze_parameter_variability,
    select_axes,
    check_need_log_scale,
    load_research_data,
)


class TestVariabilityAnalysis(unittest.TestCase):
    """Test the parameter variability analysis function."""
    
    def test_single_constant_parameter(self):
        """Test identification of a single constant parameter."""
        data = pd.DataFrame({
            'Reynolds number (Re)': [1000, 5000, 10000],
            'P/e': [10, 10, 10],
            'Value': [15.2, 18.5, 22.3]
        })
        
        analysis = analyze_parameter_variability(data, ['Reynolds number (Re)', 'P/e'])
        
        self.assertEqual(len(analysis['constants']), 1)
        self.assertEqual(analysis['constants']['P/e'], 10)
        self.assertEqual(analysis['variables']['Reynolds number (Re)'], 3)
    
    def test_all_variables(self):
        """Test when all parameters are variable."""
        data = pd.DataFrame({
            'Reynolds number (Re)': [1000, 5000, 10000],
            'P/e': [8, 10, 12],
        })
        
        analysis = analyze_parameter_variability(data, ['Reynolds number (Re)', 'P/e'])
        
        self.assertEqual(len(analysis['constants']), 0)
        self.assertEqual(len(analysis['variables']), 2)
    
    def test_all_constants(self):
        """Test when all parameters are constant."""
        data = pd.DataFrame({
            'Reynolds number (Re)': [1000, 1000, 1000],
            'P/e': [10, 10, 10],
        })
        
        analysis = analyze_parameter_variability(data, ['Reynolds number (Re)', 'P/e'])
        
        self.assertEqual(len(analysis['constants']), 2)
        self.assertEqual(len(analysis['variables']), 0)
    
    def test_nan_handling(self):
        """Test that NaN values are properly ignored."""
        data = pd.DataFrame({
            'Reynolds number (Re)': [1000, 5000, np.nan],
            'P/e': [np.nan, np.nan, np.nan],
        })
        
        analysis = analyze_parameter_variability(data, ['Reynolds number (Re)', 'P/e'])
        
        # P/e should be ignored (all NaN)
        self.assertNotIn('P/e', analysis['constants'])
        self.assertNotIn('P/e', analysis['variables'])
        
        # Re should be variable
        self.assertEqual(analysis['variables']['Reynolds number (Re)'], 2)
    
    def test_mixed_constants_and_variables(self):
        """Test realistic scenario with mix of constants and variables."""
        data = pd.DataFrame({
            'Reynolds number (Re)': [1000, 5000, 10000, 20000],
            'P/e': [10, 10, 10, 10],
            'Alpha': [45, 45, 45, 45],
            'Aspect ratio': [2, 4, 2, 4],
        })
        
        analysis = analyze_parameter_variability(
            data, 
            ['Reynolds number (Re)', 'P/e', 'Alpha', 'Aspect ratio']
        )
        
        # Constants
        self.assertEqual(len(analysis['constants']), 2)
        self.assertIn('P/e', analysis['constants'])
        self.assertIn('Alpha', analysis['constants'])
        
        # Variables
        self.assertEqual(len(analysis['variables']), 2)
        self.assertEqual(analysis['variables']['Reynolds number (Re)'], 4)
        self.assertEqual(analysis['variables']['Aspect ratio'], 2)


class TestAxisSelection(unittest.TestCase):
    """Test the axis selection logic."""
    
    def setUp(self):
        """Set up test data."""
        self.data = pd.DataFrame({
            'Reynolds number (Re)': [1000, 5000, 10000, 20000],
            'P/e': [10, 10, 10, 10],
            'Alpha': [45, 45, 45, 45],
            'Aspect ratio': [2, 4, 2, 4],
            'Value': [15.2, 18.5, 22.3, 25.8]
        })
    
    def test_x_axis_selection_highest_variability(self):
        """X-axis should be parameter with most unique values."""
        analysis = analyze_parameter_variability(
            self.data,
            ['Reynolds number (Re)', 'P/e', 'Alpha', 'Aspect ratio']
        )
        
        x_axis, legend_axis, constants = select_axes(analysis, self.data)
        
        # Re has 4 unique values (highest)
        self.assertEqual(x_axis, 'Reynolds number (Re)')
    
    def test_legend_selection_second_highest(self):
        """Legend should be parameter with second-most unique values."""
        analysis = analyze_parameter_variability(
            self.data,
            ['Reynolds number (Re)', 'P/e', 'Alpha', 'Aspect ratio']
        )
        
        x_axis, legend_axis, constants = select_axes(analysis, self.data)
        
        # Aspect ratio has 2 unique values (second highest after Re's 4)
        self.assertEqual(legend_axis, 'Aspect ratio')
    
    def test_conflict_resolution_re_priority(self):
        """When there's a tie, Reynolds number gets priority for X-axis."""
        # Create data where Re and P/e both have 3 unique values
        data = pd.DataFrame({
            'Reynolds number (Re)': [1000, 5000, 10000],
            'P/e': [8, 10, 12],
            'Alpha': [45, 45, 45],
        })
        
        analysis = analyze_parameter_variability(
            data,
            ['Reynolds number (Re)', 'P/e', 'Alpha']
        )
        
        x_axis, legend_axis, constants = select_axes(analysis, data)
        
        # Re should be chosen due to priority
        self.assertEqual(x_axis, 'Reynolds number (Re)')
    
    def test_no_variables(self):
        """When no parameters vary, return None for axes."""
        data = pd.DataFrame({
            'Reynolds number (Re)': [1000, 1000, 1000],
            'P/e': [10, 10, 10],
        })
        
        analysis = analyze_parameter_variability(
            data,
            ['Reynolds number (Re)', 'P/e']
        )
        
        x_axis, legend_axis, constants = select_axes(analysis, data)
        
        self.assertIsNone(x_axis)
        self.assertIsNone(legend_axis)
        self.assertEqual(len(constants), 2)


class TestLogScaleDetection(unittest.TestCase):
    """Test automatic log scale detection."""
    
    def test_single_order_magnitude_no_log(self):
        """Data within one order of magnitude should not use log scale."""
        values = np.array([10, 50, 100])  # Range: 100/10 = 10
        
        needs_log = check_need_log_scale(values)
        self.assertFalse(needs_log)
    
    def test_multiple_order_magnitude_use_log(self):
        """Data spanning multiple orders should use log scale."""
        values = np.array([1, 10, 100, 1000])  # Range: 1000/1 = 1000
        
        needs_log = check_need_log_scale(values)
        self.assertTrue(needs_log)
    
    def test_with_nan_values(self):
        """Should handle NaN values gracefully."""
        values = np.array([1, np.nan, 10, 100, np.nan, 1000])
        
        needs_log = check_need_log_scale(values)
        self.assertTrue(needs_log)
    
    def test_with_zero_and_negative(self):
        """Should ignore zero and negative values."""
        values = np.array([-100, 0, 1, 10, 100, 1000])
        
        needs_log = check_need_log_scale(values)
        # Only 1-1000 are considered: range = 1000
        self.assertTrue(needs_log)
    
    def test_empty_array(self):
        """Should handle empty array."""
        values = np.array([])
        
        needs_log = check_need_log_scale(values)
        self.assertFalse(needs_log)


class TestDataLoading(unittest.TestCase):
    """Test data loading and preprocessing."""
    
    def test_load_excel_file(self):
        """Test loading an Excel file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test Excel file
            data = pd.DataFrame({
                'Paper Title': ['Study A', 'Study A'],
                'Figure Number': [1, 1],
                'Variable': ['Nu', 'Nu'],
                'Value': [15.2, 18.5],
                'Reynolds number (Re)': [1000, 5000],
            })
            
            excel_path = Path(tmpdir) / 'test.xlsx'
            data.to_excel(excel_path, index=False)
            
            # Load it
            loaded_df = load_research_data(str(excel_path))
            
            self.assertEqual(len(loaded_df), 2)
            self.assertEqual(list(loaded_df.columns), list(data.columns))
    
    def test_na_replacement(self):
        """Test that N/A strings are replaced with NaN."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data = pd.DataFrame({
                'Paper Title': ['Study A'],
                'Figure Number': [1],
                'Variable': ['Nu'],
                'Value': [15.2],
                'Reynolds number (Re)': ['N/A'],
            })
            
            excel_path = Path(tmpdir) / 'test.xlsx'
            data.to_excel(excel_path, index=False)
            
            loaded_df = load_research_data(str(excel_path))
            
            # Check that 'N/A' was converted to NaN
            self.assertTrue(pd.isna(loaded_df.loc[0, 'Reynolds number (Re)']))


class TestIntegration(unittest.TestCase):
    """Integration tests with realistic data scenarios."""
    
    def test_realistic_flow_study(self):
        """Test with realistic flow study data."""
        data = pd.DataFrame({
            'Paper Title': ['Flow Dynamics'] * 8,
            'Figure Number': [1] * 4 + [2] * 4,
            'Variable': ['Nu'] * 4 + ['f'] * 4,
            'Value': [15.2, 18.5, 22.3, 25.8, 0.032, 0.028, 0.025, 0.021],
            'Reynolds number (Re)': [1000, 5000, 10000, 20000] * 2,
            'P/e': [10, 10, 10, 10, 12, 12, 12, 12],
            'Aspect ratio': [2, 2, 4, 4, 2, 2, 4, 4],
        })
        
        # Test Fig 1 (Nu)
        fig1_data = data[data['Figure Number'] == 1]
        var_data = fig1_data[fig1_data['Variable'] == 'Nu']
        
        analysis = analyze_parameter_variability(
            var_data,
            ['Reynolds number (Re)', 'P/e', 'Aspect ratio']
        )
        
        x_axis, legend_axis, constants = select_axes(analysis, var_data)
        
        # Re should be X (4 unique)
        self.assertEqual(x_axis, 'Reynolds number (Re)')
        # Aspect ratio should be legend (2 unique)
        self.assertEqual(legend_axis, 'Aspect ratio')
        # P/e should be constant
        self.assertEqual(constants['P/e'], 10)
    
    def test_multi_paper_batching(self):
        """Test batching with multiple papers."""
        data = pd.DataFrame({
            'Paper Title': ['Study A', 'Study A', 'Study B', 'Study B'],
            'Figure Number': [1, 1, 1, 1],
            'Variable': ['Nu', 'Nu', 'Nu', 'Nu'],
            'Value': [15.2, 18.5, 22.3, 25.8],
            'Reynolds number (Re)': [1000, 5000, 1000, 5000],
        })
        
        # Group by paper and figure
        groups = data.groupby(['Paper Title', 'Figure Number'])
        
        self.assertEqual(len(groups), 2)
        
        paper_names = [key[0] for key in groups.groups.keys()]
        self.assertIn('Study A', paper_names)
        self.assertIn('Study B', paper_names)


# ============================================================================
# EXAMPLE TEST SCENARIOS
# ============================================================================

def run_example_scenarios():
    """Run example scenarios showing script behavior."""
    print("\n" + "="*70)
    print("EXAMPLE SCENARIOS")
    print("="*70)
    
    # Scenario 1: Simple plot with one variable
    print("\n[Scenario 1] Simple plot - single variable")
    data1 = pd.DataFrame({
        'Reynolds number (Re)': [1000, 5000, 10000, 20000],
        'P/e': [10, 10, 10, 10],
        'Value': [15.2, 18.5, 22.3, 25.8]
    })
    analysis1 = analyze_parameter_variability(data1, ['Reynolds number (Re)', 'P/e'])
    x1, l1, c1 = select_axes(analysis1, data1)
    print(f"  X-axis: {x1}")
    print(f"  Legend: {l1}")
    print(f"  Constants: {c1}")
    
    # Scenario 2: Multi-variable with legend
    print("\n[Scenario 2] Complex plot - multiple variable parameters")
    data2 = pd.DataFrame({
        'Reynolds number (Re)': [1000, 5000, 10000, 20000],
        'P/e': [10, 10, 10, 10],
        'Alpha': [45, 45, 60, 60],
        'Value': [15.2, 18.5, 22.3, 25.8]
    })
    analysis2 = analyze_parameter_variability(data2, ['Reynolds number (Re)', 'P/e', 'Alpha'])
    x2, l2, c2 = select_axes(analysis2, data2)
    print(f"  X-axis: {x2}")
    print(f"  Legend: {l2}")
    print(f"  Constants: {c2}")
    
    # Scenario 3: All constant (no variation)
    print("\n[Scenario 3] Constant plot - all parameters fixed")
    data3 = pd.DataFrame({
        'Reynolds number (Re)': [1000, 1000, 1000],
        'P/e': [10, 10, 10],
        'Value': [15.2, 15.2, 15.2]
    })
    analysis3 = analyze_parameter_variability(data3, ['Reynolds number (Re)', 'P/e'])
    x3, l3, c3 = select_axes(analysis3, data3)
    print(f"  X-axis: {x3}")
    print(f"  Legend: {l3}")
    print(f"  Constants: {c3}")
    
    # Scenario 4: Log scaling detection
    print("\n[Scenario 4] Log scaling detection")
    data4a = np.array([10, 50, 100])
    data4b = np.array([1, 10, 100, 1000])
    print(f"  Data [10, 50, 100] needs log: {check_need_log_scale(data4a)}")
    print(f"  Data [1, 10, 100, 1000] needs log: {check_need_log_scale(data4b)}")


if __name__ == '__main__':
    # Run unit tests
    print("Running unit tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run example scenarios
    run_example_scenarios()
