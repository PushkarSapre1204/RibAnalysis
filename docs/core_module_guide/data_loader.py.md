# data_loader.py — Data Loading & Batching Reference

## Overview

The **data_loader.py** module handles loading experimental data from Excel/CSV files and organizing it into hierarchical batches for processing. It provides utilities for data loading, validation, and hierarchical grouping.

**Key Responsibility**: Load research data and organize it into logical groupings for analysis.

---

## Core Functions

### load_research_data(file_path: str) → pd.DataFrame

Loads Excel file and performs initial preprocessing.

**Signature:**
```python
def load_research_data(file_path: str) -> pd.DataFrame:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path` | str | Path to Excel file with research data |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| DataFrame | pd.DataFrame | Cleaned and preprocessed data |

**Behavior:**
- ✓ Reads Excel file
- ✓ Converts 'N/A' strings to NaN for consistent handling
- ✓ Converts numeric parameter columns to float types
- ✓ Coerces non-numeric values to NaN (e.g., text in numeric columns)
- ✓ Prints loading summary with row/column counts

**Columns Converted to Numeric:**
- Reynolds number (Re)
- P/e
- e/D
- Alpha
- Aspect ratio
- Number of ribbed walls
- Value (output variable)

**Example:**
```python
from ribs_core.data_loader import load_research_data

df = load_research_data('my_research_data.xlsx')
print(f"Loaded {df.shape[0]} rows and {df.shape[1]} columns")
```

**Output Example:**
```
Loaded data: 150 rows, 15 columns
Columns: ['Paper Title', 'Figure Number', 'Point ID', 'Variable', 'Value', ...]
```

---

### create_hierarchical_batches(df: pd.DataFrame) → Dict[Tuple[str, int], pd.DataFrame]

Groups data hierarchically by Paper Title and Figure Number.

**Signature:**
```python
def create_hierarchical_batches(df: pd.DataFrame) -> Dict[Tuple[str, int], pd.DataFrame]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `df` | pd.DataFrame | Input DataFrame from load_research_data() |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| batches | Dict[Tuple[str, int], pd.DataFrame] | Dictionary mapping (paper_title, figure_number) to filtered DataFrames |

**Behavior:**
- ✓ Groups data by (Paper Title, Figure Number)
- ✓ Creates independent DataFrame for each batch
- ✓ Prints summary of all batches created
- ✓ Resets index in each batch to start from 0

**Why Hierarchical?**
Data is organized in 2-level hierarchy:
1. **Level 1 (Paper)**: All data from one research paper
2. **Level 2 (Figure)**: One figure/plot from that paper

This structure allows per-figure analysis and per-paper processing.

**Example:**
```python
from ribs_core.data_loader import load_research_data, create_hierarchical_batches

df = load_research_data('data.xlsx')
batches = create_hierarchical_batches(df)

# Access a specific batch
paper_title = "Heat Transfer in Ribbed Channels"
figure_num = 1
batch = batches[(paper_title, figure_num)]
print(f"Batch size: {len(batch)} rows")
```

**Output Example:**
```
Created 12 figure batches
  Heat Transfer in Ribbed Channels... Fig 1: 25 points
  Heat Transfer in Ribbed Channels... Fig 2: 28 points
  Friction Factor Study... Fig 1: 15 points
  ...
```

---

### get_variables_in_batch(batch_df: pd.DataFrame) → List[str]

Extracts unique output variables from a batch.

**Signature:**
```python
def get_variables_in_batch(batch_df: pd.DataFrame) -> List[str]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `batch_df` | pd.DataFrame | DataFrame for a specific paper-figure combination |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| variables | List[str] | Sorted list of unique variable names (e.g., ['Nu', 'f', 'St']) |

**Behavior:**
- ✓ Extracts unique values from 'Variable' column
- ✓ Returns sorted list for consistent ordering
- ✓ Only includes variables present in this specific batch

**Example:**
```python
# Get all variables in Figure 1
batch = batches[("Paper Title", 1)]
vars_in_batch = get_variables_in_batch(batch)
print(f"Variables in this figure: {vars_in_batch}")  # ['Nu', 'Nu/Nu0']
```

**Output Example:**
```
['Nu', 'Nu/Nu0', 'St']
```

---

### get_available_symbols(df: pd.DataFrame, papers: List[str]) → List[str]

Gets output variable symbols that are available in ALL selected papers.

**Signature:**
```python
def get_available_symbols(df: pd.DataFrame, papers: List[str]) -> List[str]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `df` | pd.DataFrame | Full input DataFrame |
| `papers` | List[str] | List of paper titles to check |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| symbols | List[str] | Sorted list of symbols present in ALL selected papers |

**Behavior:**
- ✓ Finds unique variables in each selected paper
- ✓ Returns only the intersection (variables in ALL papers)
- ✓ Returns sorted list for consistency
- ✓ Returns empty list if no common variables exist

**Purpose:**
Used to identify comparable datasets across multiple research papers.

**Example:**
```python
# Which variables are measured in ALL 3 papers?
common_vars = get_available_symbols(df, papers=[
    "Heat Transfer Study 2020",
    "Ribbed Channel Analysis",
    "Friction Factor Comparison"
])
print(f"Common variables: {common_vars}")  # Might be ['Nu', 'f']
```

**Output Example:**
```
['Nu', 'f']  # Only these are in all 3 papers
```

---

## Data Flow

```
Excel File
    ↓
load_research_data()
    ├─ Read Excel
    ├─ Convert 'N/A' → NaN
    ├─ Convert to numeric types
    └─ Return cleaned DataFrame
    ↓
create_hierarchical_batches()
    ├─ Group by (Paper Title, Figure Number)
    ├─ Create separate DataFrame per batch
    └─ Return Dict[Tuple, DataFrame]
    ↓
Per-Batch Processing
    ├─ get_variables_in_batch() — Find variables in this batch
    ├─ get_available_symbols() — Find common variables across papers
    └─ Process each batch independently
```

---

## Integration Points

### Used By

| Module | Purpose |
|--------|---------|
| **preprocessor.py** | Loads data and creates batches for pipeline |
| **geometric_engine.py** | Receives batch DataFrames for geometric processing |
| **Test workflows** | Loads test data from Excel for validation |

### Input Format

**Required Excel Columns:**
- Paper Title (text)
- Figure Number (integer)
- Point ID (text)
- Variable (text) — e.g., 'Nu', 'f', 'St', 'Nu/Nu0'
- Value (numeric)
- Reynolds number (Re) (numeric or N/A)
- Geometry (text or N/A)
- P/e (numeric or N/A)
- e/D (numeric or N/A)
- Alpha (numeric or N/A)
- Aspect ratio (numeric or N/A)
- Number of ribbed walls (integer or N/A)
- Reading on (text or N/A)
- Constant factor (numeric or N/A)
- Dittus-Boelter Value (numeric or N/A)

### Output Format

**For Each Batch:**
```
(Paper Title str, Figure Number int) → DataFrame
  ├─ Columns: All 15 input columns
  ├─ Values: Cleaned and converted to numeric types
  ├─ NaN: All N/A values converted
  └─ Index: Reset to 0, 1, 2, ...
```

---

## Error Handling

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| FileNotFoundError | Excel file not found | Check file path is correct |
| KeyError on column | Column name doesn't match | Verify exact column names in Excel |
| ValueError in numeric conversion | Non-numeric data in numeric column | Data will be converted to NaN |
| Empty batches | No data for some paper-figure combination | Check data filtering criteria |

### Example: Handling Missing Files

```python
from pathlib import Path

file_path = 'data.xlsx'

if not Path(file_path).exists():
    print(f"Error: {file_path} not found")
else:
    df = load_research_data(file_path)
```

---

## Examples

### Example 1: Load and Batch Data

```python
from ribs_core.data_loader import load_research_data, create_hierarchical_batches

# Load data
df = load_research_data('experiments.xlsx')
print(f"Total rows: {df.shape[0]}")

# Create batches
batches = create_hierarchical_batches(df)
print(f"Total batches: {len(batches)}")

# Process each batch
for (paper, figure), batch in batches.items():
    print(f"{paper} - Figure {figure}: {len(batch)} points")
```

### Example 2: Find Variables in Specific Batch

```python
# Get the first batch
first_key = list(batches.keys())[0]
first_batch = batches[first_key]

# Find variables in this batch
variables = get_variables_in_batch(first_batch)
print(f"Variables measured: {variables}")
```

### Example 3: Find Common Variables Across Papers

```python
# Get all unique paper titles
papers = df['Paper Title'].unique().tolist()

# Find variables common to all papers
common = get_available_symbols(df, papers)
print(f"Variables in all {len(papers)} papers: {common}")

# This tells us which variables can be compared meta-analytically
```

---

## Performance Characteristics

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| load_research_data() | O(n) | n = number of rows |
| create_hierarchical_batches() | O(n) | Single pass groupby |
| get_variables_in_batch() | O(m) | m = rows in batch |
| get_available_symbols() | O(p·v) | p = papers, v = variables per paper |

For typical datasets (100-1000 rows, 10-50 papers), all operations complete in < 1 second.

---

## Related Documentation

- [INDEX.md](INDEX.md) — Overview and architecture
- [preprocessor.py.md](preprocessor.py.md) — Uses these functions for pipeline orchestration
- [geometric_engine.py.md](geometric_engine.py.md) — Processes data after batching
- [config.py.md](config.py.md) — Configuration for column definitions
