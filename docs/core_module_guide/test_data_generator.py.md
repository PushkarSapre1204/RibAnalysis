# test_data_generator.py — Test Data Generation Reference

## Overview

The **test_data_generator.py** module provides utilities for creating synthetic test data. It generates realistic test papers with controlled parameters for:
- Unit testing pipeline components
- Validation and debugging
- Feature testing (Safety Trigger, Atomic Derivation, etc.)
- Reproducible test scenarios

**Key Responsibility**: Generate high-quality synthetic test datasets that mimic real research papers.

---

## Module Functions

### create_test_paper_heat_transfer(staging_dir: Path) → Path

Creates a realistic test paper with heat transfer (Nusselt) data.

**Signature:**
```python
def create_test_paper_heat_transfer(staging_dir: Path) -> Path:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `staging_dir` | Path | Path to Staging directory (test paper will be created as subdirectory) |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| paper_dir | Path | Path to created test paper directory |

**Features:**
- ✓ 10 data points (2 figures) — 5 points each
- ✓ Nu data (raw values): 15.2, 18.5, 22.3, 28.7, 35.6
- ✓ Nu ratio data: 1.2, 1.3, 1.35, 1.4, 1.45 (normalized)
- ✓ Constant geometric parameters (W=20mm, H=10mm, e=0.5mm)
- ✓ Varying Reynolds numbers (1000 to 10000)
- ✓ Dittus-Boelert baseline normalization
- ✓ Rectangular rib geometry

**Output Files Created:**
- `{staging_dir}/test_paper_heat_transfer/raw_data.csv`
- `{staging_dir}/test_paper_heat_transfer/manifest.json`

**CSV Data:**
```
Paper Title: "Test Heat Transfer Study"
Figure 1: Nu data (raw values) with varying Re
Figure 2: Nu/Nu0 ratio data with same Re range
Constant parameters: Geometry=Rectangular, P/e=5.2, Alpha=45, Walls=2
```

**Manifest Data:**
```json
{
  "Paper Identification": {
    "Title": "Test Heat Transfer Study",
    "Authors/Year": "Test Author 2024"
  },
  "Experimental Apparatus": {
    "Channel Dimensions": {
      "Width": 20,
      "Height": 10,
      "Length": 200
    },
    "Rib Dimensions": {
      "Width": 0.8,
      "Height": 0.5,
      "Pitch": 2.6
    }
  },
  "Boundary Conditions": {
    "Reynolds Range": [1000, 10000],
    "Prandtl": 0.71
  }
}
```

**Example:**
```python
from pathlib import Path
from ribs_core.test_data_generator import create_test_paper_heat_transfer

test_paper_dir = create_test_paper_heat_transfer(Path('Staging'))
print(f"Test paper created: {test_paper_dir}")

# Files created:
# - Staging/test_paper_heat_transfer/raw_data.csv
# - Staging/test_paper_heat_transfer/manifest.json
```

---

### create_test_paper_friction(staging_dir: Path) → Path

Creates a test paper with friction factor (f) data.

**Signature:**
```python
def create_test_paper_friction(staging_dir: Path) -> Path:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `staging_dir` | Path | Path to Staging directory |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| paper_dir | Path | Path to created test paper directory |

**Features:**
- ✓ Friction factor data (raw values)
- ✓ Friction ratio data (f/f_0)
- ✓ Blasius baseline normalization
- ✓ Rectangular rib geometry
- ✓ Constant parameters
- ✓ Varying Reynolds numbers

**Output Files:**
- `{staging_dir}/test_paper_friction/raw_data.csv`
- `{staging_dir}/test_paper_friction/manifest.json`

**Example:**
```python
test_paper_dir = create_test_paper_friction(Path('Staging'))
```

---

### create_test_paper_mixed_variables(staging_dir: Path) → Path

Creates a test paper with mixed variable types (Nu, St, f, and their ratios).

**Signature:**
```python
def create_test_paper_mixed_variables(staging_dir: Path) -> Path:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `staging_dir` | Path | Path to Staging directory |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| paper_dir | Path | Path to created test paper directory |

**Features:**
- ✓ Multiple variables: Nu, Nu/Nu0, St, St/St0, f, f/f0
- ✓ Tests variable identification and conversion
- ✓ Tests Stanton-to-Nusselt conversion
- ✓ Realistic parameter combinations

**Use Case:**
Testing the BaselineEngine's variable identification and unit conversion logic.

**Example:**
```python
test_paper_dir = create_test_paper_mixed_variables(Path('Staging'))
```

---

### create_test_paper_varied_parameters(staging_dir: Path) → Path

Creates a test paper to validate Safety Trigger mechanism.

**Signature:**
```python
def create_test_paper_varied_parameters(staging_dir: Path) -> Path:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `staging_dir` | Path | Path to Staging directory |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| paper_dir | Path | Path to created test paper directory |

**Features:**
- ✓ Paper where some parameters intentionally vary
- ✓ P/e varies (5.0, 5.2, 5.4) — should NOT be auto-filled
- ✓ Geometry varies (Rectangular, Trapezoidal)
- ✓ Alpha constant (45°) — safe to auto-fill
- ✓ Tests that Safety Trigger blocks derivation for varied params

**Use Case:**
Verify that parameters marked as "varied" are not automatically filled, even if derivable.

**Example:**
```python
test_paper_dir = create_test_paper_varied_parameters(Path('Staging'))

# This paper should trigger Safety Trigger mechanism:
# - P/e varies → Don't auto-fill P/e
# - Geometry varies → Don't auto-fill related params
# - Alpha is constant → Safe to auto-fill if missing
```

---

### create_test_paper_missing_values(staging_dir: Path) → Path

Creates a test paper with missing/NaN values to test error handling.

**Signature:**
```python
def create_test_paper_missing_values(staging_dir: Path) -> Path:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `staging_dir` | Path | Path to Staging directory |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| paper_dir | Path | Path to created test paper directory |

**Features:**
- ✓ Some Re values missing (marked N/A)
- ✓ Some geometric parameters missing
- ✓ Some measurements missing
- ✓ Tests how pipeline handles incomplete data
- ✓ Tests derivation when dependencies missing

**Use Case:**
Verify robustness when data is incomplete or partially missing.

**Example:**
```python
test_paper_dir = create_test_paper_missing_values(Path('Staging'))

# Tests:
# - Handling of N/A values
# - Derivation when dependencies missing
# - Atomic derivation with partial information
```

---

### create_comprehensive_test_dataset(staging_dir: Path) → Dict[str, Path]

Creates a complete test dataset with all test paper types.

**Signature:**
```python
def create_comprehensive_test_dataset(staging_dir: Path) -> Dict[str, Path]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `staging_dir` | Path | Path to Staging directory |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| papers | Dict[str, Path] | Dictionary mapping test paper names to their paths |

**Returns Dictionary:**
```python
{
    'heat_transfer': Path('Staging/test_paper_heat_transfer'),
    'friction': Path('Staging/test_paper_friction'),
    'mixed_variables': Path('Staging/test_paper_mixed_variables'),
    'varied_parameters': Path('Staging/test_paper_varied_parameters'),
    'missing_values': Path('Staging/test_paper_missing_values'),
}
```

**Behavior:**
- ✓ Creates all test paper types
- ✓ Comprehensive test coverage
- ✓ Returns mapping of all created papers

**Use Case:**
Run complete preprocessing pipeline on all test papers at once to validate the entire system.

**Example:**
```python
from ribs_core.test_data_generator import create_comprehensive_test_dataset
from ribs_core.preprocessor import MetaAnalysisPreprocessor
from pathlib import Path

# Create all test papers
test_papers = create_comprehensive_test_dataset(Path('Staging'))
print(f"Created {len(test_papers)} test papers")

# Run pipeline on test data
preprocessor = MetaAnalysisPreprocessor(
    staging_dir=Path('Staging'),
    verbose=True
)

success = preprocessor.run()

if success:
    print("✓ Pipeline works correctly on all test papers")
else:
    print("✗ Pipeline failed on some test papers")
```

---

## Common Workflows

### Workflow 1: Test Single Component

```python
from pathlib import Path
from ribs_core.test_data_generator import create_test_paper_heat_transfer
from ribs_core.geometric_engine import GeometricEngine

# Create test data
test_dir = create_test_paper_heat_transfer(Path('Staging'))

# Test GeometricEngine
geo_engine = GeometricEngine(verbose=True)
result, log, status = geo_engine.process_paper(test_dir)

print(f"Status: {status}")
print(f"Derived parameters: {log.get('derived_count', 0)}")
```

### Workflow 2: Test Variable Identification

```python
from ribs_core.test_data_generator import create_test_paper_mixed_variables
from ribs_core.baseline_engine import BaselineEngine

# Create test data with mixed variable types
test_dir = create_test_paper_mixed_variables(Path('Staging'))

# Load and process
import pandas as pd
raw_data = pd.read_csv(test_dir / 'raw_data.csv')

base_engine = BaselineEngine()

for var in raw_data['Variable'].unique():
    base_var, fmt = base_engine.identify_variable_type(var)
    print(f"{var} → Base: {base_var}, Format: {fmt}")
```

### Workflow 3: Test Safety Trigger

```python
from ribs_core.test_data_generator import create_test_paper_varied_parameters
from ribs_core.geometric_engine import GeometricEngine
import pandas as pd

# Create test data where parameters vary
test_dir = create_test_paper_varied_parameters(Path('Staging'))

raw_data = pd.read_csv(test_dir / 'raw_data.csv')

geo_engine = GeometricEngine()

# Check which parameters are varied
varied = geo_engine.get_varied_parameters(raw_data)
print(f"Varied parameters: {varied}")
# Expected: ['P/e', 'Geometry', ...]

# Process and verify Safety Trigger
result, log, status = geo_engine.process_paper(test_dir)

# Verify varied parameters were not auto-filled
for param in varied:
    source_col = f'{param}_Source'
    if source_col in result.columns:
        derived_count = (result[source_col] == 'derived').sum()
        assert derived_count == 0, f"{param} should not be derived (it varies)"
```

### Workflow 4: Full Pipeline Test

```python
from ribs_core.test_data_generator import create_comprehensive_test_dataset
from ribs_core.preprocessor import MetaAnalysisPreprocessor
from pathlib import Path
import pandas as pd

# Create comprehensive test data
print("Creating test dataset...")
test_papers = create_comprehensive_test_dataset(Path('Staging'))

# Run pipeline on test data
print("Running preprocessing pipeline...")
preprocessor = MetaAnalysisPreprocessor(
    staging_dir=Path('Staging'),
    verbose=True
)

success = preprocessor.run()

# Verify outputs
if success:
    master_df = pd.read_csv('data/clean_data_master.csv')
    print(f"✓ Master CSV created: {len(master_df)} rows")
    print(f"  Papers: {master_df['Paper Title'].nunique()}")
    print(f"  Variables: {master_df['Variable'].unique()}")
else:
    print("✗ Pipeline failed")
```

### Workflow 5: Test Error Handling

```python
from ribs_core.test_data_generator import create_test_paper_missing_values
from ribs_core.geometric_engine import GeometricEngine
from pathlib import Path

# Create test data with missing values
test_dir = create_test_paper_missing_values(Path('Staging'))

# Process and check how errors are handled
geo_engine = GeometricEngine(verbose=True)
result, log, status = geo_engine.process_paper(test_dir)

print(f"Status: {status}")  # Might be 'warning'
print(f"Errors: {log.get('errors', [])}")
print(f"Warnings: {log.get('warnings', [])}")

# Check which rows had issues
if 'warning' in result.get('Status', []):
    warning_rows = result[result['Status'] == 'warning']
    print(f"Rows with warnings: {len(warning_rows)}")
```

---

## Test Data Characteristics

### Heat Transfer Test Paper

| Characteristic | Value |
|---|---|
| **Paper Name** | test_paper_heat_transfer |
| **Variables** | Nu (raw), Nu/Nu0 (normalized) |
| **Data Points** | 10 total (5 per figure) |
| **Re Range** | 1000 to 10000 |
| **Geometry** | Rectangular, constant |
| **P/e** | 5.2 (constant) |
| **Expected Baseline** | Dittus-Boelert |

### Friction Test Paper

| Characteristic | Value |
|---|---|
| **Paper Name** | test_paper_friction |
| **Variables** | f (raw), f/f0 (normalized) |
| **Data Points** | 10 total |
| **Re Range** | 1000 to 10000 |
| **Expected Baseline** | Blasius |

### Mixed Variables Test Paper

| Characteristic | Value |
|---|---|
| **Paper Name** | test_paper_mixed_variables |
| **Variables** | Nu, Nu/Nu0, St, St/St0, f, f/f0 |
| **Tests** | Variable identification, unit conversion |
| **Special Focus** | Stanton-to-Nusselt conversion |

### Varied Parameters Test Paper

| Characteristic | Value |
|---|---|
| **Paper Name** | test_paper_varied_parameters |
| **Varied Params** | P/e, Geometry |
| **Constant Params** | Alpha, Re |
| **Tests** | Safety Trigger mechanism |
| **Expected Outcome** | Varied params NOT auto-filled |

### Missing Values Test Paper

| Characteristic | Value |
|---|---|
| **Paper Name** | test_paper_missing_values |
| **Missing Data** | Some Re, geometric params partially missing |
| **Tests** | Error handling, robustness |
| **Expected Outcome** | Graceful degradation, derivation with warnings |

---

## Integration with Testing

### Unit Tests

```python
def test_geometric_engine():
    from ribs_core.test_data_generator import create_test_paper_heat_transfer
    from ribs_core.geometric_engine import GeometricEngine
    
    test_dir = create_test_paper_heat_transfer(Path('Staging'))
    geo_engine = GeometricEngine()
    result, log, status = geo_engine.process_paper(test_dir)
    
    assert status == 'success'
    assert len(result) == 10
    assert 'P/e_Source' in result.columns

def test_baseline_engine():
    from ribs_core.test_data_generator import create_test_paper_mixed_variables
    from ribs_core.baseline_engine import BaselineEngine
    
    test_dir = create_test_paper_mixed_variables(Path('Staging'))
    base_engine = BaselineEngine()
    # ... test logic
```

### Integration Tests

```python
def test_full_pipeline():
    from ribs_core.test_data_generator import create_comprehensive_test_dataset
    from ribs_core.preprocessor import MetaAnalysisPreprocessor
    
    test_papers = create_comprehensive_test_dataset(Path('Staging'))
    preprocessor = MetaAnalysisPreprocessor(staging_dir=Path('Staging'))
    
    success = preprocessor.run()
    assert success
```

---

## Related Documentation

- [INDEX.md](INDEX.md) — Overview and pipeline architecture
- [preprocessor.py.md](preprocessor.py.md) — Uses test data with preprocessor
- [geometric_engine.py.md](geometric_engine.py.md) — Test geometric processing
- [baseline_engine.py.md](baseline_engine.py.md) — Test baseline calculations
- [stitching_engine.py.md](stitching_engine.py.md) — Test output stitching
