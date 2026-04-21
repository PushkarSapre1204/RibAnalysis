# config.py — Configuration Reference

## Overview

The **config.py** module is the centralized configuration file for the entire preprocessing pipeline. It defines the data schema, processing rules, correlation formulas, and output settings without requiring modifications to the main scripts.

**Key Responsibility**: Provide all configurable parameters in one place for easy customization and maintenance.

---

## Configuration Sections

### 1. Data Schema Definition

#### PARAMETER_COLUMNS
```python
PARAMETER_COLUMNS = [
    'Reynolds number (Re)',
    'Geometry',
    'P/e',
    'e/D',
    'Alpha',
    'Aspect ratio',
    'Number of ribbed walls'
]
```
**Purpose**: Defines the 7 geometric parameters analyzed to select plot axes

**Impact**: Only listed parameters are included in axis selection and variability analysis
**Customization**: Add custom parameters to analyze additional geometric features

#### CORE_COLUMNS
```python
CORE_COLUMNS = ['Paper Title', 'Figure Number', 'Variable', 'Value']
```
**Purpose**: Defines mandatory identification columns

**Impact**: Data must have these 4 columns to load successfully

#### TEST_CONDITION_COLUMNS
```python
TEST_CONDITION_COLUMNS = [
    'Reading on',
    'Constant factor'
]
```
**Purpose**: Defines test condition columns (shown in titles, not used for axes)

**Impact**: These values appear in subplot titles but don't affect axis selection

#### ADDITIONAL_DATA_COLUMNS
```python
ADDITIONAL_DATA_COLUMNS = ['Dittus-Boelter Value']
```
**Purpose**: Informational columns not used in processing

**Impact**: These columns are preserved but not analyzed

---

### 2. Baseline Correlations

#### CORRELATIONS Dictionary

Defines all available correlation formulas for heat transfer and friction calculations:

```python
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
```

**Parameters for each correlation**:
- `variable`: Heat transfer variable ('Nu' or 'f')
- `formula`: Lambda function implementing the correlation
- `description`: Human-readable formula description
- `is_standard`: Whether this is a standard baseline correlation

**Usage**: BaselineEngine uses this to calculate baseline values for normalization

**Customization**: Add new correlations by appending to the CORRELATIONS dictionary

---

### 3. Geometric Parameter Derivations

#### GEOMETRIC_DERIVATIONS

Defines atomic relationships for parameter derivation:

```python
GEOMETRIC_DERIVATIONS = {
    'Aspect ratio': {
        'dependencies': ['Width', 'Height'],
        'formula': lambda w, h: w / h,
        'units': 'dimensionless',
        'description': 'Channel width / height',
    },
    'e/D': {
        'dependencies': ['Rib Height', 'Hydraulic Diameter'],
        'formula': lambda e, dh: e / dh,
        'units': 'dimensionless',
        'description': 'Rib height / hydraulic diameter',
    },
    'P/e': {
        'dependencies': ['Pitch', 'Rib Height'],
        'formula': lambda p, e: p / e,
        'units': 'dimensionless',
        'description': 'Pitch / rib height',
    },
}
```

**Purpose**: Automatically calculate missing geometric parameters from manifest constants

**Impact**: Unknown parameters are derived instead of marked as NaN if dependencies are available

**Safety Check**: Atomic derivation is skipped if the parameter is in the varied_parameters list (Safety Trigger)

---

### 4. Output Schema Configuration

#### STITCHING_MASTER_SCHEMA
```python
STITCHING_MASTER_SCHEMA = [
    'Paper Title',
    'Figure Number',
    'Point ID',
    'Variable',
    'Value',  # Replaced with Standard_Ratio (normalized)
    'Reynolds number (Re)',
    'Geometry',
    'P/e',
    'e/D',
    'Alpha',
    'Aspect ratio',
    'Number of ribbed walls',
]
```

**Purpose**: Defines columns in the final clean_data.csv output

**Impact**: Only these columns appear in the standardized output; all other processing columns are dropped

#### STITCHING_LOG_SCHEMA
```python
STITCHING_LOG_SCHEMA = [
    'Paper Title',
    'Figure Number',
    'Point ID',
    'Variable',
    'Original_Value',
    'Standard_Ratio',  # Normalized value
    'Standard_Ratio_Method',  # Baseline method used
    'P/e_Source',
    'e/D_Source',
    # ... all [Parameter]_Source columns
]
```

**Purpose**: Defines columns in the clean_data_log.csv (metadata and source tracking)

**Impact**: Enables complete lineage tracking of all processing decisions

---

### 5. Processing Parameters

#### Missing Value Handling
```python
MISSING_VALUE_STRINGS = ['N/A', 'NA', 'n/a', 'na', 'None', '']
```
**Impact**: All these strings are converted to NaN for consistent handling

#### Minimum Data Points
```python
MIN_DATA_POINTS = 1  # Set >1 to skip sparse plots
```
**Impact**: Figures with fewer than this many points are skipped

#### Numeric Conversion
```python
NUMERIC_PARAMETERS = [
    'Reynolds number (Re)',
    'P/e',
    'e/D',
    'Alpha',
    'Aspect ratio',
    'Number of ribbed walls'
]
```
**Impact**: These columns are converted to numeric types; non-numeric values become NaN

---

### 6. Priority & Tie-Breaking

#### X_AXIS_PRIORITY
```python
X_AXIS_PRIORITY = [
    'Reynolds number (Re)',
    'P/e',
    'e/D',
    'Alpha',
    'Aspect ratio',
    'Number of ribbed walls',
]
```

**Purpose**: When multiple parameters have equal variability, use this priority for X-axis selection

**Impact**: Re is preferred for X-axis if there's a tie

#### LEGEND_PRIORITY
```python
LEGEND_PRIORITY = [
    'Alpha',
    'Aspect ratio',
    'P/e',
    'e/D',
    'Reynolds number (Re)',
    'Number of ribbed walls',
]
```

**Purpose**: When multiple parameters have equal variability, use this priority for legend selection

**Impact**: Alpha is preferred for legend if there's a tie

---

### 7. Logging & Output

#### Logging Configuration
```python
VERBOSITY = 'normal'  # 'quiet', 'normal', 'verbose'
SAVE_DEBUG_INFO = False  # Create debug CSV with details
DEBUG_INFO_DIR = './debug'
```

**Impact**: Controls output detail level during processing

#### Output Directories
```python
PREPROCESSOR_LOGGING_DIR = 'preprocessing_logs'
PREPROCESSOR_MASTER_OUTPUT_DIR = 'data'
```

**Impact**: Where processing logs and master CSVs are saved

---

## How to Customize

### Example 1: Add a Custom Correlation

```python
CORRELATIONS['Custom_Correlation'] = {
    'variable': 'Nu',
    'formula': lambda re, pr: 0.025 * (re ** 0.8) * (pr ** 0.35),
    'description': 'Custom: Nu = 0.025 * Re^0.8 * Pr^0.35',
    'is_standard': False,
}
```

Then reference it in data like: `Variable = 'Nu/Nu_Custom_Correlation'`

### Example 2: Add a Custom Geometric Parameter

```python
PARAMETER_COLUMNS.append('Custom_Ratio')

GEOMETRIC_DERIVATIONS['Custom_Ratio'] = {
    'dependencies': ['Parameter_A', 'Parameter_B'],
    'formula': lambda a, b: a / b,
    'units': 'dimensionless',
    'description': 'Parameter A / Parameter B',
}
```

### Example 3: Change Output Schema

```python
# Add custom columns to output
STITCHING_MASTER_SCHEMA.extend([
    'Custom_Field_1',
    'Custom_Field_2',
])
```

---

## Impact of Configuration Changes

| Change | Impact | Risk Level |
|--------|--------|------------|
| Add PARAMETER_COLUMNS | New parameters included in axis selection | Low |
| Modify correlation formula | Changes baseline values globally | **High** |
| Change STITCHING_MASTER_SCHEMA | Output columns change; validation tools may fail | **High** |
| Add GEOMETRIC_DERIVATIONS | Auto-fills more missing values | Low |
| Modify MISSING_VALUE_STRINGS | Different values treated as NaN | Medium |
| Change X_AXIS_PRIORITY | Plot axis selection changes | Low |

---

## Validation

When modifying config.py:

1. ✅ Ensure all formula lambdas have correct parameter count
2. ✅ Verify STITCHING_MASTER_SCHEMA matches downstream tools' expectations
3. ✅ Test with test_data_generator to verify correlations
4. ✅ Check logging directory is writable

---

## Related Documentation

- [INDEX.md](INDEX.md) — Overview and quick start
- [baseline_engine.py.md](baseline_engine.py.md) — Uses CORRELATIONS
- [geometric_engine.py.md](geometric_engine.py.md) — Uses GEOMETRIC_DERIVATIONS
- [stitching_engine.py.md](stitching_engine.py.md) — Uses STITCHING_*_SCHEMA
