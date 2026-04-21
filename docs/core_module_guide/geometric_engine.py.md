# geometric_engine.py — Geometric Parameter Processing Reference

## Overview

The **geometric_engine.py** module implements **Task 1: Geometric Parameter Processing**. It handles derivation, validation, and source tracking of the 5 core geometric parameters:
- P/e (Pitch to rib height ratio)
- e/D (Rib height to hydraulic diameter)
- Alpha (Rib angle in degrees)
- Geometry (Rib geometry type)
- Aspect Ratio (Channel width to height)

**Key Responsibility**: Process and derive geometric parameters with safety checks and complete source tracking.

---

## GeometricEngine Class

### Initialization

**Signature:**
```python
class GeometricEngine:
    def __init__(self, verbose: bool = False):
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `verbose` | bool | False | Enable verbose logging for debugging |

**Attributes:**
- `verbose`: Logging verbosity flag
- `derivation_log`: List tracking all derivation decisions

**Example:**
```python
from ribs_core.geometric_engine import GeometricEngine

# Standard initialization
geo_engine = GeometricEngine()

# With verbose logging
geo_engine_verbose = GeometricEngine(verbose=True)
```

---

## Core Methods

### parse_numeric_value(value: Any) → Optional[float]

Parses numeric values with flexible unit and format handling.

**Signature:**
```python
@staticmethod
def parse_numeric_value(value: Any) -> Optional[float]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `value` | Any | Value to parse (string, number, None) |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| float_value | Optional[float] | Parsed numeric value or None |

**Supported Formats:**
- ✓ Plain numbers: `5.2` → `5.2`
- ✓ Ratios: `"1/4"` → `0.25`
- ✓ Units: `"25.5 mm"` → `25.5`
- ✓ Degrees: `"45 deg"` → `45.0`
- ✓ Percentages: `"50%"` → `50.0`
- ✓ Mixed: `"1/4 mm"` → `0.25`

**Behavior:**
- Returns None for NaN or null values
- Returns None for unparseable strings
- Case-insensitive
- Strips whitespace automatically

**Example:**
```python
from ribs_core.geometric_engine import GeometricEngine

# All these work:
GeometricEngine.parse_numeric_value(5.2)          # 5.2
GeometricEngine.parse_numeric_value("1/4")        # 0.25
GeometricEngine.parse_numeric_value("25.5 mm")    # 25.5
GeometricEngine.parse_numeric_value("45 degrees") # 45.0
GeometricEngine.parse_numeric_value(None)         # None
```

---

### load_paper_data(paper_dir: Path) → Tuple[pd.DataFrame, Dict[str, Any]]

Loads raw_data.csv and manifest.json from paper directory.

**Signature:**
```python
def load_paper_data(self, paper_dir: Path) -> Tuple[pd.DataFrame, Dict[str, Any]]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `paper_dir` | Path | Path to paper staging directory (contains raw_data.csv and manifest.json) |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| raw_data_df | pd.DataFrame | Loaded raw data |
| manifest_dict | Dict | Parsed manifest configuration |

**Expected Files in paper_dir:**
- `raw_data.csv` — Raw experimental data
- `manifest.json` — Channel dimensions and constants

**Raises:**
- `FileNotFoundError` — If required files are missing
- `ValueError` — If data is invalid or corrupted

**Example:**
```python
from pathlib import Path

geo_engine = GeometricEngine()
raw_data, manifest = geo_engine.load_paper_data(Path('Staging/P001'))

print(f"Loaded {len(raw_data)} rows from P001")
print(f"Channel geometry: {manifest['Experimental Apparatus']['Channel Geometry']}")
```

---

### extract_manifest_constants(manifest: Dict) → Dict[str, float]

Extracts channel dimensions and constants from manifest.

**Signature:**
```python
def extract_manifest_constants(self, manifest: Dict[str, Any]) -> Dict[str, float]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `manifest` | Dict | Parsed manifest.json content |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| constants | Dict[str, float] | Extracted constants like Width, Height, Pitch, etc. |

**Extracted Constants Include:**
- Width, Height, Length (channel dimensions)
- Pitch, Rib Height (rib dimensions)
- Hydraulic Diameter
- Aspect Ratio
- All other numeric constants from manifest

**Example:**
```python
constants = geo_engine.extract_manifest_constants(manifest)

print(f"Width: {constants.get('Width')} mm")
print(f"Rib Height: {constants.get('Rib Height')} mm")
print(f"Pitch: {constants.get('Pitch')} mm")
```

---

### get_varied_parameters(raw_data: pd.DataFrame) → List[str]

Identifies which geometric parameters vary across the dataset.

**Signature:**
```python
def get_varied_parameters(self, raw_data: pd.DataFrame) -> List[str]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `raw_data` | pd.DataFrame | Raw data from paper |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| varied_params | List[str] | Names of parameters that have >1 unique non-NaN value |

**Purpose:**
Implements the **Safety Trigger** mechanism. Parameters that vary across data are NOT auto-filled if missing, because they're intentionally varied in the experiment.

**Example:**
```python
# In Figure 1, Reynolds varies but Geometry is constant
varied = geo_engine.get_varied_parameters(figure_1_data)
print(varied)  # ['Reynolds number (Re)']

# Safety Trigger: Don't auto-fill Re even if missing
```

---

### Atomic Derivation Methods

#### derive_aspect_ratio(width: float, height: float) → float

**Signature:**
```python
def derive_aspect_ratio(self, width: float, height: float) -> float:
```

**Formula:** `Aspect Ratio = Width / Height`

**Example:**
```python
aspect_ratio = geo_engine.derive_aspect_ratio(width=20, height=10)
print(aspect_ratio)  # 2.0
```

---

#### derive_relative_roughness(rib_height: float, hydraulic_diameter: float) → float

**Signature:**
```python
def derive_relative_roughness(self, rib_height: float, hydraulic_diameter: float) -> float:
```

**Formula:** `e/D = Rib Height / Hydraulic Diameter`

**Example:**
```python
e_d = geo_engine.derive_relative_roughness(rib_height=0.5, hydraulic_diameter=5.0)
print(e_d)  # 0.1
```

---

#### derive_pitch_to_height(pitch: float, rib_height: float) → float

**Signature:**
```python
def derive_pitch_to_height(self, pitch: float, rib_height: float) -> float:
```

**Formula:** `P/e = Pitch / Rib Height`

**Example:**
```python
p_e = geo_engine.derive_pitch_to_height(pitch=2.6, rib_height=0.5)
print(p_e)  # 5.2
```

---

### Main Processing Method

#### process_paper(paper_dir: Path) → Tuple[pd.DataFrame, Dict[str, Any], str]

Main orchestration method that processes all geometric parameters for a paper.

**Signature:**
```python
def process_paper(
    self,
    paper_dir: Path
) -> Tuple[pd.DataFrame, Dict[str, Any], str]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `paper_dir` | Path | Path to paper staging directory |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| processed_df | pd.DataFrame | Data with derived geometric parameters |
| log | Dict | Processing decisions log |
| status | str | 'success', 'warning', or 'error' |

**Processing Steps:**
1. ✓ Load raw_data.csv and manifest.json
2. ✓ Extract manifest constants
3. ✓ Identify varied parameters (Safety Trigger)
4. ✓ Fill missing parameters from constants
5. ✓ Derive missing parameters atomically
6. ✓ Create [Param]_Source tracking columns
7. ✓ Log all decisions

**Output Columns Added:**
- `P/e_Source` — Source of P/e value
- `e/D_Source` — Source of e/D value
- `Alpha_Source` — Source of Alpha value
- `Geometry_Source` — Source of Geometry value
- `Aspect_Ratio_Source` — Source of Aspect Ratio

**Source Values:**
- `'manifest'` — Value from experiment manifest
- `'derived'` — Calculated from other parameters
- `'original'` — Was in original raw data
- `'derived_with_warning'` — Derived but dependencies partially missing

**Example:**
```python
from pathlib import Path

geo_engine = GeometricEngine(verbose=True)
processed_df, log, status = geo_engine.process_paper(Path('Staging/P001'))

print(f"Status: {status}")
print(f"Rows processed: {len(processed_df)}")
print(f"Parameters derived: {log['derived_count']}")

# Check source tracking
print(processed_df['P/e_Source'].value_counts())
# manifest    45
# derived     20
# original    35
```

---

## Processing Logic

### Safety Trigger (Parameter Variation Safety)

```
For each parameter:
  IF parameter is in varied_parameters list:
    → DON'T auto-fill missing values
    → Reason: Parameter is intentionally varied
  ELSE:
    → Safe to auto-fill from manifest constants
```

**Example:**
```
Figure 1 Data:
  Re: [1000, 2000, 4000, 8000] ← Varies
  P/e: [5.2, 5.2, 5.2, 5.2] ← Constant
  
Processing:
  - Re: Don't auto-fill (it varies intentionally)
  - P/e: OK to auto-fill from manifest if missing
```

### Atomic Derivation Chain

```
Manifest Constants:
  Width = 20mm, Height = 10mm, Pitch = 2.6mm, Rib Height = 0.5mm
  
Missing In Data:
  Aspect Ratio, P/e, e/D
  
Derivation:
  Aspect Ratio = Width / Height = 20 / 10 = 2.0
  P/e = Pitch / Rib Height = 2.6 / 0.5 = 5.2
  e/D = Rib Height / Dh = (calculated Dh required)
```

### Source Tracking

Every derived value gets a `_Source` column indicating:
- ✓ Where the value came from
- ✓ How reliable it is
- ✓ What assumptions were made

**Example:**
```
Row 1: P/e = 5.2, P/e_Source = 'manifest'
Row 2: P/e = 5.2, P/e_Source = 'derived'
Row 3: P/e = NaN, P/e_Source = 'derived_with_warning' (missing dependency)
```

---

## Common Workflows

### Workflow 1: Process Single Paper

```python
from pathlib import Path
from ribs_core.geometric_engine import GeometricEngine

geo = GeometricEngine(verbose=True)
result_df, log, status = geo.process_paper(Path('Staging/P001'))

if status == 'success':
    print("Geometric parameters processed successfully")
    print(f"Derived {log['derived_count']} values")
else:
    print(f"Warning: {status}")
    print(f"Errors: {log.get('errors', [])}")
```

### Workflow 2: Check Derived Parameters

```python
# Check which parameters were derived vs. original
for param in ['P/e', 'e/D', 'Alpha', 'Aspect ratio']:
    source_col = f'{param}_Source'
    if source_col in result_df.columns:
        counts = result_df[source_col].value_counts()
        print(f"{param}:")
        print(f"  {counts}")
```

### Workflow 3: Validate Against Safety Triggers

```python
# Check if varied parameters were accidentally filled
varied = geo.get_varied_parameters(raw_data)
print(f"Varied parameters: {varied}")

# These should NOT have been auto-filled
for param in varied:
    if f'{param}_Source' in result_df.columns:
        derived_count = (result_df[f'{param}_Source'] == 'derived').sum()
        if derived_count > 0:
            print(f"WARNING: {param} was derived but is marked as varied!")
```

---

## Integration with Pipeline

```
raw_data.csv + manifest.json
    ↓
GeometricEngine.process_paper()
    ├─ Parse numeric values
    ├─ Extract manifest constants
    ├─ Identify varied parameters
    ├─ Auto-fill missing values (with Safety Trigger)
    ├─ Derive missing geometricparameters
    └─ Add source tracking columns
    ↓
Processed DataFrame (with [Param]_Source columns)
    ↓
BaselineEngine.process_paper() (next step in pipeline)
```

---

## Related Documentation

- [INDEX.md](INDEX.md) — Overview and pipeline architecture
- [config.py.md](config.py.md) — Configuration for geometric derivations
- [baseline_engine.py.md](baseline_engine.py.md) — Next processing step
- [preprocessor.py.md](preprocessor.py.md) — Uses GeometricEngine in pipeline
