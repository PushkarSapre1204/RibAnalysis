# RIBS Core Module Documentation

## Overview

The **ribs_core** module is a comprehensive meta-analysis preprocessing pipeline designed to process experimental heat transfer and fluid mechanics research data. It automates the standardization, normalization, and validation of complex parameter data from multiple research papers into a unified schema.

### Key Purpose

Transform raw experimental data from diverse research papers into:
- Standardized, schema-compliant datasets
- Normalized heat transfer and friction factor values
- Complete processing lineage and decision tracking
- Quality-assured master datasets for meta-analysis

---

## Pipeline Architecture

### Overall Pipeline Flow

```
┌─────────────────────────────────────────────────┐
│ INPUT: Raw Data from Staging Directory          │
│ (raw_data.csv + manifest.json per paper)        │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │   GEOMETRIC ENGINE   │  (Task 1)
        │  Process Parameters: │
        │  • P/e, e/D, Alpha   │
        │  • Geometry          │
        │  • Aspect Ratio      │
        │                      │
        │ - Safety Trigger     │
        │ - Atomic Derivation  │
        │ - Source Tracking    │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │  BASELINE ENGINE     │  (Task 2)
        │ Normalize & Convert: │
        │  • Identify vars     │
        │  • St → Nu conver.   │
        │  • Calculate baseline│
        │  • "Uncover" logic   │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │  STITCHING ENGINE    │  (Task 3/4)
        │  Separate Outputs:   │
        │  • clean_data.csv    │
        │  • clean_data_log.csv│
        │ (schema + metadata)  │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │  MASTER AGGREGATION  │
        │  Combine all papers: │
        │  • clean_data_master │
        │  • master_log        │
        └──────────────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ OUTPUT: Master Files │
        │  • Schema dataset    │
        │  • Processing log    │
        │  • Decision log      │
        └──────────────────────┘
```

### Data Flow & Dependencies

```
Manual Inputs: Staging folder with paper data
              ↓
GeometricEngine ← reads manifest.json + raw_data.csv
                ↓ (outputs geometric parameters)
BaselineEngine  ← receives geometric output
                ↓ (outputs normalized values)
StitchingEngine ← receives baseline output
                ↓ (separates into schema + metadata)
Master Aggregation (combines all papers)
                ↓
Output CSVs + Logs
```

---
 
## Module Components

This module contains 8 key components:

| Component | Purpose | Role |
|-----------|---------|------|
| [**config.py**](config.py.md) | Centralized configuration | Defines schema, correlations, and settings |
| [**data_loader.py**](data_loader.py.md) | Data input & batching | Loads Excel/CSV, creates hierarchical groups |
| [**geometric_engine.py**](geometric_engine.py.md) | **Task 1**: Parameter processing | Derives geometric parameters with safety checks |
| [**baseline_engine.py**](baseline_engine.py.md) | **Task 2**: Normalization | Calculates baselines, converts units, tracks decisions |
| [**stitching_engine.py**](stitching_engine.py.md) | **Task 3/4**: Output separation | Creates schema + metadata CSVs |
| [**preprocessor.py**](preprocessor.py.md) | **Orchestrator**: Pipeline coordinator | Runs full pipeline, aggregates outputs |
| [**test_data_generator.py**](test_data_generator.py.md) | Test utilities | Generates synthetic test data |
| [**__init__.py**](#) | Module marker | Identifies package |

---

## Quick Start

### Basic Usage: Run Full Pipeline

```python
from ribs_core.preprocessor import MetaAnalysisPreprocessor
from pathlib import Path

# Initialize preprocessor
preprocessor = MetaAnalysisPreprocessor(
    staging_dir=Path('Staging'),
    verbose=True
)

# Run complete pipeline
success = preprocessor.run()

# Outputs:
# - data/clean_data_master.csv (standardized schema)
# - preprocessing_logs/master_preprocessing_log.json (decisions)
```

### Component Usage Flow

```
1. Configure Settings           → config.py
2. Load Data                    → data_loader.py
3. Process Geometry             → geometric_engine.py
4. Normalize Baselines          → baseline_engine.py
5. Separate Schema & Metadata   → stitching_engine.py
6. Aggregate Master CSV         → preprocessor.py (orchestrator)
```

---

## Data Schema

### Input Schema (raw_data.csv)

**15 Required Columns:**
- **Core (5)**: Paper Title, Figure Number, Point ID, Variable, Value
- **Parameters (7)**: Reynolds number (Re), Geometry, P/e, e/D, Alpha, Aspect ratio, Number of ribbed walls
- **Test Conditions (2)**: Reading on, Constant factor
- **Additional (1)**: Dittus-Boelter Value

> Use `N/A` for missing parameter values. Parameters are analyzed to determine data axes and variable types.

### Output Schema (clean_data.csv)

**Standardized Output:**
- Geometric parameters with derivations
- Normalized baseline values (Nu/Nu₀ or f/f₀)
- Source tracking for all values
- Consistent variable symbols (Nu, f, St, etc.)

---

## Key Concepts

### Safety Trigger
Prevents automatic parameter filling if that parameter varies across the dataset. This ensures data integrity when parameters are intentionally varied in experiments.

**Example**: If P/e varies across rows in a figure, the system doesn't auto-fill P/e values for missing entries.

### Atomic Derivation
Calculates missing geometric parameters from manifest constants using atomic relationships:
- **Aspect Ratio** = Width / Height
- **e/Dh** = Rib Height / Hydraulic Diameter
- **P/e** = Pitch / Rib Height

### Source Tracking
Creates `[Parameter]_Source` columns for every derived or processed value:
- `'manifest'` - Value from experiment manifest
- `'derived'` - Calculated from other parameters
- `'baseline_method'` - Normalization method used
- `'warning'` - Data quality flags

### Uncover and Reconvert Logic
When baseline method is unknown:
1. Detects patterns in variable names (e.g., "Nu/Nu0" indicates Dittus-Boelert baseline)
2. Back-calculates the baseline value
3. Converts to standard format
4. Tracks the recovery decision

---

## Common Workflows

### Workflow 1: Process Single Paper

```python
from ribs_core.geometric_engine import GeometricEngine
from ribs_core.baseline_engine import BaselineEngine

# Step 1: Process geometric parameters
geo_engine = GeometricEngine()
geo_df, geo_log = geo_engine.process_paper(paper_dir=Path('Staging/P001'))

# Step 2: Normalize baselines
base_engine = BaselineEngine()
base_df, base_log = base_engine.process_paper(geo_df)

# Result: Fully processed paper data
```

### Workflow 2: Batch Process Multiple Papers

```python
preprocessor = MetaAnalysisPreprocessor(staging_dir=Path('Staging'))
papers = preprocessor.find_paper_directories()

for paper_dir in papers:
    # Each paper goes through full pipeline
    result = preprocessor.process_paper(paper_dir)
    print(f"Processed: {paper_dir.name}")
```

### Workflow 3: Analyze Parameter Variability

```python
from ribs_core.data_loader import create_hierarchical_batches

batches = create_hierarchical_batches(df)

for (paper, figure), batch_df in batches.items():
    # Analyze which parameters vary in this figure
    varied = detect_varied_parameters(batch_df)
    print(f"{paper} Fig {figure}: Varied params = {varied}")
```

---

## Configuration & Customization

### Modify Correlations

Edit [config.py](config.py.md) to add or change baseline correlation formulas:

```python
CORRELATIONS = {
    'Dittus-Boelert': {
        'variable': 'Nu',
        'formula': lambda re, pr: 0.023 * (re ** 0.8) * (pr ** 0.4),
    },
    # Add custom correlations here
}
```

### Customize Schema

Define output columns in `config.STITCHING_MASTER_SCHEMA`:

```python
STITCHING_MASTER_SCHEMA = [
    'Paper Title', 'Figure Number', 'Point ID',
    'Variable', 'Value',
    'Reynolds number (Re)', 'Geometry', 'P/e', 'e/D', 'Alpha',
    'Aspect ratio', 'Number of ribbed walls'
]
```

---

## Detailed Documentation

For detailed technical information about each component, see:

- [**config.py** Documentation](config.py.md) — Configuration settings and allowed values
- [**data_loader.py** Documentation](data_loader.py.md) — Data loading and batching functions
- [**geometric_engine.py** Documentation](geometric_engine.py.md) — Geometric parameter derivation
- [**baseline_engine.py** Documentation](baseline_engine.py.md) — Correlation calculations and normalization
- [**stitching_engine.py** Documentation](stitching_engine.py.md) — Output schema and file separation
- [**preprocessor.py** Documentation](preprocessor.py.md) — Pipeline orchestration
- [**test_data_generator.py** Documentation](test_data_generator.py.md) — Test data creation

---

## Error Handling & Debugging

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Missing manifest.json | Paper directory incomplete | Add manifest.json to paper directory |
| NaN in geometric params | Data not derived atomically | Check manifest constants are present |
| Unknown baseline method | Variable name doesn't match patterns | Use "Uncover" logic or specify explicitly |
| Schema mismatch | Output columns don't match expected schema | Check STITCHING_MASTER_SCHEMA config |

### Enable Verbose Logging

```python
preprocessor = MetaAnalysisPreprocessor(
    staging_dir=Path('Staging'),
    verbose=True  # Enable detailed logging
)
```

This generates detailed logs in `preprocessing_logs/` for each paper processed.

---

## Integration Points

### With Other Modules

- **Verification Tools** (`tools/verification_tool/`) — Validate processed data
- **Visualization Tools** (`tools/visualiser_tool/`) — Plot processed datasets

### Data Flow

```
Raw Data (Excel, CSV)
    ↓
ribs_core.data_loader
    ↓
ribs_core.geometric_engine
    ↓
ribs_core.baseline_engine
    ↓
ribs_core.stitching_engine
    ↓
clean_data_master.csv + processing logs
    ↓
verification_tool / visualiser_tool
```

---

## Summary

The ribs_core module provides:
✅ Automated parameter derivation with safety checks
✅ Normalized baseline calculations with decision tracking
✅ Consistent output schema across all papers
✅ Complete processing lineage documentation
✅ Quality assurance and error detection

Start with the [Quick Start](#quick-start) section, then explore individual component documentation as needed.
