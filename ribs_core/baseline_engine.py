"""
Baseline Normalization & Correlation Engine

Handles Task 2: Normalization & Baseline Re-conversion
- Variable identification (Nu, Nu/Nu0, St, St/St0, f, f/f0)
- Stanton-to-Nusselt conversion
- Baseline correlation calculations
- "Uncover and Reconvert" logic for non-standard baselines
- Source tracking for normalization decisions

Author: Meta-Analysis Preprocessor
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Tuple, Optional, Any, Callable
from ribs_core import config

logger = logging.getLogger(__name__)


class BaselineEngine:
    """Engine for baseline normalization and correlation calculations."""
    
    # Correlation formulas (callable functions)
    CORRELATIONS = {
        'Dittus-Boelert': {
            'variable': 'Nu',
            'formula': lambda re, pr: 0.023 * (re ** 0.8) * (pr ** 0.4),
            'description': 'Nu = 0.023 * Re^0.8 * Pr^0.4',
            'is_standard': True,
        },
        'Blasius': {
            'variable': 'f',
            'formula': lambda re: 0.316 * (re ** -0.25),
            'description': 'f = 0.316 * Re^-0.25',
            'is_standard': True,
        },
        'Petukhov': {
            'variable': 'f',
            'formula': lambda re: (0.79 * np.log(re) - 1.64) ** -2,
            'description': 'f = (0.79*ln(Re) - 1.64)^-2',
            'is_standard': False,
        },
        'Gnielinski': {
            'variable': 'Nu',
            'formula': lambda re, pr, f: (
                ((f / 8) * (re - 1000) * pr) / 
                (1 + 12.7 * np.sqrt(f / 8) * (pr ** (2/3) - 1))
            ),
            'description': 'Gnielinski',
            'is_standard': False,
        },
    }
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the Baseline Engine.
        
        Args:
            verbose: Enable verbose logging
        """
        self.verbose = verbose
    
    def identify_variable_type(self, variable: str) -> Tuple[str, str]:
        """
        Identify the base variable and its format.
        
        Args:
            variable: Variable name from data
            
        Returns:
            Tuple of (base_variable, format_type)
            where format_type in: 'raw', 'ratio', 'unknown'
            and base_variable in: 'Nu', 'f', 'St'
        """
        var_lower = variable.lower()
        
        # Identify base variable
        if 'nu' in var_lower:
            base = 'Nu'
        elif 'f' in var_lower and 'ff' not in var_lower:  # 'f' but not 'f/f'
            base = 'f'
        elif 'st' in var_lower:
            base = 'St'
        else:
            return variable, 'unknown'
        
        # Identify format (raw vs ratio)
        if '/' in variable or 'ratio' in var_lower or '_0' in variable:
            fmt = 'ratio'
        else:
            fmt = 'raw'
        
        return base, fmt
    
    def convert_stanton_to_nusselt(
        self,
        st_values: pd.Series,
        re_values: pd.Series,
        pr_value: float
    ) -> pd.Series:
        """
        Convert Stanton number to Nusselt number.
        
        Formula: Nu = St * Re * Pr
        
        Args:
            st_values: Stanton numbers
            re_values: Reynolds numbers
            pr_value: Prandtl number
            
        Returns:
            Nusselt number values
        """
        nu = st_values * re_values * pr_value
        return nu
    
    def calculate_baseline_nu(
        self,
        re_values: pd.Series,
        pr_value: float = None,
        method: str = 'Dittus-Boelert'
    ) -> pd.Series:
        """
        Calculate Nu_0 using standard baseline method.
        
        Args:
            re_values: Reynolds number values
            pr_value: Prandtl number
            method: Baseline method name
            
        Returns:
            Baseline Nu values
        """
        if pr_value is None:
            pr_value = config.PREPROCESSOR_PRANDTL_DEFAULT
        
        if method not in self.CORRELATIONS:
            raise ValueError(f"Unknown correlation method: {method}")
        
        corr = self.CORRELATIONS[method]
        if corr['variable'] != 'Nu':
            raise ValueError(f"{method} is for {corr['variable']}, not Nu")
        
        return corr['formula'](re_values, pr_value)
    
    def calculate_baseline_f(
        self,
        re_values: pd.Series,
        method: str = 'Blasius'
    ) -> pd.Series:
        """
        Calculate f_0 using standard baseline method.
        
        Args:
            re_values: Reynolds number values
            method: Baseline method name
            
        Returns:
            Baseline friction factor values
        """
        if method not in self.CORRELATIONS:
            raise ValueError(f"Unknown correlation method: {method}")
        
        corr = self.CORRELATIONS[method]
        if corr['variable'] != 'f':
            raise ValueError(f"{method} is for {corr['variable']}, not f")
        
        return corr['formula'](re_values)
    
    def uncover_baseline_method(
        self,
        reported_method: str
    ) -> Tuple[bool, str]:
        """
        Check if baseline method is standard or needs "uncovering".
        
        Args:
            reported_method: Baseline method reported by author
            
        Returns:
            Tuple of (is_standard, method_name)
            If is_standard=True, use author's values as-is
            If is_standard=False, need to back-calculate raw values
        """
        if not reported_method:
            return True, 'Dittus-Boelert'  # Default to standard
        
        reported_lower = reported_method.lower()
        
        # Map various names to standard methods
        if 'dittus' in reported_lower or 'boelert' in reported_lower:
            return True, 'Dittus-Boelert'
        elif 'dittus-boelert' in reported_lower or 'db' in reported_lower:
            return True, 'Dittus-Boelert'
        elif 'blasius' in reported_lower:
            return True, 'Blasius'
        elif 'experimental' in reported_lower or 'exp' in reported_lower:
            return True, 'Experimental'
        elif 'petukhov' in reported_lower:
            return False, 'Petukhov'
        elif 'gnielinski' in reported_lower:
            return False, 'Gnielinski'
        
        # Unknown method - assume needs uncovering
        return False, reported_method
    
    def back_calculate_raw_nu(
        self,
        ratio_values: pd.Series,
        baseline_method: str,
        re_values: pd.Series,
        pr_value: float = None
    ) -> pd.Series:
        """
        Back-calculate raw Nu from author's reported ratio.
        
        Given: reported_ratio = reported_Nu / reported_baseline
        Calculate: raw_Nu = reported_ratio * baseline_value
        
        Args:
            ratio_values: Reported Nu/Nu0 ratios
            baseline_method: Author's baseline method name
            re_values: Reynolds numbers
            pr_value: Prandtl number
            
        Returns:
            Back-calculated raw Nu values
        """
        if pr_value is None:
            pr_value = config.PREPROCESSOR_PRANDTL_DEFAULT
        
        # Get author's baseline values using their method
        if baseline_method not in self.CORRELATIONS:
            logger.warning(f"Unknown baseline method: {baseline_method}, using Dittus-Boelert")
            baseline_method = 'Dittus-Boelert'
        
        corr = self.CORRELATIONS[baseline_method]
        author_baseline = corr['formula'](re_values, pr_value)
        
        # Back-calculate raw Nu
        raw_nu = ratio_values * author_baseline
        
        return raw_nu
    
    def back_calculate_raw_f(
        self,
        ratio_values: pd.Series,
        baseline_method: str,
        re_values: pd.Series
    ) -> pd.Series:
        """
        Back-calculate raw f from author's reported ratio.
        
        Given: reported_ratio = reported_f / reported_baseline
        Calculate: raw_f = reported_ratio * baseline_value
        
        Args:
            ratio_values: Reported f/f0 ratios
            baseline_method: Author's baseline method name
            re_values: Reynolds numbers
            
        Returns:
            Back-calculated raw f values
        """
        # Get author's baseline values using their method
        if baseline_method not in self.CORRELATIONS:
            logger.warning(f"Unknown baseline friction method: {baseline_method}, using Blasius")
            baseline_method = 'Blasius'
        
        corr = self.CORRELATIONS[baseline_method]
        author_baseline = corr['formula'](re_values)
        
        # Back-calculate raw f
        raw_f = ratio_values * author_baseline
        
        return raw_f
    
    def process_variable_row(
        self,
        row: pd.Series,
        author_baseline_method: str,
        pr_value: float = None
    ) -> Dict[str, Any]:
        """
        Process a single row of data for baseline normalization.
        
        Determines:
        1. Variable type (Nu, f, St, Na ratio)
        2. Whether back-calculation is needed
        3. Standard ratio and normalization method
        
        Args:
            row: Single row from DataFrame
            author_baseline_method: Baseline method from manifest
            pr_value: Prandtl number
            
        Returns:
            Dictionary with processing results:
            {
                'variable': str,
                'base_variable': str,
                'raw_value': float,
                'standard_ratio': float,
                'standard_baseline_type': str,
                'standard_baseline_method': str,
                'processing_note': str,
            }
        """
        if pr_value is None:
            pr_value = config.PREPROCESSOR_PRANDTL_DEFAULT
        
        result = {
            'variable': row['Variable'],
            'base_variable': '',
            'raw_value': np.nan,
            'standard_ratio': np.nan,
            'standard_baseline_type': '',
            'standard_baseline_method': '',
            'processing_note': '',
        }
        
        # Handle missing values
        if pd.isna(row['Value']) or pd.isna(row['Reynolds number (Re)']):
            result['processing_note'] = 'Missing value or Re'
            return result
        
        value = float(row['Value'])
        re = float(row['Reynolds number (Re)'])
        
        # Identify variable type
        base_var, fmt = self.identify_variable_type(row['Variable'])
        result['base_variable'] = base_var
        
        # Handle unknown variables
        if fmt == 'unknown':
            result['processing_note'] = f'Unknown variable type: {row["Variable"]}'
            return result
        
        # Case 1: Raw value (not a ratio)
        if fmt == 'raw':
            result['raw_value'] = value
            
            # Convert Stanton to Nusselt if needed
            if base_var == 'St':
                nu = self.convert_stanton_to_nusselt(
                    pd.Series([value]),
                    pd.Series([re]),
                    pr_value
                )[0]
                result['raw_value'] = nu
                result['base_variable'] = 'Nu'
                result['processing_note'] = f'Converted St to Nu: Nu = {nu:.4f}'
                base_var = 'Nu'
            
            # Calculate standard baseline and ratio
            if base_var == 'Nu':
                standard_baseline = self.calculate_baseline_nu(
                    pd.Series([re]),
                    pr_value,
                    'Dittus-Boelert'
                )[0]
                result['standard_ratio'] = value / standard_baseline
                result['standard_baseline_type'] = 'Standard'
                result['standard_baseline_method'] = 'Dittus-Boelert'
                
            elif base_var == 'f':
                standard_baseline = self.calculate_baseline_f(
                    pd.Series([re]),
                    'Blasius'
                )[0]
                result['standard_ratio'] = value / standard_baseline
                result['standard_baseline_type'] = 'Standard'
                result['standard_baseline_method'] = 'Blasius'
            
            return result
        
        # Case 2: Author's ratio (needs "Uncover & Reconvert")
        is_standard, author_method = self.uncover_baseline_method(author_baseline_method)
        
        if is_standard and author_method != 'Experimental':
            # Keep author's ratio as standard
            result['raw_value'] = value
            result['standard_ratio'] = value
            result['standard_baseline_type'] = 'Author (Standard)'
            result['standard_baseline_method'] = author_method
            result['processing_note'] = f'Using author\'s standard baseline: {author_method}'
            return result
        
        if author_method == 'Experimental':
            # Keep experimental baseline ratio as-is
            result['raw_value'] = value
            result['standard_ratio'] = value
            result['standard_baseline_type'] = 'Author (Experimental)'
            result['standard_baseline_method'] = 'Experimental'
            result['processing_note'] = 'Using author\'s experimental baseline'
            return result
        
        # Non-standard baseline: back-calculate and reconvert
        if base_var == 'Nu':
            raw_nu = self.back_calculate_raw_nu(
                pd.Series([value]),
                author_method,
                pd.Series([re]),
                pr_value
            )[0]
            
            standard_baseline = self.calculate_baseline_nu(
                pd.Series([re]),
                pr_value,
                'Dittus-Boelert'
            )[0]
            
            standard_ratio = raw_nu / standard_baseline
            
            result['raw_value'] = raw_nu
            result['standard_ratio'] = standard_ratio
            result['standard_baseline_type'] = 'Reconverted'
            result['standard_baseline_method'] = f'{author_method}→Dittus-Boelert'
            result['processing_note'] = (
                f'Back-calculated from {author_method}: Nu={raw_nu:.4f}, '
                f'then normalized to Dittus-Boelert'
            )
            
        elif base_var == 'f':
            raw_f = self.back_calculate_raw_f(
                pd.Series([value]),
                author_method,
                pd.Series([re])
            )[0]
            
            standard_baseline = self.calculate_baseline_f(
                pd.Series([re]),
                'Blasius'
            )[0]
            
            standard_ratio = raw_f / standard_baseline
            
            result['raw_value'] = raw_f
            result['standard_ratio'] = standard_ratio
            result['standard_baseline_type'] = 'Reconverted'
            result['standard_baseline_method'] = f'{author_method}→Blasius'
            result['processing_note'] = (
                f'Back-calculated from {author_method}: f={raw_f:.4f}, '
                f'then normalized to Blasius'
            )
        
        return result
    
    def process_paper(
        self,
        df: pd.DataFrame,
        author_baseline_method: str,
        pr_value: float = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Process normalization for all rows in a paper.
        
        Adds columns to DataFrame:
        - Standard_Ratio: Normalized ratio using standard baseline
        - Standard_Ratio_Method: Which baseline conversion was used
        - Standard_Baseline_Type: Type of baseline (Standard, Author, Reconverted, Experimental)
        - Processing_Note: Explanation of processing per row
        
        Args:
            df: Data frame with Value and Reynolds number (Re) columns
            author_baseline_method: Baseline method from manifest
            pr_value: Prandtl number
            
        Returns:
            Tuple of (processed_df, decision_log_dict)
        """
        if pr_value is None:
            pr_value = config.PREPROCESSOR_PRANDTL_DEFAULT
        
        # Add output columns
        df['Standard_Ratio'] = np.nan
        df['Standard_Ratio_Method'] = ''
        df['Standard_Baseline_Type'] = ''
        df['Processing_Note'] = ''
        
        # Process each row
        for idx, row in df.iterrows():
            result = self.process_variable_row(row, author_baseline_method, pr_value)
            
            df.loc[idx, 'Standard_Ratio'] = result['standard_ratio']
            df.loc[idx, 'Standard_Ratio_Method'] = result['standard_baseline_method']
            df.loc[idx, 'Standard_Baseline_Type'] = result['standard_baseline_type']
            df.loc[idx, 'Processing_Note'] = result['processing_note']
        
        # Decision log
        decision_log = {
            'author_baseline_method': author_baseline_method,
            'prandtl_number': pr_value,
            'is_standard': self.uncover_baseline_method(author_baseline_method)[0],
            'baseline_type_distribution': df['Standard_Baseline_Type'].value_counts().to_dict(),
            'processed_rows': len(df),
            'rows_with_standard_ratio': (~df['Standard_Ratio'].isna()).sum(),
        }
        
        if self.verbose:
            logger.info(f"Completed baseline normalization for {len(df)} rows")
        
        return df, decision_log
