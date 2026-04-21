# preprocessor.py — Pipeline Orchestrator Reference

## Overview

The **preprocessor.py** module is the **main pipeline orchestrator**. It coordinates the complete preprocessing workflow:
- Per-paper processing (geometric + baseline + stitching)
- Local clean_data.csv generation for each paper
- Master CSV aggregation (combining all papers)
- Comprehensive decision logging

**Key Responsibility**: Run the complete pipeline and coordinate all processing engines.

---

## MetaAnalysisPreprocessor Class

### Initialization

**Signature:**
```python
class MetaAnalysisPreprocessor:
    def __init__(self, staging_dir: Path, verbose: bool = False):
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `staging_dir` | Path | Path to Staging directory (contains paper subdirectories) |
| `verbose` | bool | Enable verbose logging for debugging |

**Attributes Created:**
- `staging_dir`: Reference to staging directory
- `verbose`: Logging flag
- `geometric_engine`: GeometricEngine instance
- `baseline_engine`: BaselineEngine instance
- `stitching_engine`: StitchingEngine instance
- `logging_dir`: Directory for per-paper logs (from config)
- `master_output_dir`: Directory for master outputs (from config)
- `master_decision_log`: Central decision log dictionary

**Example:**
```python
from pathlib import Path
from ribs_core.preprocessor import MetaAnalysisPreprocessor

# Initialize preprocessor
preprocessor = MetaAnalysisPreprocessor(
    staging_dir=Path('Staging'),
    verbose=True
)
```

---

## Core Methods

### find_paper_directories() → List[Path]

Discovers all paper directories in the Staging folder.

**Signature:**
```python
def find_paper_directories(self) -> List[Path]:
```

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| paper_dirs | List[Path] | Sorted list of paper directory paths |

**Criteria for Valid Paper Directory:**
- Is a subdirectory in `staging_dir`
- Contains `raw_data.csv` file
- Contains `manifest.json` file

**Behavior:**
- ✓ Scans all subdirectories
- ✓ Checks for required files
- ✓ Returns sorted list (alphabetical order)
- ✓ Logs findings if verbose

**Example:**
```python
papers = preprocessor.find_paper_directories()

print(f"Found {len(papers)} papers:")
for paper_dir in papers:
    print(f"  - {paper_dir.name}")
```

**Output Example:**
```
Found 3 papers:
  - P001
  - P002
  - P003
```

---

### process_paper_geometric(paper_dir: Path) → Tuple[pd.DataFrame, Dict[str, Any], str]

Processes geometric parameters for a paper.

**Signature:**
```python
def process_paper_geometric(
    self,
    paper_dir: Path
) -> Tuple[pd.DataFrame, Dict[str, Any], str]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `paper_dir` | Path | Path to paper directory |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| geo_df | pd.DataFrame | DataFrame with geometric parameters processed |
| geo_log | Dict | Geometric processing decisions |
| status | str | 'success', 'warning', or 'error' |

**Behavior:**
- ✓ Delegates to GeometricEngine.process_paper()
- ✓ Captures all output
- ✓ Logs results to preprocessing_logs/
- ✓ Returns processed data and log

**Example:**
```python
paper_dir = Path('Staging/P001')
geo_df, geo_log, status = preprocessor.process_paper_geometric(paper_dir)

print(f"Status: {status}")
print(f"Rows: {len(geo_df)}")
print(f"Derived parameters: {geo_log.get('derived_count', 0)}")
```

---

### process_paper_baseline(geo_df: pd.DataFrame, paper_dir: Path) → Tuple[pd.DataFrame, Dict[str, Any], str]

Processes baseline normalization for a paper.

**Signature:**
```python
def process_paper_baseline(
    self,
    geo_df: pd.DataFrame,
    paper_dir: Path
) -> Tuple[pd.DataFrame, Dict[str, Any], str]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `geo_df` | pd.DataFrame | DataFrame from geometric processing |
| `paper_dir` | Path | Path to paper directory (for logging) |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| base_df | pd.DataFrame | DataFrame with normalized values |
| base_log | Dict | Baseline processing decisions |
| status | str | 'success', 'warning', or 'error' |

**Behavior:**
- ✓ Delegates to BaselineEngine.process_paper()
- ✓ Takes geometric output as input
- ✓ Logs decisions
- ✓ Returns normalized data

**Example:**
```python
base_df, base_log, status = preprocessor.process_paper_baseline(geo_df, paper_dir)

print(f"Status: {status}")
print(f"Methods used: {base_log.get('methods_used', {})}")
print(f"Variables normalized: {base_log.get('variables_count', 0)}")
```

---

### process_paper_stitch(base_df: pd.DataFrame, paper_dir: Path) → Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any], str]

Separates data into schema and metadata files.

**Signature:**
```python
def process_paper_stitch(
    self,
    base_df: pd.DataFrame,
    paper_dir: Path
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any], str]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `base_df` | pd.DataFrame | DataFrame from baseline processing |
| `paper_dir` | Path | Path to paper directory (for output) |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| main_df | pd.DataFrame | Schema DataFrame |
| log_df | pd.DataFrame | Metadata DataFrame |
| stitch_log | Dict | Stitching decisions |
| status | str | 'success', 'warning', or 'error' |

**Output Files Created:**
- `{paper_dir}/clean_data.csv` — Standardized schema
- `{paper_dir}/clean_data_log.csv` — Complete lineage

**Example:**
```python
main_df, log_df, stitch_log, status = preprocessor.process_paper_stitch(base_df, paper_dir)

print(f"Status: {status}")
print(f"Main CSV: {len(main_df)} rows, {len(main_df.columns)} columns")
print(f"Log CSV: {len(log_df)} rows, {len(log_df.columns)} columns")
```

---

### process_paper(paper_dir: Path) → Tuple[str, Dict[str, Any]]

Orchestrates complete per-paper processing (geometric + baseline + stitching).

**Signature:**
```python
def process_paper(
    self,
    paper_dir: Path
) -> Tuple[str, Dict[str, Any]]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `paper_dir` | Path | Path to paper directory |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| status | str | 'success', 'warning', or 'error' |
| combined_log | Dict | Combined log from all stages |

**Processing Pipeline:**
```
1. Geometric Processing
   ↓
2. Baseline Normalization
   ↓
3. Stitching & Output Separation
   ↓
4. Log Results
```

**Combined Log Includes:**
- All geometric decisions
- All baseline decisions
- All stitching decisions
- Paper-specific metadata
- Timing information

**Example:**
```python
# Process a single paper end-to-end
status, combined_log = preprocessor.process_paper(Path('Staging/P001'))

print(f"Paper P001 Status: {status}")
print(f"Outputs:")
print(f"  - clean_data.csv")
print(f"  - clean_data_log.csv")
print(f"Total time: {combined_log.get('processing_time_seconds', '?')}s")
```

---

### run() → bool

Runs the complete preprocessing pipeline for all papers.

**Signature:**
```python
def run(self) -> bool:
```

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| success | bool | True if all papers processed, False if any failures |

**Processing Steps:**
1. ✓ Find all paper directories
2. ✓ For each paper:
   - Process geometric parameters
   - Process baseline normalization
   - Separate and stitch outputs
3. ✓ Aggregate master CSV from all papers
4. ✓ Save master decision log
5. ✓ Return overall status

**Output Files:**
- `Staging/P001/clean_data.csv`
- `Staging/P001/clean_data_log.csv`
- `Staging/P002/clean_data.csv`
- `Staging/P002/clean_data_log.csv`
- ... (one pair per paper)
- `data/clean_data_master.csv` (all papers combined)
- `preprocessing_logs/master_preprocessing_log.json` (central log)

**Example:**
```python
preprocessor = MetaAnalysisPreprocessor(
    staging_dir=Path('Staging'),
    verbose=True
)

success = preprocessor.run()

if success:
    print("✓ Preprocessing completed successfully!")
    print("Outputs saved to:")
    print("  - Staging/P*/clean_data.csv")
    print("  - Staging/P*/clean_data_log.csv")
    print("  - data/clean_data_master.csv")
else:
    print("✗ Preprocessing encountered errors")
    print("Check preprocessing_logs/ for details")
```

---

## Master Decision Log

The **master_decision_log** is a comprehensive JSON file tracking all preprocessing decisions.

### Structure

```json
{
  "preprocessing_timestamp": "2024-04-12T15:30:45.123456",
  "staging_directory": "/path/to/Staging",
  "papers_processed": [
    {
      "paper_name": "P001",
      "status": "success",
      "clean_data_path": "Staging/P001/clean_data.csv",
      "clean_data_log_path": "Staging/P001/clean_data_log.csv",
      "rows_processed": 125,
      "geometric_log": { ... },
      "baseline_log": { ... },
      "stitch_log": { ... },
      "processing_time_seconds": 2.34
    },
    { ... more papers ... }
  ],
  "master_csv_path": "data/clean_data_master.csv",
  "master_csv_rows": 435,
  "total_papers": 3,
  "total_processing_time_seconds": 8.42,
  "errors": []
}
```

### Location

```
preprocessing_logs/master_preprocessing_log.json
```

### Usage

```python
import json

with open('preprocessing_logs/master_preprocessing_log.json') as f:
    master_log = json.load(f)

print(f"Timestamp: {master_log['preprocessing_timestamp']}")
print(f"Papers processed: {master_log['total_papers']}")
print(f"Total time: {master_log['total_processing_time_seconds']}s")
print(f"Master CSV rows: {master_log['master_csv_rows']}")

# Check for errors
if master_log['errors']:
    print(f"Errors: {master_log['errors']}")
```

---

## Common Workflows

### Workflow 1: Run Complete Pipeline

```python
from pathlib import Path
from ribs_core.preprocessor import MetaAnalysisPreprocessor

# Initialize
preprocessor = MetaAnalysisPreprocessor(
    staging_dir=Path('Staging'),
    verbose=True
)

# Run complete pipeline
success = preprocessor.run()

# Check results
if success:
    print("✓ All papers processed successfully")
    # Master CSV is ready in data/clean_data_master.csv
else:
    print("✗ Check logs for errors")
```

### Workflow 2: Process Single Paper

```python
# Find papers
papers = preprocessor.find_paper_directories()

# Process first paper only
if papers:
    status, log = preprocessor.process_paper(papers[0])
    print(f"Status: {status}")
else:
    print("No papers found in Staging")
```

### Workflow 3: Debug Specific Paper

```python
from pathlib import Path

paper_dir = Path('Staging/P001')

# Step 1: Geometric processing
print("Step 1: Processing geometry...")
geo_df, geo_log, status = preprocessor.process_paper_geometric(paper_dir)
print(f"  Rows: {len(geo_df)}, Status: {status}")

# Step 2: Baseline processing
print("Step 2: Processing baselines...")
base_df, base_log, status = preprocessor.process_paper_baseline(geo_df, paper_dir)
print(f"  Rows: {len(base_df)}, Status: {status}")

# Step 3: Stitching
print("Step 3: Stitching outputs...")
main_df, log_df, stitch_log, status = preprocessor.process_paper_stitch(base_df, paper_dir)
print(f"  Main CSV: {len(main_df)} rows, Log CSV: {len(log_df)} rows")
```

### Workflow 4: Analyze Results

```python
import pandas as pd
import json

# Load master CSV
master_df = pd.read_csv('data/clean_data_master.csv')
print(f"Total records: {len(master_df)}")
print(f"Papers: {master_df['Paper Title'].nunique()}")

# Load decision log
with open('preprocessing_logs/master_preprocessing_log.json') as f:
    log = json.load(f)

print(f"Processing time: {log['total_processing_time_seconds']}s")
print(f"Errors: {len(log['errors'])}")
```

---

## Integration with Other Tools

### Verification Tools

```python
# After preprocessing
from tools.verification_tool.verification_gui import verify_dataset

master_csv = 'data/clean_data_master.csv'
verify_dataset(master_csv)
```

### Visualization Tools

```python
# After preprocessing
from tools.visualiser_tool.visualiser_gui import visualize_data

master_csv = 'data/clean_data_master.csv'
visualize_data(master_csv, output_dir='visualizations/')
```

---

## Error Handling

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| No papers found | Staging directory empty or wrong path | Check Staging folder exists with paper subdirs |
| Missing manifest.json | Paper incomplete | Add manifest.json to paper directory |
| Geometric derivation failed | Missing constants in manifest | Check manifest has channel dimensions |
| Baseline calculation error | Missing Reynolds number | Ensure all rows have Re value |
| Master CSV not created | All papers failed | Check individual paper logs |

### Enable Debugging

```python
preprocessor = MetaAnalysisPreprocessor(
    staging_dir=Path('Staging'),
    verbose=True  # Enable detailed logging
)

success = preprocessor.run()

# Check logs
import os
for log_file in os.listdir('preprocessing_logs'):
    print(f"Log: {log_file}")
```

---

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Geometric processing (per paper) | ~0.5s | Depends on data size |
| Baseline processing (per paper) | ~0.5s | Correlation calculation |
| Stitching (per paper) | ~0.2s | File I/O |
| Master aggregation | ~1-2s | Depends on number of papers |
| **Complete pipeline** | ~3-5s | For 3-5 papers with 100-200 rows each |

---

## Related Documentation

- [INDEX.md](INDEX.md) — Overview and pipeline architecture
- [config.py.md](config.py.md) — Configuration used by all engines
- [geometric_engine.py.md](geometric_engine.py.md) — Task 1 processor
- [baseline_engine.py.md](baseline_engine.py.md) — Task 2 processor
- [stitching_engine.py.md](stitching_engine.py.md) — Task 3/4 processor
- [test_data_generator.py.md](test_data_generator.py.md) — Testing utilities
