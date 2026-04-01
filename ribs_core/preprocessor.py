"""
Main Preprocessor Orchestrator

Coordinates the complete preprocessing pipeline:
- Per-paper processing (geometric + baseline)
- Local clean_data.csv generation
- Master CSV aggregation
- Decision logging

Author: Meta-Analysis Preprocessor
"""

import pandas as pd
import numpy as np
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from ribs_core import config
from ribs_core.geometric_engine import GeometricEngine
from ribs_core.baseline_engine import BaselineEngine

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MetaAnalysisPreprocessor:
    """Main orchestrator for meta-analysis preprocessing pipeline."""
    
    def __init__(self, staging_dir: Path, verbose: bool = False):
        """
        Initialize the preprocessor.
        
        Args:
            staging_dir: Path to Staging directory
            verbose: Enable verbose logging
        """
        self.staging_dir = Path(staging_dir)
        self.verbose = verbose
        self.geometric_engine = GeometricEngine(verbose=verbose)
        self.baseline_engine = BaselineEngine(verbose=verbose)
        
        # Create logging directory
        self.logging_dir = Path(config.PREPROCESSOR_LOGGING_DIR)
        self.logging_dir.mkdir(exist_ok=True)
        
        # Master CSV output
        self.master_output_dir = Path(config.PREPROCESSOR_MASTER_OUTPUT_DIR)
        self.master_output_dir.mkdir(exist_ok=True)
        
        # Central decision log
        self.master_decision_log = {
            'preprocessing_timestamp': datetime.now().isoformat(),
            'staging_directory': str(self.staging_dir),
            'papers_processed': [],
            'master_csv_path': '',
            'errors': [],
        }
    
    def find_paper_directories(self) -> List[Path]:
        """
        Find all paper directories in Staging.
        
        Paper directories should contain raw_data.csv and manifest.json.
        
        Returns:
            List of paper directory paths
        """
        paper_dirs = []
        
        for item in self.staging_dir.iterdir():
            if item.is_dir():
                # Check for required files
                raw_data = item / 'raw_data.csv'
                manifest = item / 'manifest.json'
                
                if raw_data.exists() and manifest.exists():
                    paper_dirs.append(item)
                    if self.verbose:
                        logger.info(f"Found paper directory: {item.name}")
        
        return sorted(paper_dirs)
    
    def process_paper_geometric(
        self,
        paper_dir: Path
    ) -> Tuple[pd.DataFrame, Dict[str, Any], str]:
        """
        Process geometric parameters for a paper.
        
        Args:
            paper_dir: Path to paper directory
            
        Returns:
            Tuple of (processed_df, decision_log, error_message)
            error_message is '' if no errors
        """
        try:
            df, geo_log = self.geometric_engine.process_paper(
                paper_dir
            )
            return df, geo_log, ''
        
        except Exception as e:
            logger.error(f"Error processing geometric parameters for {paper_dir.name}: {e}")
            return None, None, str(e)
    
    def process_paper_baseline(
        self,
        df: pd.DataFrame,
        manifest: Dict[str, Any],
        paper_name: str
    ) -> Tuple[pd.DataFrame, Dict[str, Any], str]:
        """
        Process baseline normalization for a paper.
        
        Args:
            df: Data frame with processed geometric parameters
            manifest: Manifest dictionary
            paper_name: Name of paper for logging
            
        Returns:
            Tuple of (processed_df, decision_log, error_message)
            error_message is '' if no errors
        """
        try:
            # Extract baseline method and Prandtl number from manifest
            data_reduction = manifest.get('Data Reduction & Normalization', {})
            baseline_method = data_reduction.get('Smooth Baseline (Heat Transfer)', '')
            
            # Try to get Prandtl from manifest
            pr_value = None
            boundary = manifest.get('Boundary & Flow Conditions', {})
            fluid_props = boundary.get('Fluid Properties', {})
            if isinstance(fluid_props, dict):
                pr_value = fluid_props.get('Pr')
            
            if pr_value is None:
                pr_value = config.PREPROCESSOR_PRANDTL_DEFAULT
            
            # Store Prandtl in dataframe for tracking
            df['Prandtl'] = pr_value
            
            # Process baseline for each row
            df, baseline_log = self.baseline_engine.process_paper(
                df,
                baseline_method,
                pr_value
            )
            
            return df, baseline_log, ''
        
        except Exception as e:
            logger.error(f"Error processing baseline for {paper_name}: {e}")
            return None, None, str(e)
    
    def filter_reading_on(
        self,
        df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Filter data by "Reading on" column.
        
        Returns smooth (baseline) and ribbed (performance) data separately.
        
        Args:
            df: Data frame with "Reading on" column
            
        Returns:
            Tuple of (smooth_df, ribbed_df)
        """
        smooth_mask = df['Reading on'].str.lower().str.contains(
            '|'.join(config.PREPROCESSOR_SMOOTH_BASELINE_KEYWORDS),
            regex=True,
            na=False
        )
        
        ribbed_mask = df['Reading on'].str.lower().str.contains(
            '|'.join(config.PREPROCESSOR_RIBBED_PERFORM_KEYWORDS),
            regex=True,
            na=False
        )
        
        smooth_df = df[smooth_mask].copy()
        ribbed_df = df[ribbed_mask].copy()
        other_df = df[~smooth_mask & ~ribbed_mask].copy()
        
        # Add detection category
        if not smooth_df.empty:
            smooth_df['Reading_Category'] = 'Baseline'
        if not ribbed_df.empty:
            ribbed_df['Reading_Category'] = 'Performance'
        if not other_df.empty:
            other_df['Reading_Category'] = 'Unknown'
        
        combined_df = pd.concat([smooth_df, ribbed_df, other_df], ignore_index=True)
        
        return combined_df, {
            'smooth_count': len(smooth_df),
            'ribbed_count': len(ribbed_df),
            'unknown_count': len(other_df),
        }
    
    def save_clean_data_csv(
        self,
        df: pd.DataFrame,
        paper_dir: Path
    ) -> str:
        """
        Save processed data to clean_data.csv in paper directory.
        
        Args:
            df: Processed data frame
            paper_dir: Paper directory
            
        Returns:
            Path to saved CSV or error message
        """
        try:
            output_path = paper_dir / config.PREPROCESSOR_CLEAN_DATA_FILENAME
            df.to_csv(output_path, index=False)
            
            if self.verbose:
                logger.info(f"Saved clean_data.csv to {output_path}")
            
            return str(output_path)
        
        except Exception as e:
            logger.error(f"Error saving clean_data.csv for {paper_dir.name}: {e}")
            return ''
    
    def save_paper_decision_log(
        self,
        decision_log: Dict[str, Any],
        paper_dir: Path
    ) -> str:
        """
        Save paper decision log as JSON.
        
        Args:
            decision_log: Decision log dictionary
            paper_dir: Paper directory
            
        Returns:
            Path to saved JSON or empty string
        """
        try:
            paper_log_dir = self.logging_dir / paper_dir.name
            paper_log_dir.mkdir(exist_ok=True)
            
            log_path = paper_log_dir / 'processing_decisions.json'
            with open(log_path, 'w') as f:
                json.dump(decision_log, f, indent=2, default=str)
            
            if self.verbose:
                logger.info(f"Saved decision log to {log_path}")
            
            return str(log_path)
        
        except Exception as e:
            logger.error(f"Error saving decision log for {paper_dir.name}: {e}")
            return ''
    
    def process_single_paper(
        self,
        paper_dir: Path
    ) -> Dict[str, Any]:
        """
        Process a single paper through complete pipeline.
        
        Args:
            paper_dir: Path to paper directory
            
        Returns:
            Processing result dictionary
        """
        result = {
            'paper_name': paper_dir.name,
            'status': 'success',
            'error': '',
            'geometric_log': {},
            'baseline_log': {},
            'clean_data_path': '',
            'decision_log_path': '',
            'rows_processed': 0,
        }
        
        try:
            logger.info(f"Processing paper: {paper_dir.name}")
            
            # Step 1: Geometric processing
            df, geo_log, geo_error = self.process_paper_geometric(paper_dir)
            if geo_error:
                result['status'] = 'error'
                result['error'] = geo_error
                return result
            
            result['geometric_log'] = geo_log
            
            # Step 2: Load manifest for baseline info
            manifest_path = paper_dir / 'manifest.json'
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            # Step 3: Baseline normalization
            df, base_log, base_error = self.process_paper_baseline(
                df,
                manifest,
                paper_dir.name
            )
            if base_error:
                result['status'] = 'error'
                result['error'] = base_error
                return result
            
            result['baseline_log'] = base_log
            
            # Step 4: Reading on filtering (if column exists)
            if 'Reading on' in df.columns:
                df, reading_log = self.filter_reading_on(df)
                df.drop('Reading_Category', axis=1, errors='ignore', inplace=True)
            
            # Step 5: Save local clean_data.csv
            clean_data_path = self.save_clean_data_csv(df, paper_dir)
            if not clean_data_path:
                result['status'] = 'warning'
                result['error'] = 'Could not save clean_data.csv'
            else:
                result['clean_data_path'] = clean_data_path
            
            # Step 6: Save decision log
            decision_log = {
                'paper': paper_dir.name,
                'timestamp': datetime.now().isoformat(),
                'geometric_processing': geo_log,
                'baseline_processing': base_log,
                'rows_processed': len(df),
            }
            
            log_path = self.save_paper_decision_log(decision_log, paper_dir)
            if log_path:
                result['decision_log_path'] = log_path
            
            result['rows_processed'] = len(df)
            
            logger.info(f"✓ Completed {paper_dir.name} ({len(df)} rows)")
            
            return result
        
        except Exception as e:
            logger.error(f"Unexpected error processing {paper_dir.name}: {e}")
            result['status'] = 'error'
            result['error'] = str(e)
            return result
    
    def aggregate_master_csv(self) -> Tuple[str, int]:
        """
        Aggregate all clean_data.csv files into master CSV.
        
        Returns:
            Tuple of (master_csv_path, total_rows)
        """
        master_dfs = []
        
        for paper_dir in self.find_paper_directories():
            clean_data_path = paper_dir / config.PREPROCESSOR_CLEAN_DATA_FILENAME
            
            if clean_data_path.exists():
                try:
                    df = pd.read_csv(clean_data_path)
                    master_dfs.append(df)
                    logger.info(f"Added {len(df)} rows from {paper_dir.name}")
                except Exception as e:
                    logger.warning(f"Could not load {clean_data_path}: {e}")
        
        if not master_dfs:
            logger.warning("No clean_data.csv files found to aggregate")
            return '', 0
        
        # Concatenate all DataFrames
        master_df = pd.concat(master_dfs, ignore_index=True)
        
        # Save master CSV
        master_csv_path = (
            self.master_output_dir / config.PREPROCESSOR_MASTER_OUTPUT_FILENAME
        )
        master_df.to_csv(master_csv_path, index=False)
        
        logger.info(f"Saved master CSV to {master_csv_path} ({len(master_df)} rows)")
        self.master_decision_log['master_csv_path'] = str(master_csv_path)
        
        return str(master_csv_path), len(master_df)
    
    def run_all_papers(self) -> Dict[str, Any]:
        """
        Process all papers in Staging directory.
        
        Returns:
            Master processing report
        """
        logger.info(f"Starting preprocessing pipeline for {self.staging_dir}")
        
        paper_dirs = self.find_paper_directories()
        if not paper_dirs:
            logger.warning(f"No paper directories found in {self.staging_dir}")
            return self.master_decision_log
        
        logger.info(f"Found {len(paper_dirs)} paper(s)")
        
        # Process each paper
        for paper_dir in paper_dirs:
            result = self.process_single_paper(paper_dir)
            self.master_decision_log['papers_processed'].append(result)
            
            if result['status'] == 'error':
                self.master_decision_log['errors'].append({
                    'paper': result['paper_name'],
                    'error': result['error'],
                })
        
        # Aggregate master CSV
        master_path, total_rows = self.aggregate_master_csv()
        if master_path:
            self.master_decision_log['master_csv_rows'] = total_rows
        
        # Save master decision log
        master_log_path = self.logging_dir / 'master_preprocessing_log.json'
        with open(master_log_path, 'w') as f:
            json.dump(self.master_decision_log, f, indent=2, default=str)
        
        logger.info(f"Preprocessing complete. Log: {master_log_path}")
        
        return self.master_decision_log


def process_staging_directory(
    staging_dir: Path = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    CLI entry point for preprocessing.
    
    Args:
        staging_dir: Path to Staging directory (default: ./Staging)
        verbose: Enable verbose logging
        
    Returns:
        Processing report
    """
    if staging_dir is None:
        staging_dir = Path('./Staging')
    
    preprocessor = MetaAnalysisPreprocessor(staging_dir, verbose=verbose)
    return preprocessor.run_all_papers()


if __name__ == '__main__':
    import sys
    
    staging_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('./Staging')
    verbose = '--verbose' in sys.argv
    
    report = process_staging_directory(staging_dir, verbose)
    
    print("\n" + "="*80)
    print("PREPROCESSING SUMMARY")
    print("="*80)
    print(json.dumps(report, indent=2, default=str))
