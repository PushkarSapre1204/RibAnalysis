# stitching_engine.py — Schema Separation & Output Reference

## Overview

The **stitching_engine.py** module implements **Task 3/4: Data Uniformity and Schema Stitching**. It separates preprocessed data into two specialized CSV files:
- **clean_data.csv** — Standardized schema-only data for meta-analysis
- **clean_data_log.csv** — Complete source tracking and processing metadata

**Key Responsibility**: Separate processed data into schema + metadata outputs while maintaining complete data lineage.

---

## StitchingEngine Class

### Initialization

**Signature:**
```python
class StitchingEngine:
    def __init__(self, verbose: bool = False):
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `verbose` | bool | False | Enable verbose logging for debugging |

**Example:**
```python
from ribs_core.stitching_engine import StitchingEngine

stitch_engine = StitchingEngine(verbose=True)
```

---

## Core Method

### stitch_paper(df: pd.DataFrame, paper_dir: Path) → Tuple[pd.DataFrame, pd.DataFrame]

Separates preprocessed data into main schema and log CSV files.

**Signature:**
```python
def stitch_paper(
    self,
    df: pd.DataFrame,
    paper_dir: Path
) -> Tuple[pd.DataFrame, pd.DataFrame]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `df` | pd.DataFrame | Complete processed DataFrame from BaselineEngine (includes all source tracking) |
| `paper_dir` | Path | Paper directory where outputs will be saved |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| main_df | pd.DataFrame | Clean schema DataFrame (for analysis) |
| log_df | pd.DataFrame | Metadata DataFrame (for lineage tracking) |

**Processing Steps:**
1. ✓ Extract standardized schema columns → `main_df`
2. ✓ Replace Value with Standard_Ratio (normalized) in `main_df`
3. ✓ Standardize Variable symbols (map to Nu/Nu_0 or f/f_0)
4. ✓ Extract lineage columns → `log_df`
5. ✓ Save both to CSV files in paper directory
6. ✓ Log all decisions

**Files Created:**
- `clean_data.csv` — Schema-compliant data
- `clean_data_log.csv` — Processing metadata

**Example:**
```python
from pathlib import Path

stitch_engine = StitchingEngine(verbose=True)
main_df, log_df = stitch_engine.stitch_paper(
    processed_df,
    paper_dir=Path('Staging/P001')
)

print(f"Main CSV: {len(main_df)} rows, {len(main_df.columns)} columns")
print(f"Log CSV: {len(log_df)} rows, {len(log_df.columns)} columns")

# Files saved:
# - Staging/P001/clean_data.csv (schema only)
# - Staging/P001/clean_data_log.csv (with source tracking)
```

---

## Output Schemas

### clean_data.csv — Standardized Schema

**Columns** (defined in `config.STITCHING_MASTER_SCHEMA`):

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| Paper Title | text | Paper identifier | Original |
| Figure Number | int | Plot number in paper | Original |
| Point ID | text | Data point identifier | Original |
| Variable | text | **Standardized** symbol (Nu, f, St, Nu/Nu_0, f/f_0) | Derived |
| Value | numeric | **Normalized** value (ratio, not raw) | Derived |
| Reynolds number (Re) | numeric | Flow rate parameter | Geometric + Original |
| Geometry | text | Rib geometry type | Geometric + Original |
| P/e | numeric | Pitch to rib height ratio | Geometric + Original |
| e/D | numeric | Rib height to hydraulic diameter | Geometric + Original |
| Alpha | numeric | Rib angle (degrees) | Geometric + Original |
| Aspect ratio | numeric | Channel width/height ratio | Geometric + Original |
| Number of ribbed walls | int | Count of ribbed walls | Geometric + Original |

**Purpose:**
- Ready for meta-analysis
- Consistent schema across all papers
- All values normalized and standardized
- NO source tracking or processing metadata

**Example Row:**
```
Paper Title: "Heat Transfer Study 2024"
Figure Number: 1
Point ID: "P_001"
Variable: "Nu/Nu_0"
Value: 1.35
Reynolds number (Re): 5000
...
```

---

### clean_data_log.csv — Complete Lineage

**Columns** (defined in `config.STITCHING_LOG_SCHEMA`):

| Column | Type | Description |
|--------|------|-------------|
| Paper Title | text | Paper identifier |
| Figure Number | int | Plot number |
| Point ID | text | Data point identifier |
| Variable | text | Original variable name |
| Original_Value | numeric | Raw measurement value |
| Standard_Ratio | numeric | Normalized value |
| Standard_Ratio_Method | text | Baseline method used |
| P/e_Source | text | Source of P/e (manifest/derived/original) |
| e/D_Source | text | Source of e/D |
| Alpha_Source | text | Source of Alpha |
| Geometry_Source | text | Source of Geometry |
| Aspect_Ratio_Source | text | Source of Aspect Ratio |
| **[Other Source Tracking Columns]** | text | Track origin of all parameters |

**Purpose:**
- Complete audit trail of all processing decisions
- Enable validation and verification
- Identify which values were derived vs. original
- Support reproducibility and troubleshooting

**Example Row:**
```
Paper Title: "Heat Transfer Study 2024"
Variable: "Nu"
Original_Value: 32.5
Standard_Ratio: 1.35
Standard_Ratio_Method: "Dittus-Boelert"
P/e_Source: "manifest"
e/D_Source: "derived"
...
```

---

## Supporting Methods

### _map_to_standard_symbol(baseline_method: str) → str

Maps baseline method to standardized variable symbol.

**Signature:**
```python
@staticmethod
def _map_to_standard_symbol(baseline_method: str) -> str:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `baseline_method` | str | Baseline method name (e.g., 'Dittus-Boelert', 'Blasius') |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| symbol | str | Standard symbol: 'Nu/Nu_0' or 'f/f_0' |

**Mapping Rules:**
- Friction factor methods (Blasius, Petukhov) → `'f/f_0'`
- Heat transfer methods (Dittus-Boelert, Gnielinski) → `'Nu/Nu_0'`
- Unknown/Default → `'Nu/Nu_0'`

**Example:**
```python
symbol = StitchingEngine._map_to_standard_symbol('Dittus-Boelert')
print(symbol)  # 'Nu/Nu_0'

symbol = StitchingEngine._map_to_standard_symbol('Blasius')
print(symbol)  # 'f/f_0'
```

---

### _save_main_csv(main_df: pd.DataFrame, paper_dir: Path) → None

Saves the main schema CSV file.

**Signature:**
```python
def _save_main_csv(self, main_df: pd.DataFrame, paper_dir: Path) -> None:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `main_df` | pd.DataFrame | Main schema DataFrame |
| `paper_dir` | Path | Paper directory for output |

**Behavior:**
- ✓ Saves to `{paper_dir}/clean_data.csv`
- ✓ Uses UTF-8 encoding
- ✓ No index column in output
- ✓ Logs success/failure

**Output File:**
```
Staging/P001/clean_data.csv
- Schema-compliant columns only
- Ready for meta-analysis tools
- No processing metadata
```

---

### _save_log_csv(log_df: pd.DataFrame, paper_dir: Path) → None

Saves the complete metadata/lineage CSV file.

**Signature:**
```python
def _save_log_csv(self, log_df: pd.DataFrame, paper_dir: Path) -> None:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `log_df` | pd.DataFrame | Log DataFrame with source tracking |
| `paper_dir` | Path | Paper directory for output |

**Behavior:**
- ✓ Saves to `{paper_dir}/clean_data_log.csv`
- ✓ Uses UTF-8 encoding
- ✓ No index column in output
- ✓ Logs success/failure
- ✓ Preserves all source tracking columns

**Output File:**
```
Staging/P001/clean_data_log.csv
- Complete processing lineage
- All source tracking columns
- Original + normalized values
- For validation and audit
```

---

## Data Separation Example

### Input DataFrame (from BaselineEngine)

```
Variable    Value    Standard_Ratio  Standard_Ratio_Method  P/e_Source  ...
'Nu'        32.5     1.35            'Dittus-Boelert'       'manifest'
'Nu/Nu0'    1.3      1.30            'Dittus-Boelert'       'manifest'
'f'         0.032    0.95            'Blasius'              'derived'
```

### Processing

```
Input: All columns + processing metadata
  ↓
Separate:
  ├─ main_df: Schema columns + normalized values
  └─ log_df: ID columns + source tracking + original values
  ↓
Output:
  ├─ clean_data.csv (main_df) — For analysis
  └─ clean_data_log.csv (log_df) — For lineage
```

### Output: clean_data.csv

```
Variable          Value   P/e  e/D  ...
'Nu/Nu_0'        1.35    5.2  0.1  ...
'Nu/Nu_0'        1.30    5.2  0.1  ...
'f/f_0'          0.95    5.2  0.1  ...
```

### Output: clean_data_log.csv

```
Variable  Original_Value  Standard_Ratio  Method             P/e_Source  ...
'Nu'      32.5           1.35            'Dittus-Boelert'   'manifest'
'Nu/Nu0'  1.3            1.30            'Dittus-Boelert'   'manifest'
'f'       0.032          0.95            'Blasius'          'derived'
```

---

## Master Aggregation

### aggregate_master_main_csv(all_papers: List[Path], output_dir: Path) → Path

Combines all per-paper clean_data.csv files into one master file.

**Signature:**
```python
@staticmethod
def aggregate_master_main_csv(
    all_papers: List[Path],
    output_dir: Path
) -> Path:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `all_papers` | List[Path] | List of paper directories (each with clean_data.csv) |
| `output_dir` | Path | Output directory for master file |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| output_path | Path | Path to created master CSV |

**Behavior:**
- ✓ Reads all clean_data.csv files
- ✓ Concatenates into single DataFrame
- ✓ Saves as `{output_dir}/clean_data_master.csv`
- ✓ Preserves schema consistency

**Output File:**
```
data/clean_data_master.csv
- All papers combined
- Consistent schema
- Ready for meta-analysis
- ~10,000+ rows (all papers)
```

**Example:**
```python
from pathlib import Path

papers = [Path('Staging/P001'), Path('Staging/P002'), Path('Staging/P003')]

master_path = StitchingEngine.aggregate_master_main_csv(
    papers,
    output_dir=Path('data')
)

print(f"Master file created: {master_path}")
```

---

## Common Workflows

### Workflow 1: Process Single Paper

```python
from pathlib import Path
from ribs_core.baseline_engine import BaselineEngine
from ribs_core.stitching_engine import StitchingEngine

# After baseline processing
base_engine = BaselineEngine()
base_df, _, _ = base_engine.process_paper(geo_df)

# Separate into schema + metadata
stitch_engine = StitchingEngine(verbose=True)
main_df, log_df = stitch_engine.stitch_paper(
    base_df,
    paper_dir=Path('Staging/P001')
)

# Files created:
# - Staging/P001/clean_data.csv (for analysis)
# - Staging/P001/clean_data_log.csv (for audit)
```

### Workflow 2: Aggregate All Papers into Master

```python
# Collect all paper directories
all_papers = [
    Path('Staging/P001'),
    Path('Staging/P002'),
    Path('Staging/P003'),
]

# Aggregate all clean_data.csv into master
master_path = StitchingEngine.aggregate_master_main_csv(
    all_papers,
    output_dir=Path('data')
)

print(f"Master dataset created: {master_path}")

# Load and analyze
import pandas as pd
master_df = pd.read_csv(master_path)
print(f"Total rows: {len(master_df)}")
print(f"Papers included: {master_df['Paper Title'].nunique()}")
```

### Workflow 3: Validation Using Logs

```python
import pandas as pd

# Load audit log to validate
log_df = pd.read_csv('Staging/P001/clean_data_log.csv')

# Check derivation sources
print("Parameter sources:")
for col in ['P/e_Source', 'e/D_Source', 'Alpha_Source']:
    if col in log_df.columns:
        print(f"  {col}:", log_df[col].value_counts())

# Flag rows with warnings
warnings = log_df[log_df['Status'] != 'success']
print(f"Warnings: {len(warnings)} rows")
```

---

## Schema Configuration

### Customizing Output Schema

Modify `config.py` to change output columns:

```python
# Schema for main CSV (analysis-ready)
STITCHING_MASTER_SCHEMA = [
    'Paper Title',
    'Figure Number',
    'Point ID',
    'Variable',
    'Value',  # Replaced with Standard_Ratio
    'Reynolds number (Re)',
    'Geometry',
    'P/e',
    'e/D',
    'Alpha',
    'Aspect ratio',
    'Number of ribbed walls',
    # Add custom columns here
]

# Schema for log CSV (complete lineage)
STITCHING_LOG_SCHEMA = [
    'Paper Title',
    'Figure Number',
    'Point ID',
    'Variable',
    'Original_Value',
    'Standard_Ratio',
    'Standard_Ratio_Method',
    # ... all source columns
    # Add custom tracking here
]
```

---

## Integration with Pipeline

```
BaselineEngine Output
(with Standard_Ratio + method)
    ↓
StitchingEngine.stitch_paper()
    ├─ Separate schema + metadata
    ├─ Standardize symbols
    ├─ Save clean_data.csv
    └─ Save clean_data_log.csv
    ↓
Per-Paper Outputs:
    ├─ clean_data.csv (for analysis)
    └─ clean_data_log.csv (for audit)
    ↓
Preprocessor.aggregate() calls:
    └─ aggregate_master_main_csv()
    ↓
Master Outputs:
    └─ clean_data_master.csv (all papers combined)
```

---

## Related Documentation

- [INDEX.md](INDEX.md) — Overview and pipeline architecture
- [config.py.md](config.py.md) — Configuration for schema definitions
- [baseline_engine.py.md](baseline_engine.py.md) — Previous processing step
- [preprocessor.py.md](preprocessor.py.md) — Uses StitchingEngine for output
