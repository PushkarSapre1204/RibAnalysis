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
    """
    Engine for baseline normalization with two parallel pipelines.
    
    Implements corrected normalization logic:
    - Pipeline A: Heat Transfer (Nu, Nu/Nu_0, St, St/St_0) → Nu/Nu_0
    - Pipeline B: Friction (f, f/f_0) → f/f_0
    
    Data types handled (from manifest):
    1. Rig Normalised - experimental baseline available
    2. Correlation Normalised - correlation-based baseline
    3. Raw Data - only measured values provided
    """
    
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
    
    def identify_pipeline(self, variable: str) -> str:
        """
        Identify which pipeline (Heat Transfer or Friction) a variable belongs to.
        
        Args:
            variable: Variable name from data
            
        Returns:
            'heat_transfer' or 'friction'
        """
        var_lower = variable.lower()
        
        # Heat Transfer: Nu, Nu/Nu_0, St, St/St_0
        if 'nu' in var_lower or ('st' in var_lower and 'f' not in var_lower):
            return 'heat_transfer'
        
        # Friction: f, f/f_0
        elif 'f' in var_lower and 'st' not in var_lower:  # f but not St
            return 'friction'
        
        return 'unknown'
    
    def identify_variable_format(self, variable: str, pipeline: str) -> Tuple[str, str]:
        """
        Identify the specific format of a variable within its pipeline.
        
        Args:
            variable: Variable name
            pipeline: 'heat_transfer' or 'friction'
            
        Returns:
            Tuple of (base_variable, format_type)
            heat_transfer: base in ['Nu', 'St'], format in ['raw', 'ratio']
            friction: base in ['f'], format in ['raw', 'ratio']
        """
        var_lower = variable.lower()
        
        if pipeline == 'heat_transfer':
            if 'nu' in var_lower:
                base = 'Nu'
            elif 'st' in var_lower:
                base = 'St'
            else:
                return 'unknown', 'unknown'
            
            # Format: ratio if contains / or _0 or _ratio
            fmt = 'ratio' if ('/' in variable or '_0' in variable or '_ratio' in variable.lower()) else 'raw'
            return base, fmt
        
        elif pipeline == 'friction':
            base = 'f'
            fmt = 'ratio' if ('/' in variable or '_0' in variable or '_ratio' in variable.lower()) else 'raw'
            return base, fmt
        
        return 'unknown', 'unknown'
    
    def extract_data_type_from_manifest(
        self,
        variable: str,
        manifest: Dict[str, Any],
        pipeline: str
    ) -> Tuple[str, Optional[str]]:
        """
        Extract data type and baseline method from manifest.
        
        Args:
            variable: Variable name
            manifest: Manifest dictionary from paper
            pipeline: 'heat_transfer' or 'friction'
            
        Returns:
            Tuple of (data_type, baseline_method)
            data_type: 'Rig', 'Correlation', 'Raw', or None if not found
            baseline_method: correlation method name or None
        """
        try:
            data_reduction = manifest.get('Data Reduction & Normalization', {})
            
            if pipeline == 'heat_transfer':
                # Check for heat transfer baseline info
                rig_baseline = data_reduction.get('Rig Baseline (Heat Transfer)')
                corr_baseline = data_reduction.get('Smooth Baseline (Heat Transfer)', '')
                
                if rig_baseline and rig_baseline != 'N/A':
                    return 'Rig', None
                elif corr_baseline and corr_baseline != 'N/A':
                    # Extract baseline method
                    if isinstance(corr_baseline, list):
                        corr_baseline = corr_baseline[0]
                    return 'Correlation', str(corr_baseline) if corr_baseline else None
                else:
                    return 'Raw', None
            
            elif pipeline == 'friction':
                # Check for friction baseline info
                rig_baseline = data_reduction.get('Rig Baseline (Friction)')
                corr_baseline = data_reduction.get('Friction Baseline', '')
                
                if rig_baseline and rig_baseline != 'N/A':
                    return 'Rig', None
                elif corr_baseline and corr_baseline != 'N/A':
                    if isinstance(corr_baseline, list):
                        corr_baseline = corr_baseline[0]
                    return 'Correlation', str(corr_baseline) if corr_baseline else None
                else:
                    return 'Raw', None
        
        except Exception as e:
            if self.verbose:
                logger.warning(f"Error extracting data type from manifest: {e}")
            return 'Raw', None
        
        return 'Raw', None
    
    def is_standard_baseline(
        self,
        baseline_method: str,
        pipeline: str
    ) -> bool:
        """
        Check if baseline method is our standard for the pipeline.
        
        Args:
            baseline_method: Baseline correlation method name
            pipeline: 'heat_transfer' or 'friction'
            
        Returns:
            True if method is (Dittus-Boelert for heat, Blasius for friction)
        """
        if not baseline_method:
            return True  # Default to standard if not specified
        
        method_lower = baseline_method.lower()
        
        if pipeline == 'heat_transfer':
            # Standard for heat transfer: Dittus-Boelert
            return any(x in method_lower for x in ['dittus', 'boelert', 'experimental'])
        
        elif pipeline == 'friction':
            # Standard for friction: Blasius
            return any(x in method_lower for x in ['blasius', 'experimental'])
        
        return False
    
    def get_standard_baseline_method(self, pipeline: str) -> str:
        """
        Get the standard baseline method for a pipeline.
        
        Args:
            pipeline: 'heat_transfer' or 'friction'
            
        Returns:
            Standard method name for the pipeline
        """
        if pipeline == 'heat_transfer':
            return 'Dittus-Boelert'
        elif pipeline == 'friction':
            return 'Blasius'
        return ''
    
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
        manifest: Dict[str, Any] = None,
        pr_value: float = None
    ) -> Dict[str, Any]:
        """
        Process a single row using the corrected two-pipeline logic.
        
        Args:
            row: Single data row with Variable, Value, Re
            manifest: Manifest dictionary for extracting data type
            pr_value: Prandtl number
            
        Returns:
            Dictionary with processing results
        """
        if pr_value is None:
            pr_value = config.PREPROCESSOR_PRANDTL_DEFAULT
        
        result = {
            'variable': row.get('Variable', ''),
            'base_variable': '',
            'raw_value': np.nan,
            'standard_ratio': np.nan,
            'standard_baseline_type': '',
            'standard_baseline_method': '',
            'processing_note': '',
        }
        
        # Handle missing values
        if pd.isna(row.get('Value')) or pd.isna(row.get('Reynolds number (Re)')):
            result['processing_note'] = 'Missing value or Reynolds number'
            return result
        
        value = float(row['Value'])
        re = float(row['Reynolds number (Re)'])
        variable = row.get('Variable', '')
        
        # STEP 1: Identify pipeline
        pipeline = self.identify_pipeline(variable)
        if pipeline == 'unknown':
            result['processing_note'] = f'Unknown variable type: {variable}'
            return result
        
        # STEP 2: Get variable format
        base_var, var_fmt = self.identify_variable_format(variable, pipeline)
        result['base_variable'] = base_var
        
        if pipeline == 'heat_transfer':
            return self._process_heat_transfer_row(
                row, result, value, re, base_var, var_fmt, manifest, pr_value
            )
        elif pipeline == 'friction':
            return self._process_friction_row(
                row, result, value, re, base_var, var_fmt, manifest
            )
        
        return result
    
    def _process_heat_transfer_row(
        self,
        row: pd.Series,
        result: Dict[str, Any],
        value: float,
        re: float,
        base_var: str,
        var_fmt: str,
        manifest: Dict[str, Any],
        pr_value: float
    ) -> Dict[str, Any]:
        """
        Process heat transfer (Nu/St) row through Pipeline A.
        
        Target output: Nu/Nu_0 using Dittus-Boelert baseline
        """
        # Step 1: Convert Stanton to Nusselt if needed
        if base_var == 'St':
            nu_raw = self.convert_stanton_to_nusselt(
                pd.Series([value]),
                pd.Series([re]),
                pr_value
            )[0]
            result['processing_note'] += f'Converted St to Nu: {nu_raw:.4f}. '
            base_var = 'Nu'
            var_fmt = 'ratio' if var_fmt == 'ratio' else 'raw'  # St_0 is ratio, St is raw
            value = nu_raw
        
        # Step 2: Check if raw Nu or ratio
        if var_fmt == 'raw':
            # TYPE 3: Raw Nu data - need to normalize
            nu_baseline = self.calculate_baseline_nu(
                pd.Series([re]),
                pr_value,
                'Dittus-Boelert'
            )[0]
            
            result['raw_value'] = value
            result['standard_ratio'] = value / nu_baseline
            result['standard_baseline_type'] = 'Raw Data'
            result['standard_baseline_method'] = 'Dittus-Boelert'
            result['processing_note'] += f'Raw Nu normalized using Dittus-Boelert'
        
        else:  # var_fmt == 'ratio'
            # Already a ratio - check manifest for data type
            data_type, baseline_method = self.extract_data_type_from_manifest(
                row.get('Variable', ''),
                manifest or {},
                'heat_transfer'
            )
            
            if data_type == 'Rig':
                # TYPE 1: Rig normalised - use as-is
                result['raw_value'] = value
                result['standard_ratio'] = value
                result['standard_baseline_type'] = 'Rig Normalised'
                result['standard_baseline_method'] = 'Rig Baseline'
                result['processing_note'] += 'Using rig baseline (kept as-is)'
            
            elif data_type == 'Correlation':
                # TYPE 2: Correlation normalised
                if self.is_standard_baseline(baseline_method, 'heat_transfer'):
                    # Standard baseline - keep as-is
                    result['raw_value'] = value
                    result['standard_ratio'] = value
                    result['standard_baseline_type'] = 'Correlation (Standard)'
                    result['standard_baseline_method'] = baseline_method or 'Dittus-Boelert'
                    result['processing_note'] += f'Using standard baseline: {baseline_method}'
                
                else:
                    # Non-standard baseline - unconvert & reconvert
                    # Back-calculate raw Nu
                    if baseline_method not in self.CORRELATIONS:
                        baseline_method = 'Dittus-Boelert'  # Fallback
                    
                    raw_nu = self.back_calculate_raw_nu(
                        pd.Series([value]),
                        baseline_method,
                        pd.Series([re]),
                        pr_value
                    )[0]
                    
                    # Reconvert to Dittus-Boelert
                    nu_baseline = self.calculate_baseline_nu(
                        pd.Series([re]),
                        pr_value,
                        'Dittus-Boelert'
                    )[0]
                    
                    result['raw_value'] = raw_nu
                    result['standard_ratio'] = raw_nu / nu_baseline
                    result['standard_baseline_type'] = 'Correlation (Unconverted & Reconverted)'
                    result['standard_baseline_method'] = f'{baseline_method}→Dittus-Boelert'
                    result['processing_note'] += (
                        f'Unconverted from {baseline_method}, '
                        f'reconverted to Dittus-Boelert'
                    )
            
            else:  # data_type == 'Raw'
                # Treat ratio as if from standard baseline for safety
                result['raw_value'] = value
                result['standard_ratio'] = value
                result['standard_baseline_type'] = 'Correlation (Standard)'
                result['standard_baseline_method'] = 'Dittus-Boelert'
                result['processing_note'] += 'Treated as standard correlation ratio'
        
        return result
    
    def _process_friction_row(
        self,
        row: pd.Series,
        result: Dict[str, Any],
        value: float,
        re: float,
        base_var: str,
        var_fmt: str,
        manifest: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process friction (f) row through Pipeline B.
        
        Target output: f/f_0 using Blasius baseline
        """
        # Step 1: No Stanton conversion needed for friction
        
        # Step 2: Check if raw f or ratio
        if var_fmt == 'raw':
            # TYPE 3: Raw f data - need to normalize
            f_baseline = self.calculate_baseline_f(
                pd.Series([re]),
                'Blasius'
            )[0]
            
            result['raw_value'] = value
            result['standard_ratio'] = value / f_baseline
            result['standard_baseline_type'] = 'Raw Data'
            result['standard_baseline_method'] = 'Blasius'
            result['processing_note'] = f'Raw f normalized using Blasius'
        
        else:  # var_fmt == 'ratio'
            # Already a ratio - check manifest for data type
            data_type, baseline_method = self.extract_data_type_from_manifest(
                row.get('Variable', ''),
                manifest or {},
                'friction'
            )
            
            if data_type == 'Rig':
                # TYPE 1: Rig normalised - use as-is
                result['raw_value'] = value
                result['standard_ratio'] = value
                result['standard_baseline_type'] = 'Rig Normalised'
                result['standard_baseline_method'] = 'Rig Baseline'
                result['processing_note'] = 'Using rig baseline (kept as-is)'
            
            elif data_type == 'Correlation':
                # TYPE 2: Correlation normalised
                if self.is_standard_baseline(baseline_method, 'friction'):
                    # Standard baseline (Blasius) - keep as-is
                    result['raw_value'] = value
                    result['standard_ratio'] = value
                    result['standard_baseline_type'] = 'Correlation (Standard)'
                    result['standard_baseline_method'] = baseline_method or 'Blasius'
                    result['processing_note'] = f'Using standard baseline: {baseline_method}'
                
                else:
                    # Non-standard baseline - unconvert & reconvert
                    if baseline_method not in self.CORRELATIONS:
                        baseline_method = 'Blasius'  # Fallback
                    
                    raw_f = self.back_calculate_raw_f(
                        pd.Series([value]),
                        baseline_method,
                        pd.Series([re])
                    )[0]
                    
                    # Reconvert to Blasius
                    f_baseline = self.calculate_baseline_f(
                        pd.Series([re]),
                        'Blasius'
                    )[0]
                    
                    result['raw_value'] = raw_f
                    result['standard_ratio'] = raw_f / f_baseline
                    result['standard_baseline_type'] = 'Correlation (Unconverted & Reconverted)'
                    result['standard_baseline_method'] = f'{baseline_method}→Blasius'
                    result['processing_note'] = (
                        f'Unconverted from {baseline_method}, '
                        f'reconverted to Blasius'
                    )
            
            else:  # data_type == 'Raw'
                # Treat ratio as if from standard baseline for safety
                result['raw_value'] = value
                result['standard_ratio'] = value
                result['standard_baseline_type'] = 'Correlation (Standard)'
                result['standard_baseline_method'] = 'Blasius'
                result['processing_note'] = 'Treated as standard correlation ratio'
        
        return result
    
    def process_paper(
        self,
        df: pd.DataFrame,
        manifest: Dict[str, Any] = None,
        pr_value: float = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any], str]:
        """
        Process normalization for all rows in a paper using corrected pipeline logic.
        
        Adds columns to DataFrame:
        - Standard_Ratio: Normalized ratio (Nu/Nu_0 or f/f_0)
        - Standard_Ratio_Method: Baseline method used
        - Standard_Baseline_Type: Data type (Rig/Correlation/Raw)
        - Processing_Note: Explanation of processing per row
        
        Args:
            df: Data frame with Value and Reynolds number (Re) columns
            manifest: Paper manifest dictionary
            pr_value: Prandtl number
            
        Returns:
            Tuple of (processed_df, decision_log_dict, status_message)
        """
        if pr_value is None:
            pr_value = config.PREPROCESSOR_PRANDTL_DEFAULT
        
        # Add output columns
        df['Standard_Ratio'] = np.nan
        df['Standard_Ratio_Method'] = ''
        df['Standard_Baseline_Type'] = ''
        df['Processing_Note'] = ''
        
        # Process each row
        errors = []
        for idx, row in df.iterrows():
            try:
                result = self.process_variable_row(row, manifest, pr_value)
                
                df.loc[idx, 'Standard_Ratio'] = result['standard_ratio']
                df.loc[idx, 'Standard_Ratio_Method'] = result['standard_baseline_method']
                df.loc[idx, 'Standard_Baseline_Type'] = result['standard_baseline_type']
                df.loc[idx, 'Processing_Note'] = result['processing_note']
            
            except Exception as e:
                error_msg = f"Error processing row {idx}: {str(e)}"
                errors.append(error_msg)
                if self.verbose:
                    logger.error(error_msg)
                df.loc[idx, 'Processing_Note'] = f'ERROR: {str(e)}'
        
        # Decision log
        decision_log = {
            'manifest_available': manifest is not None,
            'prandtl_number': pr_value,
            'baseline_type_distribution': df['Standard_Baseline_Type'].value_counts().to_dict(),
            'processed_rows': len(df),
            'error_rows': len(errors),
            'rows_with_standard_ratio': (~df['Standard_Ratio'].isna()).sum(),
            'heat_transfer_rows': len(df[df['Processing_Note'].str.contains('Nu|St', case=False, na=False)]),
            'friction_rows': len(df[df['Processing_Note'].str.contains('f', case=False, na=False)]),
        }
        
        status = 'success' if len(errors) == 0 else 'warning' if len(errors) < len(df) else 'error'
        
        if self.verbose:
            logger.info(f"Completed baseline normalization for {len(df)} rows (status: {status})")
            if errors:
                logger.warning(f"Encountered {len(errors)} errors during processing")
        
        return df, decision_log, status
