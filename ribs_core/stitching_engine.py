"""
Stitching Engine for Final Schema Separation

Handles Task 3/4: Data Uniformity and Schema Stitching
- Separates clean_data output into two CSV files:
  1. clean_data.csv: Schema-only (Value uses Standard_Ratio)
  2. clean_data_log.csv: Source tracking and processing metadata

Author: Meta-Analysis Preprocessor
"""

import pandas as pd
import logging
from typing import Tuple
from pathlib import Path
from ribs_core import config

logger = logging.getLogger(__name__)


class StitchingEngine:
    """Engine for separating schema and logging data."""
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the Stitching Engine.
        
        Args:
            verbose: Enable verbose logging
        """
        self.verbose = verbose
    
    def stitch_paper(
        self,
        df: pd.DataFrame,
        paper_dir: Path
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Separate preprocessed data into main schema and log CSV.
        
        Input df has all columns including source tracking and processing metadata.
        Output:
        - main_df: Only schema columns + standardized Value
        - log_df: Identifiers + source tracking + processing metadata
        
        Args:
            df: Complete processed DataFrame from baseline engine
            paper_dir: Paper directory for saving output
            
        Returns:
            Tuple of (main_df, log_df)
        """
        try:
            # Create main schema DataFrame
            main_df = df[config.STITCHING_MASTER_SCHEMA].copy()
            
            # Replace Value with Standard_Ratio (normalized values)
            main_df['Value'] = df['Standard_Ratio']
            
            # Standardize Variable to only Nu/Nu_0 or f/f_0
            main_df['Variable'] = df['Standard_Ratio_Method'].apply(self._map_to_standard_symbol)
            
            if self.verbose:
                logger.info(f"Created main schema DataFrame for {paper_dir.name}: "
                           f"{len(main_df)} rows, {len(main_df.columns)} columns")
            
            # Create log DataFrame  
            log_df = df[config.STITCHING_LOG_SCHEMA].copy()
            
            if self.verbose:
                logger.info(f"Created log DataFrame for {paper_dir.name}: "
                           f"{len(log_df)} rows, {len(log_df.columns)} columns")
            
            self._save_main_csv(main_df, paper_dir)
            self._save_log_csv(log_df, paper_dir)
            
            return main_df, log_df
        
        except Exception as e:
            logger.error(f"Error stitching paper {paper_dir.name}: {e}")
            raise
    
    @staticmethod
    def _map_to_standard_symbol(baseline_method: str) -> str:
        """
        Map baseline method to standardized variable symbol.
        
        Args:
            baseline_method: Baseline method name (e.g., 'Dittus-Boelert', 'Blasius')
            
        Returns:
            Standard symbol ('Nu/Nu_0' or 'f/f_0')
        """
        if baseline_method is None:
            return 'Nu/Nu_0'  # Default
        
        method_lower = str(baseline_method).lower()
        
        # Friction factor methods
        if any(x in method_lower for x in ['blasius', 'petukhov', 'friction', 'f/']):
            return 'f/f_0'
        
        # Heat transfer methods (default)
        return 'Nu/Nu_0'
    
    @staticmethod
    def _save_main_csv(df: pd.DataFrame, paper_dir: Path) -> None:
        """
        Save main schema CSV.
        
        Args:
            df: Schema-only DataFrame
            paper_dir: Paper directory
        """
        output_path = paper_dir / config.STITCHING_MAIN_FILENAME
        df.to_csv(output_path, index=False)
        logger.info(f"Saved main CSV to {output_path}")
    
    @staticmethod
    def _save_log_csv(df: pd.DataFrame, paper_dir: Path) -> None:
        """
        Save log CSV.
        
        Args:
            df: Log DataFrame
            paper_dir: Paper directory
        """
        output_path = paper_dir / config.STITCHING_LOG_FILENAME
        df.to_csv(output_path, index=False)
        logger.info(f"Saved log CSV to {output_path}")
    
    @staticmethod
    def aggregate_master_main_csv(staging_dir: Path) -> Tuple[str, int]:
        """
        Aggregate main CSV from all papers into master.
        
        Args:
            staging_dir: Path to Staging directory
            
        Returns:
            Tuple of (master_csv_path, total_rows)
        """
        main_files = []
        
        for paper_dir in sorted(staging_dir.iterdir()):
            if paper_dir.is_dir() and paper_dir.name.startswith('P'):
                main_path = paper_dir / config.STITCHING_MAIN_FILENAME
                
                if main_path.exists():
                    try:
                        df = pd.read_csv(main_path)
                        main_files.append(df)
                        logger.info(f"Added {len(df)} rows from {paper_dir.name}/{config.STITCHING_MAIN_FILENAME}")
                    except Exception as e:
                        logger.warning(f"Could not load {main_path}: {e}")
        
        if not main_files:
            logger.warning("No main CSV files found to aggregate")
            return '', 0
        
        # Concatenate all DataFrames
        master_df = pd.concat(main_files, ignore_index=True)
        
        # Save master CSV to Staging root
        master_path = staging_dir / config.STITCHING_MASTER_FILENAME
        master_df.to_csv(master_path, index=False)
        
        logger.info(f"Saved aggregated master CSV to {master_path} ({len(master_df)} rows)")
        
        return str(master_path), len(master_df)
