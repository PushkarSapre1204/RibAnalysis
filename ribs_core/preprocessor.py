"""
Main Preprocessor Orchestrator

Coordinates the complete preprocessing pipeline:
- Per-paper processing (geometric + baseline)
- Local clean_data.csv generation
- Master CSV aggregation
- Decision logging

Author: Meta-Analysis Preprocessor
"""

import sys
from pathlib import Path

# Add project root to path for ribs_core imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np
import json
import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from ribs_core import config
from ribs_core.geometric_engine import GeometricEngine
from ribs_core.baseline_engine import BaselineEngine
from ribs_core.stitching_engine import StitchingEngine

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
        self.stitching_engine = StitchingEngine(verbose=verbose)
        
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
        df: pd.DataFrame,
        manifest: Dict[str, Any],
        paper_name: str
    ) -> Tuple[pd.DataFrame, Dict[str, Any], str]:
        """
        Process geometric parameters for a paper.
        
        Args:
            df: Filtered input DataFrame
            manifest: Manifest dictionary
            paper_name: Paper folder name for logging
            
        Returns:
            Tuple of (processed_df, decision_log, error_message)
            error_message is '' if no errors
        """
        try:
            constants = self.geometric_engine.extract_manifest_constants(manifest)
            classification, varied_params = self.geometric_engine.classify_parameters(df, manifest)

            df = self.geometric_engine.derive_aspect_ratio(df, constants, manifest)
            df = self.geometric_engine.derive_relative_roughness(df, constants, manifest)
            df = self.geometric_engine.derive_pitch_to_height(df, constants, manifest)
            df = self.geometric_engine.process_alpha(df, constants, manifest)
            df = self.geometric_engine.process_geometry(df, constants, manifest)

            geo_log = {
                'paper': paper_name,
                'timestamp': pd.Timestamp.now().isoformat(),
                'constants_extracted': constants,
                'varied_parameters': varied_params,
                'parameter_classification': classification,
                'geometric_derivation': {
                    'Aspect_Ratio': {
                        'filled_count': (df['Aspect_Ratio_Source'] != 'unfilled').sum(),
                        'sources': df['Aspect_Ratio_Source'].value_counts().to_dict(),
                    },
                    'e/D': {
                        'filled_count': (df['e/D_Source'] != 'unfilled').sum(),
                        'sources': df['e/D_Source'].value_counts().to_dict(),
                    },
                    'P/e': {
                        'filled_count': (df['P/e_Source'] != 'unfilled').sum(),
                        'sources': df['P/e_Source'].value_counts().to_dict(),
                    },
                    'Alpha': {
                        'filled_count': (df['Alpha_Source'] != 'unfilled').sum(),
                        'sources': df['Alpha_Source'].value_counts().to_dict(),
                    },
                    'Geometry': {
                        'filled_count': (df['Geometry_Source'] != 'unfilled').sum(),
                        'sources': df['Geometry_Source'].value_counts().to_dict(),
                    },
                },
            }

            return df, geo_log, ''
        
        except Exception as e:
            logger.error(f"Error processing geometric parameters for {paper_name}: {e}")
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
            
            # Process baseline for each row using manifest
            df, baseline_log, status = self.baseline_engine.process_paper(
                df,
                manifest,
                pr_value
            )
            
            return df, baseline_log, ''
        
        except Exception as e:
            logger.error(f"Error processing baseline for {paper_name}: {e}")
            return None, None, str(e)
    
    @staticmethod
    def _extract_figure_string(title: str) -> str:
        """Extract canonical figure string (e.g., 'Fig 9') from a manifest title."""
        if not isinstance(title, str):
            return ''

        match = re.search(r'fig(?:ure)?\s*\.?\s*(\d+[a-zA-Z]?)', title, flags=re.IGNORECASE)
        if not match:
            return ''

        return f"Fig {match.group(1)}"

    @staticmethod
    def _normalize_figure_identifier(value: Any) -> str:
        """Normalize different figure formats to comparable lowercase identifiers."""
        if pd.isna(value):
            return ''

        text = str(value).strip()
        if not text:
            return ''

        match = re.search(r'(\d+[a-zA-Z]?)', text)
        return match.group(1).lower() if match else text.lower()

    def validate_and_filter_figures_by_tag(
        self,
        df: pd.DataFrame,
        manifest: Dict[str, Any]
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Validate manifest tags and keep only figures tagged as Processing.
        
        Args:
            df: Input raw data DataFrame
            manifest: Paper manifest dictionary
            
        Returns:
            Tuple of (filtered_df, filtering_log)
        """
        figures = manifest.get('Figures of Interest', [])
        supported_tags = set(getattr(config, 'MANIFEST_SUPPORTED_TAGS', ['Processing', 'Verification', 'Archive']))

        invalid_tags = []
        processing_ids = set()

        for figure in figures:
            if not isinstance(figure, dict):
                continue

            tag = figure.get('Tag')
            if tag not in supported_tags:
                invalid_tags.append(tag)
                continue

            if tag != 'Processing':
                continue

            fig_title = figure.get('Figure Title', '')
            fig_string = self._extract_figure_string(fig_title)
            fig_id = self._normalize_figure_identifier(fig_string)
            if fig_id:
                processing_ids.add(fig_id)

        if invalid_tags:
            raise ValueError(f"Unsupported manifest tags detected: {sorted(set(invalid_tags))}")

        figure_col = 'Figure Number'
        if figure_col not in df.columns:
            raise ValueError(f"Missing required column '{figure_col}' for figure filtering")

        if not processing_ids:
            filtered_df = df.iloc[0:0].copy()
        else:
            mask = df[figure_col].apply(self._normalize_figure_identifier).isin(processing_ids)
            filtered_df = df[mask].copy()

        return filtered_df, {
            'rows_before': len(df),
            'rows_after': len(filtered_df),
            'rows_removed': len(df) - len(filtered_df),
            'processing_figures_count': len(processing_ids),
        }

    def filter_smooth_wall(
        self,
        df: pd.DataFrame,
        column_name: str = 'Reading on'
    ) -> Tuple[pd.DataFrame, int]:
        """
        Drop rows where Reading on is smooth wall (case-insensitive).
        
        Args:
            df: Processed data frame
            df: Data frame to filter
            column_name: Reading-on column name
            
        Returns:
            Tuple of (filtered_df, removed_count)
        """
        if column_name not in df.columns:
            return df.copy(), 0

        smooth_mask = (
            df[column_name]
            .astype(str)
            .str.strip()
            .str.lower()
            .eq('smooth wall')
        )

        removed = int(smooth_mask.sum())
        return df[~smooth_mask].copy(), removed

    def save_clean_outputs(
        self,
        df: pd.DataFrame,
        paper_dir: Path
    ) -> str:
        """
        Save clean_data.csv and clean_data_log.csv in the paper directory.
        
        Args:
            df: Fully processed DataFrame
            paper_dir: Paper directory
            
        Returns:
            Path to clean_data.csv or empty string on error
        """
        try:
            main_df = df[config.STITCHING_MASTER_SCHEMA].copy()
            main_df['Value'] = df['Standard_Ratio']
            main_df['Variable'] = df['Standard_Ratio_Method'].apply(
                self.stitching_engine._map_to_standard_symbol
            )

            log_df = df[config.STITCHING_LOG_SCHEMA].copy()

            main_path = paper_dir / config.STITCHING_MAIN_FILENAME
            log_path = paper_dir / config.STITCHING_LOG_FILENAME

            main_df.to_csv(main_path, index=False)
            log_df.to_csv(log_path, index=False)
            
            if self.verbose:
                logger.info(f"Saved clean outputs for {paper_dir.name}: {main_path}, {log_path}")
            
            return str(main_path)
        
        except Exception as e:
            logger.error(f"Error saving clean outputs for {paper_dir.name}: {e}")
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
            'manifest_filter_log': {},
            'smooth_wall_removed': 0,
            'geometric_log': {},
            'baseline_log': {},
            'clean_data_path': '',
            'rows_processed': 0,
        }
        
        try:
            logger.info(f"Processing paper: {paper_dir.name}")
            
            # Step 1: Load raw inputs
            print(f"\n{'='*50}")
            print(f"PROCESSING: {paper_dir.name}")
            print(f"{'='*50}")
            raw_data_path = paper_dir / 'raw_data.csv'
            manifest_path = paper_dir / 'manifest.json'

            df = pd.read_csv(raw_data_path)
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)

            # Keep approved manifest exception: add/update paper_number.
            try:
                paper_id = manifest.get('Paper Identification', {})
                if not isinstance(paper_id, dict):
                    paper_id = {}
                paper_id['paper_number'] = paper_dir.name
                manifest['Paper Identification'] = paper_id

                with open(manifest_path, 'w') as f:
                    json.dump(manifest, f, indent=2)

                if self.verbose:
                    logger.info(f"Added paper_number '{paper_dir.name}' to manifest")
            except Exception as e:
                logger.warning(f"Could not update manifest paper_number for {paper_dir.name}: {e}")

            # Step 2: Keep only processing-tagged figures.
            df, manifest_filter_log = self.validate_and_filter_figures_by_tag(df, manifest)
            result['manifest_filter_log'] = manifest_filter_log

            # Step 3: Drop smooth wall rows.
            df, smooth_removed = self.filter_smooth_wall(df)
            result['smooth_wall_removed'] = smooth_removed

            # Step 4: Geometric fill on filtered data.
            df, geo_log, geo_error = self.process_paper_geometric(df, manifest, paper_dir.name)
            if geo_error:
                result['status'] = 'error'
                result['error'] = geo_error
                return result

            result['geometric_log'] = geo_log

            # Step 5: Baseline normalization.
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

            # Step 6: Save clean_data and clean_data_log.
            clean_data_path = self.save_clean_outputs(df, paper_dir)
            if not clean_data_path:
                result['status'] = 'error'
                result['error'] = 'Failed to save clean output files'
                return result

            result['clean_data_path'] = clean_data_path
            
            result['rows_processed'] = len(df)
            
            print(f"\n{'='*50}")
            print(f"✓ COMPLETE: {paper_dir.name}")
            print(f"Final output rows: {len(df)}")
            print(f"{'='*50}\n")
            logger.info(f"✓ Completed {paper_dir.name} ({len(df)} rows)")
            
            return result
        
        except Exception as e:
            logger.error(f"Unexpected error processing {paper_dir.name}: {e}")
            result['status'] = 'error'
            result['error'] = str(e)
            return result
    
    def aggregate_master_csv(self) -> Tuple[str, int]:
        """
        Aggregate clean_data.csv files from all papers into clean_data_master.csv.

        This is the single stitching-engine call at preprocessor level.
        
        Returns:
            Tuple of (master_csv_path, total_rows)
        """
        master_csv_path, total_rows = self.stitching_engine.aggregate_master_main_csv(
            self.staging_dir
        )
        
        if master_csv_path:
            self.master_decision_log['master_csv_path'] = master_csv_path
            logger.info(f"Master aggregation complete: {master_csv_path} ({total_rows} rows)")
        else:
            logger.warning("Master aggregation failed: No main CSV files to aggregate")
        
        return master_csv_path, total_rows
    
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
        
        logger.info("Preprocessing complete")
        
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
