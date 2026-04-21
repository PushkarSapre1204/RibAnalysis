# baseline_engine.py — Baseline Normalization & Correlation Reference

## Overview

The **baseline_engine.py** module implements **Task 2: Normalization & Baseline Re-conversion**. It normalizes heat transfer and friction factor data by:

1. **Identifying data format** — Raw measurements vs. already-normalized ratios
2. **Routing by pipeline** — Heat Transfer (Nu/St) or Friction (f)
3. **Inferring data source** — Standard correlations vs. non-standard author correlations
4. **Applying transformations** — Stanton→Nusselt conversion, unconvert & reconvert logic
5. **Tracking all decisions** — Complete audit trail for reproducibility

**Key Responsibility**: Standardize all outputs to Nu/Nu₀ (Dittus-Boelert) for heat transfer and f/f₀ (Blasius) for friction, regardless of input format or author baseline.

---

## Processing Flowchart

```
INPUT: Data row (Variable, Value, Re, Pr) + Manifest
                                    ↓
    ═══════════════════════════════════════════════════════════
    STEP 1: ALIGNMENT & PRE-PROCESSING
    - Identify pipeline: Heat Transfer (Nu/St) vs Friction (f)
    - If Stanton (St): Convert to Nu = St × Re × Pr
    - If Stanton Ratio (St/St₀): Treat as Nu/Nu₀
    ═══════════════════════════════════════════════════════════
                                    ↓
                    ┌───────────────┴───────────────┐
                    ↓                               ↓
        ┌──────────────────────┐      ┌──────────────────────┐
        │  RATIO FORMAT        │      │  RAW FORMAT          │
        │  (e.g., Nu/Nu₀, f/f₀)│      │  (e.g., Nu, f)       │
        └──────────┬───────────┘      └──────────┬───────────┘
                   ↓                              ↓
    ═══════════════════════════════════════════════════════════
    STEP 2A: INFER TYPE FROM MANIFEST (RATIO FORMAT)
    
    Check 'Rig Baseline (Heat Transfer)' or 
    'Rig Baseline (Friction)' keys
                   ↓
        ┌──────────┴──────────┐
        ↓                     ↓
    [RIG FOUND]         [RIG NOT FOUND]
        ↓                     ↓
    PATH A:             Check 'Smooth Baseline
    RIG BASELINE        (Heat Transfer)' or
    ↓                   'Friction Baseline'
    Use ratio as-is         ↓
    Track: "Rig        ┌─────┴─────┐
    Normalised"        ↓           ↓
                    [STD FOUND] [NOT FOUND]
                        ↓           ↓
                    PATH A:     PATH A:
                    STANDARD    STANDARD
                    (Dittus)    (Blasius)
                    ↓           ↓
                    Use as-is   Use as-is
                    
            ┌───────────────┴────────────────┐
            ↓ (if non-standard method found)  ↓
        PATH B: NON-STANDARD
        (e.g., Petukhov, Gnielinski)
        
        1. Unconvert: Back-calculate raw value
           raw = ratio × author_baseline
        
        2. Reconvert: Using standard baseline
           ratio = raw / standard_baseline
        
        Track: "Unconverted from [X] & 
                reconverted to Standard"
    ═══════════════════════════════════════════════════════════
    
    STEP 2B: PROCESS RAW FORMAT
                    ↓
        ┌───────────────┬───────────────┐
        ↓               ↓               ↓
    PATH C1:        PATH C2:      (PLANNED)
    RIG BASELINE    STD BASELINE
    [PLANNED]       [CURRENT]
    
    Check for Rig    No Rig baseline
    Baseline ID      in manifest
    (From manifest)         ↓
        ↓          Calc standard baseline
    [IF FOUND]     - Heat: Dittus-Boelert
        ↓          - Friction: Blasius
    Use rig value       ↓
    ratio = value /  Normalize:
    rig_baseline     ratio = value /
        ↓            baseline
    Track: "Rig         ↓
    Normalised"     Track: "Raw data
                    normalized using
    (Not yet        [Method]"
     implemented)
    ═══════════════════════════════════════════════════════════
                                    ↓
                        ┌───────────┴───────────┐
                        ↓                       ↓
                    HEAT TRANSFER           FRICTION
                    Nu/Nu₀ Output           f/f₀ Output
                    (Dittus-Boelert)        (Blasius)
                                    ↓
    ═══════════════════════════════════════════════════════════
    OUTPUT: Enhanced Row
    - standard_ratio (normalized to Nu/Nu₀ or f/f₀)
    - standard_baseline_method (correlation name)
    - standard_baseline_type (Rig/Correlation Standard/Raw)
    - processing_note (complete decision trail)
    ═══════════════════════════════════════════════════════════
```

### Processing Paths Summary

| Path | Status | Trigger | Example | Processing | Output |
|------|--------|---------|---------|-----------|--------|
| **A** | ✅ Implemented | Ratio + Standard baseline detected | Nu/Nu₀ with Dittus-Boelert | Use value as-is | `Standard_Ratio = ratio` |
| **B** | ✅ Implemented | Ratio + Non-standard baseline detected | Nu/Nu₀ with Gnielinski | Unconvert & Reconvert | `Standard_Ratio = raw / Dittus` |
| **C1** | 🔄 Planned | Raw format + Rig baseline available in manifest | Raw Nu with rig baseline ID | Use rig value | `Standard_Ratio = value / rig_baseline` |
| **C2** | ✅ Implemented | Raw format detected (no rig baseline) | Raw Nu or f | Calculate standard baseline | `Standard_Ratio = value / Baseline` |

**Note on PATH C1**: Currently, the implementation goes directly to PATH C2 for all raw format data. PATH C1 would check the manifest for available rig baseline information and use that baseline if found. This feature is planned for a future update to enable greater flexibility in handling raw data with available rig baselines.

---

## BaselineEngine Class

### Initialization

**Signature:**
```python
class BaselineEngine:
    def __init__(self, verbose: bool = False):
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `verbose` | bool | False | Enable verbose logging for debugging |

**Example:**
```python
from ribs_core.baseline_engine import BaselineEngine

base_engine = BaselineEngine(verbose=True)
```

---

## Available Correlations

The engine includes 4 built-in heat transfer correlations defined in `BaselineEngine.CORRELATIONS`:

| Correlation | Variable | Formula | Standard? |
|-------------|----------|---------|-----------|
| **Dittus-Boelert** | Nu | `Nu = 0.023 * Re^0.8 * Pr^0.4` | ✓ Yes |
| **Blasius** | f | `f = 0.316 * Re^-0.25` | ✓ Yes |
| **Petukhov** | f | `f = (0.79*ln(Re) - 1.64)^-2` | No |
| **Gnielinski** | Nu | Empirical formula | No |

**Access Correlations:**
```python
# Get correlation details
for name, info in BaselineEngine.CORRELATIONS.items():
    print(f"{name}: {info['description']}")
    print(f"  Standard: {info['is_standard']}")
```

---

## Core Methods

### identify_pipeline(variable: str) → str

Identifies which processing pipeline a variable belongs to.

**Signature:**
```python
def identify_pipeline(self, variable: str) -> str:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `variable` | str | Variable name (e.g., 'Nu', 'St', 'f', 'Nu/Nu_0') |

**Returns:**
`'heat_transfer'` or `'friction'`

**Pipeline Routing:**
- **Heat Transfer**: Variables containing 'Nu' or 'St' → processes to Nu/Nu₀ (Dittus-Boelert)
- **Friction**: Variables containing 'f' → processes to f/f₀ (Blasius)
- **Unknown**: Returns 'unknown' if no match

**Example:**
```python
base_engine = BaselineEngine()

pipeline = base_engine.identify_pipeline('Nu')
print(pipeline)  # 'heat_transfer'

pipeline = base_engine.identify_pipeline('f/f_0')
print(pipeline)  # 'friction'

pipeline = base_engine.identify_pipeline('St')
print(pipeline)  # 'heat_transfer' (Stanton is heat transfer)
```

---

### identify_variable_format(variable: str, pipeline: str) → Tuple[str, str]

Identifies the variable format (raw vs ratio) within its pipeline.

**Signature:**
```python
def identify_variable_format(self, variable: str, pipeline: str) -> Tuple[str, str]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `variable` | str | Variable name |
| `pipeline` | str | 'heat_transfer' or 'friction' |

**Returns:**
Tuple of `(base_variable, format_type)`:
- `base_variable`: 'Nu', 'St', or 'f'
- `format_type`: 'raw' or 'ratio'

**Format Detection Rules:**
- **Ratio format**: Variable contains `/`, `_0`, or `_ratio` (signals already-normalized data)
- **Raw format**: Plain variable name (signals raw measured values)

**Example:**
```python
base, fmt = base_engine.identify_variable_format('Nu', 'heat_transfer')
print(f"{base}, {fmt}")  # 'Nu', 'raw'

base, fmt = base_engine.identify_variable_format('Nu/Nu_0', 'heat_transfer')
print(f"{base}, {fmt}")  # 'Nu', 'ratio'

base, fmt = base_engine.identify_variable_format('f_ratio', 'friction')
print(f"{base}, {fmt}")  # 'f', 'ratio'
```

---

### extract_data_type_from_manifest(variable: str, manifest: Dict, pipeline: str) → Tuple[str, Optional[str]]

**Infers data type** from manifest by checking for baseline information keys.

**Signature:**
```python
def extract_data_type_from_manifest(
    self,
    variable: str,
    manifest: Dict[str, Any],
    pipeline: str
) → Tuple[str, Optional[str]]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `variable` | str | Variable name |
| `manifest` | Dict | Manifest with 'Data Reduction & Normalization' section |
| `pipeline` | str | 'heat_transfer' or 'friction' |

**Returns:**
Tuple of `(data_type, baseline_method)`:
- `data_type`: 'Rig', 'Correlation', or 'Raw'
- `baseline_method`: Correlation name (e.g., 'Dittus-Boelert') or None

**Inference Logic** (Checks manifest keys in order):

For **Heat Transfer** pipeline:
1. If `'Rig Baseline (Heat Transfer)'` key exists and ≠ 'N/A' → Return `('Rig', None)` [PATH A]
2. Else if `'Smooth Baseline (Heat Transfer)'` exists and ≠ 'N/A' → Return `('Correlation', method)` [PATH A or B]
3. Else → Return `('Raw', None)`  [PATH C2]

For **Friction** pipeline:
1. If `'Rig Baseline (Friction)'` key exists and ≠ 'N/A' → Return `('Rig', None)` [PATH A]
2. Else if `'Friction Baseline'` exists and ≠ 'N/A' → Return `('Correlation', method)` [PATH A or B]
3. Else → Return `('Raw', None)` [PATH C2]

**Example:**
```python
manifest = {
    'Data Reduction & Normalization': {
        'Smooth Baseline (Heat Transfer)': 'Dittus-Boelert'
    }
}

data_type, method = base_engine.extract_data_type_from_manifest(
    'Nu', manifest, 'heat_transfer'
)
print(f"{data_type}, {method}")
# 'Correlation', 'Dittus-Boelert'

# If manifest had Rig baseline only:
manifest2 = {
    'Data Reduction & Normalization': {
        'Rig Baseline (Heat Transfer)': 'rig_value_123'
    }
}
data_type, method = base_engine.extract_data_type_from_manifest(
    'Nu', manifest2, 'heat_transfer'
)
print(f"{data_type}, {method}")
# 'Rig', None
```

---

### is_standard_baseline(baseline_method: str, pipeline: str) → bool

Checks if baseline method is our standard for the pipeline.

**Signature:**
```python
def is_standard_baseline(self, baseline_method: str, pipeline: str) -> bool:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `baseline_method` | str | Baseline correlation name |
| `pipeline` | str | 'heat_transfer' or 'friction' |

**Returns:**
`True` if method is standard, `False` if non-standard or unknown

**Standard Definitions:**
- **Heat Transfer**: Dittus-Boelert is standard
- **Friction**: Blasius is standard

**Non-Standard Methods** (trigger unconvert & reconvert):
- Heat Transfer: Petukhov, Gnielinski, or other custom correlations
- Friction: Petukhov or other custom correlations

**Example:**
```python
# Standard baselines
is_std = base_engine.is_standard_baseline('Dittus-Boelert', 'heat_transfer')
print(is_std)  # True

# Non-standard baseline
is_std = base_engine.is_standard_baseline('Gnielinski', 'heat_transfer')
print(is_std)  # False (triggers unconvert & reconvert)
```

---

### convert_stanton_to_nusselt(st_values: pd.Series, re_values: pd.Series, pr: float) → pd.Series

Converts Stanton numbers to Nusselt numbers.

**Signature:**
```python
def convert_stanton_to_nusselt(
    self,
    st_values: pd.Series,
    re_values: pd.Series,
    pr_value: float
) -> pd.Series:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `st_values` | pd.Series | Stanton numbers |
| `re_values` | pd.Series | Reynolds numbers |
| `pr_value` | float | Prandtl number |

**Returns:**
`pd.Series` — Converted Nusselt numbers

**Formula:**
```
Nu = St × Re × Pr
```

**Example:**
```python
import pandas as pd

st_data = pd.Series([0.001, 0.0015, 0.002])
re_data = pd.Series([1000, 2000, 4000])

nu_converted = base_engine.convert_stanton_to_nusselt(st_data, re_data, 0.71)
print(nu_converted)
```

---

### calculate_baseline_nu(re_values: pd.Series, pr_value: float, method: str) → pd.Series

Calculates baseline Nusselt using specified correlation.

**Signature:**
```python
def calculate_baseline_nu(
    self,
    re_values: pd.Series,
    pr_value: float = None,
    method: str = 'Dittus-Boelert'
) -> pd.Series:
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `re_values` | pd.Series | — | Reynolds numbers |
| `pr_value` | float | config default | Prandtl number |
| `method` | str | 'Dittus-Boelert' | Correlation to use |

**Returns:**
`pd.Series` — Baseline Nu values

**Used in:**
- **PATH C2** (raw data): Calculate baseline for first-time normalization
- **PATH B** (unconvert & reconvert): Reconvert using standard baseline after uncovering

---

### calculate_baseline_f(re_values: pd.Series, method: str) → pd.Series

Calculates baseline friction factor using specified correlation.

**Signature:**
```python
def calculate_baseline_f(
    self,
    re_values: pd.Series,
    method: str = 'Blasius'
) -> pd.Series:
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `re_values` | pd.Series | — | Reynolds numbers |
| `method` | str | 'Blasius' | Correlation to use |

**Returns:**
`pd.Series` — Baseline f values

**Used in:**
- **PATH C2** (raw data): Calculate baseline for first-time normalization
- **PATH B** (unconvert & reconvert): Reconvert using standard baseline

---

### back_calculate_raw_nu(ratio_values: pd.Series, baseline_method: str, re_values: pd.Series, pr_value: float) → pd.Series

Back-calculates raw Nusselt from normalized ratio.

**Signature:**
```python
def back_calculate_raw_nu(
    self,
    ratio_values: pd.Series,
    baseline_method: str,
    re_values: pd.Series,
    pr_value: float = None
) -> pd.Series:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `ratio_values` | pd.Series | Reported Nu/Nu_baseline ratios |
| `baseline_method` | str | Author's baseline method |
| `re_values` | pd.Series | Reynolds numbers |
| `pr_value` | float | Prandtl number |

**Returns:**
`pd.Series` — Raw uncovered Nu values

**Formula:**
```
Nu_raw = ratio × author_baseline(Re, Pr)
```

**Used in:** **PATH B** (Unconvert step for non-standard correlations)

---

### back_calculate_raw_f(ratio_values: pd.Series, baseline_method: str, re_values: pd.Series) → pd.Series

Back-calculates raw friction factor from normalized ratio.

**Signature:**
```python
def back_calculate_raw_f(
    self,
    ratio_values: pd.Series,
    baseline_method: str,
    re_values: pd.Series
) -> pd.Series:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `ratio_values` | pd.Series | Reported f/f_baseline ratios |
| `baseline_method` | str | Author's baseline method |
| `re_values` | pd.Series | Reynolds numbers |

**Returns:**
`pd.Series` — Raw uncovered f values

**Formula:**
```
f_raw = ratio × author_baseline(Re)
```

**Used in:** **PATH B** (Unconvert step for non-standard correlations)

---

### process_variable_row(row: pd.Series, manifest: Dict, pr_value: float) → Dict

Processes a single row through the complete normalization pipeline.

**Signature:**
```python
def process_variable_row(
    self,
    row: pd.Series,
    manifest: Dict[str, Any] = None,
    pr_value: float = None
) -> Dict[str, Any]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `row` | pd.Series | Single data row with Variable, Value, Re |
| `manifest` | Dict | Manifest with 'Data Reduction & Normalization' section |
| `pr_value` | float | Prandtl number |

**Returns:**
Dictionary with keys:
- `standard_ratio`: Normalized ratio (Nu/Nu₀ or f/f₀)
- `standard_baseline_method`: Correlation name
- `standard_baseline_type`: 'Rig Normalised', 'Correlation (Standard)', 'Correlation (Unconverted & Reconverted)', or 'Raw Data'
- `processing_note`: Complete decision trail explaining transformations applied

**Processing Flow:**
1. **Identify pipeline** (heat transfer vs friction)
2. **Identify format** (raw vs ratio)
3. **Extract data type from manifest** (Rig/Correlation/Raw)
4. **Route to appropriate path** (A, B, or C2 as per flowchart)
5. **Apply transformations** (St→Nu conversion, unconvert & reconvert, calculate baselines)
6. **Return standardized output**

**Example:**
```python
row_data = pd.Series({
    'Variable': 'Nu',
    'Value': 25.5,
    'Reynolds number (Re)': 5000
})

manifest = {
    'Data Reduction & Normalization': {},
    'Boundary & Flow Conditions': {'Fluid Properties': {'Pr': 0.71}}
}

result = base_engine.process_variable_row(row_data, manifest, pr_value=0.71)
print(f"Standard Ratio: {result['standard_ratio']}")
print(f"Baseline Type: {result['standard_baseline_type']}")
print(f"Note: {result['processing_note']}")
```

---

### process_paper(df: pd.DataFrame, manifest: Dict, pr_value: float) → Tuple[pd.DataFrame, Dict[str, Any], str]

Main orchestration method that processes all rows in a paper.

**Signature:**
```python
def process_paper(
    self,
    df: pd.DataFrame,
    manifest: Dict[str, Any] = None,
    pr_value: float = None
) -> Tuple[pd.DataFrame, Dict[str, Any], str]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `df` | pd.DataFrame | Data frame with Variable, Value, Reynolds number (Re) columns |
| `manifest` | Dict | Paper manifest with 'Data Reduction & Normalization' and 'Boundary & Flow Conditions' sections |
| `pr_value` | float | Prandtl number (extracted from manifest if not provided) |

**Returns:**
Tuple of `(processed_df, decision_log, status)`:
- **processed_df**: Original dataframe with added columns:
  - `Standard_Ratio`: Normalized ratio (Nu/Nu₀ or f/f₀)
  - `Standard_Ratio_Method`: Baseline correlation method
  - `Standard_Baseline_Type`: Data source type
  - `Processing_Note`: Decision trail
- **decision_log**: Dictionary with processing statistics
  - `manifest_available`: Whether manifest was provided
  - `prandtl_number`: Pr value used
  - `baseline_type_distribution`: Count of each baseline type
  - `processed_rows`: Total rows processed
  - `error_rows`: Rows with errors
  - `rows_with_standard_ratio`: Successful normalizations
  - `heat_transfer_rows`: Count of heat transfer variables
  - `friction_rows`: Count of friction variables
- **status**: 'success', 'warning' (some errors), or 'error' (all failed)

**Processing:**
- Processes every row through `process_variable_row()`
- Adds 4 new columns to output dataframe
- Collects statistics for decision log
- Handles errors gracefully with error tracking

**Example:**
```python
import pandas as pd

# Load data
df = pd.read_csv('paper_data.csv')

# Load manifest
import json
with open('manifest.json') as f:
    manifest = json.load(f')

# Process
base_engine = BaselineEngine(verbose=True)
result_df, log, status = base_engine.process_paper(df, manifest, pr_value=0.71)

print(f"Status: {status}")
print(f"Processed: {log['processed_rows']} rows")
print(f"Baseline distribution: {log['baseline_type_distribution']}")

# View results
print(result_df[['Variable', 'Value', 'Standard_Ratio', 'Standard_Baseline_Type']])
```

---

## Related Documentation

- [INDEX.md](INDEX.md) — Overview and pipeline architecture
- [config.py.md](config.py.md) — Configuration for correlation formulas
- [geometric_engine.py.md](geometric_engine.py.md) — Previous processing step
- [stitching_engine.py.md](stitching_engine.py.md) — Next processing step
- [preprocessor.py.md](preprocessor.py.md) — Uses BaselineEngine in pipeline

## Key Concepts

### Raw vs. Ratio Variables

```
RAW VARIABLES: Direct measurements
  Examples: 'Nu', 'f', 'St'
  Processing: Add baseline, divide to normalize
  Output: Nu/Nu_0 or f/f_0

RATIO VARIABLES: Pre-normalized in source
  Examples: 'Nu/Nu0', 'f/f_Blasius', 'St/St_baseline'
  Processing: Detect method, verify/uncover baseline
  Output: Standardized ratio (Nu/Nu_0 or f/f_0)
```

### Uncover and Reconvert Logic

```
Challenge: Baseline method unknown or mixed

Solution:
  1. Pattern Recognition: Check variable name for clues
  2. Value Analysis: Examine actual values for patterns
  3. Back-Calculation: Reverse-engineer baseline method
  4. Re-Conversion: Convert to standard format (Nu/Nu_0 or f/f_0)
  5. Decision Tracking: Log the recovery strategy
```

### Source Tracking

Every normalized value includes source information:
```
Standard_Ratio = 1.25
Standard_Ratio_Method = 'Dittus-Boelert'
Status = 'success'

(Enables meta-analysis and result filtering)
```

---

## Common Workflows

### Workflow 1: Normalize Raw Data

```python
# Paper has raw Nu and f values
# These need baseline normalization

result_df, log, status = base_engine.process_paper(geometric_df)

for method, count in log['methods_used'].items():
    print(f"{method}: {count} values normalized")
```

### Workflow 2: Handle Pre-Normalized Data

```python
# Paper provides Nu/Nu_Dittus values
# Need to uncover actual baseline and convert to standard

# 'Uncover' logic automatically detects:
# Nu/Nu_Dittus → Dittus-Boelert baseline
# Converts to standard: Nu/Nu_0

print("Uncover decisions:")
print(result_df['Status'].value_counts())
```

### Workflow 3: Cross-Baseline Normalization

```python
# Some papers use different baselines
# standardize all to single format

# Check which baselines were used
baselines = result_df['Standard_Ratio_Method'].unique()
print(f"Baselines in dataset: {baselines}")

# All converted to Nu/Nu_0 or f/f_0 format (standard)
```

---

## Integration with Pipeline

```
GeometricEngine Output (with geometric parameters)
    ↓
BaselineEngine.process_paper()
    ├─ Identify variable types
    ├─ Calculate baselines
    ├─ Normalize raw values
    ├─ Detect/uncover baseline methods
    ├─ Convert St → Nu if needed
    └─ Add source tracking columns
    ↓
Processed DataFrame (with Standard_Ratio + method)
    ↓
StitchingEngine.stitch_paper() (next step in pipeline)
```

---

## Related Documentation

- [INDEX.md](INDEX.md) — Overview and pipeline architecture
- [config.py.md](config.py.md) — Configuration for correlation formulas
- [geometric_engine.py.md](geometric_engine.py.md) — Previous processing step
- [stitching_engine.py.md](stitching_engine.py.md) — Next processing step
- [preprocessor.py.md](preprocessor.py.md) — Uses BaselineEngine in pipeline
