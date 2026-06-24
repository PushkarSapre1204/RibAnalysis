"""
Geometric Parameter Processing Engine

Handles Task 1: Geometric Parameter Processing (The 5 Parameters)
- Processes P/e, e/D, Alpha, Geometry, and Aspect Ratio
- Implements Safety Trigger: prevents auto-fill if parameter is in varied_parameters list
- Implements Atomic Derivation: calculates missing parameters from constants
- Implements Source Tracking: creates [Param]_Source columns

Author: Meta-Analysis Preprocessor
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from ribs_core import config

logger = logging.getLogger(__name__)


class GeometricEngine:
    """Engine for processing and deriving geometric parameters with safety checks."""
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the Geometric Engine.
        
        Args:
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        self.derivation_log = []
    
    @staticmethod
    def parse_numeric_value(value: Any) -> Optional[float]:
        """
        Parse numeric values, handling units and type conversion.
        
        Converts strings like "25.5 mm", ratios like "1/4", and numbers to float.
        
        Args:
            value: Value to parse (string, number, or None)
            
        Returns:
            Float value or None if cannot parse
        """
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        
        # Already numeric
        if isinstance(value, (int, float)):
            return float(value)
        
        # String parsing
        if isinstance(value, str):
            value = value.strip()
            
            # Handle ratio format (e.g., "1/4")
            if '/' in value:
                try:
                    parts = value.split('/')
                    return float(parts[0]) / float(parts[1])
                except (ValueError, IndexError):
                    pass
            
            # Remove common units and convert
            for unit in ['mm', 'cm', 'm', 'deg', 'degree', '%']:
                value = value.replace(unit, '').strip()
            
            # Try to convert to float
            try:
                return float(value)
            except ValueError:
                return None
        
        return None
    
    def extract_manifest_constants(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract atomic constants from manifest.
        
        Map manifest's hierarchical structure to flat dictionary of constants:
        - e, P, W, H, D_h, Alpha, etc.
        
        Args:
            manifest: Manifest dictionary
            
        Returns:
            Flat dictionary of constants {param: value}
        """
        constants = {}
        
        # Helper to extract single value from list and parse numeric
        def extract_and_parse(val, parse_numeric=True):
            if isinstance(val, list):
                val = val[0] if val else None
            if parse_numeric:
                return self.parse_numeric_value(val)
            return val
        
        # Extract from nested structure
        try:
            dims = manifest.get('Experimental Apparatus & Dimensions', {})
            
            # Channel dimensions
            channel_dims = dims.get('Channel Dimensions', {})
            if channel_dims.get('Width'):
                constants['W'] = extract_and_parse(channel_dims['Width'], parse_numeric=True)
            if channel_dims.get('Height'):
                constants['H'] = extract_and_parse(channel_dims['Height'], parse_numeric=True)
            
            # Rib dimensions
            rib_dims = dims.get('Rib Dimensions', {})
            if rib_dims.get('Width'):
                constants['rib_width'] = extract_and_parse(rib_dims['Width'], parse_numeric=True)
            if rib_dims.get('Height'):
                constants['e'] = extract_and_parse(rib_dims['Height'], parse_numeric=True)
            if rib_dims.get('Pitch'):
                constants['P'] = extract_and_parse(rib_dims['Pitch'], parse_numeric=True)
            
            # Hydraulic diameter
            d_h = dims.get('Hydraulic Diameter (Dh)')
            if d_h:
                constants['D_h'] = extract_and_parse(d_h, parse_numeric=True)
            
            # Aspect ratio (can be ratio like "1/4")
            ar = dims.get('Aspect Ratio (W/H)')
            if ar:
                constants['Aspect_Ratio'] = extract_and_parse(ar, parse_numeric=True)
            
            # Alpha (angle of attack)
            alpha = dims.get('Angle of attack')
            if alpha:
                constants['Alpha'] = extract_and_parse(alpha, parse_numeric=True)
            
            # Fluid properties (Prandtl)
            boundary = manifest.get('Boundary & Flow Conditions', {})
            fluid_props = boundary.get('Fluid Properties', {})
            if isinstance(fluid_props, dict):
                if fluid_props.get('Pr'):
                    constants['Pr'] = fluid_props['Pr']
            
            # e/D_h
            e_d = dims.get('e/Dh')
            if e_d:
                constants['e/D_h'] = extract_and_parse(e_d, parse_numeric=True)
            
            # P/e
            p_e = dims.get('P/e')
            if p_e:
                constants['P/e'] = extract_and_parse(p_e, parse_numeric=True)
            
        except Exception as e:
            logger.warning(f"Error extracting manifest constants: {e}")
        
        return constants
    
    def get_varied_parameters(self, manifest: Dict[str, Any]) -> List[str]:
        """
        Extract parameters that were varied in the study (Safety Trigger).
        
        Varied parameters should NOT be auto-filled with N/A values.
        
        Args:
            manifest: Manifest dictionary
            
        Returns:
            List of parameter names that were varied
        """
        varied = []
        
        # Check if 'varied_parameters' explicitly listed
        if 'varied_parameters' in manifest:
            varied = manifest['varied_parameters']
        
        # Alternative: check which manifest values have multiple elements
        try:
            dims = manifest.get('Experimental Apparatus & Dimensions', {})
            
            # Check multi-element lists
            param_map = {
                'P/e': 'P/e',
                'e/Dh': 'e/D',
                'Angle of attack': 'Alpha',
                'Aspect Ratio (W/H)': 'Aspect ratio',
                'Channel Geometry': 'Geometry',
            }
            
            for key, param_name in param_map.items():
                val = dims.get(key)
                if val and isinstance(val, list) and len(val) > 1:
                    if param_name not in varied:
                        varied.append(param_name)
        
        except Exception as e:
            logger.warning(f"Error extracting varied parameters: {e}")
        
        return varied
    
    def classify_parameters(
        self,
        df: pd.DataFrame,
        manifest: Dict[str, Any]
    ) -> Tuple[Dict[str, List[str]], List[str]]:
        """
        Classify parameters as constants, variables, or unfilled.
        
        Implements Safety Trigger: if parameter in varied_parameters list,
        it cannot be auto-filled.
        
        Args:
            df: Raw data DataFrame
            manifest: Manifest dictionary
            
        Returns:
            Tuple of (classification_dict, varied_parameters_list)
            
        classification_dict structure:
            {
                'constants': [param1, param2],
                'variables': [param3, param4],
                'unfilled': [param5],
            }
        """
        classification = {
            'constants': [],
            'variables': [],
            'unfilled': [],
        }
        
        # Get varied parameters (Safety Trigger)
        varied_params = self.get_varied_parameters(manifest)
        
        # Check each parameter column
        all_param_columns = config.PREPROCESSOR_RAW_DATA_COLUMNS['parameters']
        
        for param in all_param_columns:
            if param not in df.columns:
                classification['unfilled'].append(param)
                continue
            
            # Count non-N/A values
            non_na_mask = ~df[param].isna()
            unique_vals = df.loc[non_na_mask, param].nunique()
            
            # Check if parameter is in varied list (Safety Trigger)
            if param in varied_params:
                classification['unfilled'].append(param)
                if self.verbose:
                    logger.info(f"Safety Trigger: {param} marked as varied → no auto-fill")
            elif unique_vals == 0:
                classification['unfilled'].append(param)
            elif unique_vals == 1:
                classification['constants'].append(param)
            else:
                classification['variables'].append(param)
        
        return classification, varied_params
    
    def derive_aspect_ratio(
        self,
        df: pd.DataFrame,
        constants: Dict[str, Any],
        manifest: Dict[str, Any],
        source_col: str = 'Aspect_Ratio_Source'
    ) -> pd.DataFrame:
        """
        Derive Aspect Ratio (W/H) from atomic components.
        
        Fills N/A values in 'Aspect ratio' column by:
        1. Check if manifest has constant W/H
        2. Calculate from W and H if available
        3. Mark source of each value
        
        Args:
            df: Data frame to process (modified in place)
            constants: Constants extracted from manifest
            manifest: Manifest dictionary for multi-value detection
            source_col: Name of source tracking column
            
        Returns:
            Modified DataFrame
        """
        if 'Aspect ratio' not in df.columns:
            df['Aspect ratio'] = np.nan
        if source_col not in df.columns:
            df[source_col] = 'unfilled'
        
        
        for idx in df.index:
            val = df.loc[idx, 'Aspect ratio']
            
            # Skip if already has value
            if pd.notna(val):
                df.loc[idx, source_col] = 'raw'
                continue
            
            # Check for multiple values in manifest (Case C)
            manifest_value = manifest.get('Experimental Apparatus & Dimensions', {}).get('Aspect Ratio (W/H)')
            if isinstance(manifest_value, list) and len(manifest_value) > 1:
                df.loc[idx, source_col] = 'WARNING'
                if self.verbose:
                    logger.info(f"Multiple values in manifest for Aspect ratio: {manifest_value} - skipping auto-fill")
                continue
            
            # Try manifest constant (Case A)
            if 'Aspect_Ratio' in constants and pd.notna(constants['Aspect_Ratio']):
                df.loc[idx, 'Aspect ratio'] = constants['Aspect_Ratio']
                df.loc[idx, source_col] = 'metadata'
                if self.verbose:
                    logger.info(f"Filled Aspect ratio from metadata: {constants['Aspect_Ratio']}")
                continue
            
            # Try atomic derivation (W/H)
            if 'W' in constants and 'H' in constants:
                w = constants['W']
                h = constants['H']
                if pd.notna(w) and pd.notna(h) and h != 0:
                    ar = w / h
                    df.loc[idx, 'Aspect ratio'] = ar
                    df.loc[idx, source_col] = 'derived'
                    if self.verbose:
                        logger.info(f"Derived Aspect ratio: {w}/{h} = {ar}")
                    continue
        
        return df
    
    def derive_relative_roughness(
        self,
        df: pd.DataFrame,
        constants: Dict[str, Any],
        manifest: Dict[str, Any],
        source_col: str = 'e/D_Source'
    ) -> pd.DataFrame:
        """
        Derive Relative Roughness (e/D_h) from atomic components.
        
        Fills N/A values in 'e/D' column by:
        1. Check if manifest has constant e/D_h
        2. Calculate from e and D_h if available
        3. If D_h missing, calculate D_h = 2WH/(W+H) first
        4. Mark source of each value
        
        Args:
            df: Data frame to process (modified in place)
            constants: Constants extracted from manifest
            manifest: Manifest dictionary for multi-value detection
            source_col: Name of source tracking column
            
        Returns:
            Modified DataFrame
        """
        if 'e/D' not in df.columns:
            df['e/D'] = np.nan
        if source_col not in df.columns:
            df[source_col] = 'unfilled'
        
        
        for idx in df.index:
            val = df.loc[idx, 'e/D']
            
            # Skip if already has value
            if pd.notna(val):
                df.loc[idx, source_col] = 'raw'
                continue
            
            # Check for multiple values in manifest (Case C)
            manifest_value = manifest.get('Experimental Apparatus & Dimensions', {}).get('e/Dh')
            if isinstance(manifest_value, list) and len(manifest_value) > 1:
                df.loc[idx, source_col] = 'WARNING'
                if self.verbose:
                    logger.info(f"Multiple values in manifest for e/D: {manifest_value} - skipping auto-fill")
                continue
            
            # Try manifest constant (Case A)
            if 'e/D_h' in constants and pd.notna(constants['e/D_h']):
                df.loc[idx, 'e/D'] = constants['e/D_h']
                df.loc[idx, source_col] = 'metadata'
                if self.verbose:
                    logger.info(f"Filled e/D from metadata: {constants['e/D_h']}")
                continue
            
            # Try atomic derivation (e / D_h)
            e = constants.get('e')
            d_h = constants.get('D_h')
            
            # If D_h missing, try to calculate from W and H
            if pd.isna(d_h) and 'W' in constants and 'H' in constants:
                w = constants['W']
                h = constants['H']
                if pd.notna(w) and pd.notna(h) and (w + h) != 0:
                    d_h = (2 * w * h) / (w + h)
                    if self.verbose:
                        logger.info(f"Calculated D_h: 2*{w}*{h}/({w}+{h}) = {d_h}")
            
            # Now derive e/D_h if both available
            if pd.notna(e) and pd.notna(d_h) and d_h != 0:
                e_d = e / d_h
                df.loc[idx, 'e/D'] = e_d
                df.loc[idx, source_col] = 'derived'
                if self.verbose:
                    logger.info(f"Derived e/D: {e}/{d_h} = {e_d}")
                continue
        
        return df
    
    def derive_pitch_to_height(
        self,
        df: pd.DataFrame,
        constants: Dict[str, Any],
        manifest: Dict[str, Any],
        source_col: str = 'P/e_Source'
    ) -> pd.DataFrame:
        """
        Derive Pitch-to-Height (P/e) from atomic components.
        
        Fills N/A values in 'P/e' column by:
        1. Check if manifest has constant P/e
        2. Calculate from P (pitch) and e (rib height) if available
        3. Mark source of each value
        
        Args:
            df: Data frame to process (modified in place)
            constants: Constants extracted from manifest
            manifest: Manifest dictionary for multi-value detection
            source_col: Name of source tracking column
            
        Returns:
            Modified DataFrame
        """
        if 'P/e' not in df.columns:
            df['P/e'] = np.nan
        if source_col not in df.columns:
            df[source_col] = 'unfilled'
        
        
        for idx in df.index:
            val = df.loc[idx, 'P/e']
            
            # Skip if already has value
            if pd.notna(val):
                df.loc[idx, source_col] = 'raw'
                continue
            
            # Check for multiple values in manifest (Case C)
            manifest_value = manifest.get('Experimental Apparatus & Dimensions', {}).get('P/e')
            if isinstance(manifest_value, list) and len(manifest_value) > 1:
                df.loc[idx, source_col] = 'WARNING'
                if self.verbose:
                    logger.info(f"Multiple values in manifest for P/e: {manifest_value} - skipping auto-fill")
                continue
            
            # Try manifest constant (Case A)
            if 'P/e' in constants and pd.notna(constants['P/e']):
                df.loc[idx, 'P/e'] = constants['P/e']
                df.loc[idx, source_col] = 'metadata'
                if self.verbose:
                    logger.info(f"Filled P/e from metadata: {constants['P/e']}")
                continue
            
            # Try atomic derivation (P / e)
            p = constants.get('P')
            e = constants.get('e')
            
            if pd.notna(p) and pd.notna(e) and e != 0:
                p_e = p / e
                df.loc[idx, 'P/e'] = p_e
                df.loc[idx, source_col] = 'derived'
                if self.verbose:
                    logger.info(f"Derived P/e: {p}/{e} = {p_e}")
                continue
        
        return df
    
    def process_alpha(
        self,
        df: pd.DataFrame,
        constants: Dict[str, Any],
        manifest: Dict[str, Any],
        source_col: str = 'Alpha_Source'
    ) -> pd.DataFrame:
        """
        Process Alpha (rib angle) with source tracking.
        
        Fills N/A values in 'Alpha' column if manifest has constant.
        
        Args:
            df: Data frame to process (modified in place)
            constants: Constants extracted from manifest
            manifest: Manifest dictionary for multi-value detection
            source_col: Name of source tracking column
            
        Returns:
            Modified DataFrame
        """
        if 'Alpha' not in df.columns:
            df['Alpha'] = np.nan
        if source_col not in df.columns:
            df[source_col] = 'unfilled'
        
        for idx in df.index:
            val = df.loc[idx, 'Alpha']
            
            # Skip if already has value
            if pd.notna(val):
                df.loc[idx, source_col] = 'raw'
                continue
            
            # Check for multiple values in manifest (Case C)
            manifest_value = manifest.get('Experimental Apparatus & Dimensions', {}).get('Angle of attack')
            if isinstance(manifest_value, list) and len(manifest_value) > 1:
                df.loc[idx, source_col] = 'WARNING'
                if self.verbose:
                    logger.info(f"Multiple values in manifest for Alpha: {manifest_value} - skipping auto-fill")
                continue
            
            # Try manifest constant (Case A)
            if 'Alpha' in constants and pd.notna(constants['Alpha']):
                df.loc[idx, 'Alpha'] = constants['Alpha']
                df.loc[idx, source_col] = 'metadata'
                if self.verbose:
                    logger.info(f"Filled Alpha from metadata: {constants['Alpha']}")
                continue
        
        return df
    
    def process_geometry(
        self,
        df: pd.DataFrame,
        constants: Dict[str, Any],
        manifest: Dict[str, Any],
        source_col: str = 'Geometry_Source'
    ) -> pd.DataFrame:
        """
        Process Geometry (rib type) with source tracking.
        
        Fills N/A values in 'Geometry' column if manifest has constant.
        
        Args:
            df: Data frame to process (modified in place)
            constants: Constants extracted from manifest
            manifest: Manifest dictionary for multi-value detection
            source_col: Name of source tracking column
            
        Returns:
            Modified DataFrame
        """
        if 'Geometry' not in df.columns:
            df['Geometry'] = np.nan
        if source_col not in df.columns:
            df[source_col] = 'unfilled'
        
        for idx in df.index:
            val = df.loc[idx, 'Geometry']
            
            # Skip if already has value
            if pd.notna(val):
                df.loc[idx, source_col] = 'raw'
                continue
            
            # Check for multiple values in manifest (Case C)
            manifest_value = manifest.get('Experimental Apparatus & Dimensions', {}).get('Channel Geometry')
            if isinstance(manifest_value, list) and len(manifest_value) > 1:
                df.loc[idx, source_col] = 'WARNING'
                if self.verbose:
                    logger.info(f"Multiple values in manifest for Geometry: {manifest_value} - skipping auto-fill")
                continue
            
            # Try manifest constant (Channel Geometry) (Case A)
            if 'Channel_Geometry' in constants and pd.notna(constants['Channel_Geometry']):
                df.loc[idx, 'Geometry'] = constants['Channel_Geometry']
                df.loc[idx, source_col] = 'metadata'
                if self.verbose:
                    logger.info(f"Filled Geometry from metadata: {constants['Channel_Geometry']}")
                continue
        
        return df
