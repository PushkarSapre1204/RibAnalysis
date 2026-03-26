
# Automated Research Data Visualization Tool

A Python script that reads experimental data from an Excel file and automatically generates publication-quality plots with parameter-agnostic axis selection based on data variability.

## Features

✅ **Hierarchical Batching**: Groups data by Paper Title and Figure Number  
✅ **Dynamic Axis Selection**: Identifies which parameters to plot based on data variability  
✅ **Automatic Log-Log Scaling**: Detects when log scaling is needed (>1 order of magnitude)  
✅ **N/A Value Handling**: Gracefully handles missing parameter values  
✅ **Multi-Variable Subplots**: Creates vertically stacked subplots for figures with multiple variables  
✅ **Publication-Quality Output**: Unique colors and markers per legend series, 300 DPI PNG  

## Installation

### 1. Clone or Download the Script

Ensure you have the main files:
- `research_data_visualizer.py` - Main visualization script
- `example_usage.py` - Example usage and test data generator

### 2. Install Required Dependencies

```bash
pip install pandas openpyxl matplotlib seaborn numpy
```

**Requirements:**
- Python 3.7+
- pandas >= 1.0
- matplotlib >= 3.0
- seaborn >= 0.11
- openpyxl (for Excel support)
- numpy >= 1.18

## Data Schema

Your Excel file must have these **15 columns** (in any order):

### Core Data Columns (5):
| Column | Type | Description |
|--------|------|-------------|
| Paper Title | Text | Name of the research paper |
| Figure Number | Integer | Figure number within the paper |
| Point ID | Text | Unique identifier for each data point (e.g., "P1", "P2") |
| Variable | Text | Name of dependent variable (e.g., "Nu", "f", "St") |
| Value | Float | Numerical measurement |

### Parameter Columns (7) - Used for Axis Selection:
| Column | Type | Description |
|--------|------|-------------|
| Reynolds number (Re) | Float or "N/A" | Reynolds number (flow parameter) |
| Geometry | Text or "N/A" | **RIB geometry type** (e.g., "Rectangular", "Trapezoidal") |
| P/e | Float or "N/A" | Pitch to rib height ratio |
| e/D | Float or "N/A" | Rib height to hydraulic diameter |
| Alpha | Float or "N/A" | Rib angle in degrees |
| Aspect ratio | Float or "N/A" | Channel aspect ratio (width/height) |
| Number of ribbed walls | Integer or "N/A" | Count of ribbed walls |

### Test Condition Columns (2) - Shown in Titles Only:
| Column | Type | Description |
|--------|------|-------------|
| Reading on | Text or "N/A" | Which wall measurement was taken (test parameter) |
| Constant factor | Float or "N/A" | Correction or scaling factor (test parameter) |

### Additional Data Columns (1) - Not Used in Analysis:
| Column | Type | Description |
|--------|------|-------------|
| Dittus-Boelter Value | Float or "N/A" | Reference correlation value (informational only) |

### Example Excel Data:

```
Paper Title | Figure # | Point ID | Variable | Value | Re    | Geometry      | P/e | e/D  | Alpha | Aspect | Walls | Reading on | Constant factor | Dittus-Boelter Value
Flow Study  | 1        | P1       | Nu       | 15.2  | 1000  | Rectangular   | 10  | 0.1  | 45    | 2      | 1     | Wall 1     | 1.0             | 12.5
Flow Study  | 1        | P2       | Nu       | 18.5  | 5000  | Rectangular   | 10  | 0.1  | 45    | 2      | 1     | Wall 1     | 1.0             | 15.2
...
```

Use **"N/A"** for any missing or non-applicable values.

## Usage

### Quick Start - Run Example

```bash
python example_usage.py
```

This will:
1. Generate sample research data (`master_research_data.xlsx`)
2. Create plots in the `./plots/` directory
3. Display a demonstration of the script's capabilities

### Use with Your Own Data

```python
from research_data_visualizer import process_research_data

# Process your Excel file
process_research_data('your_master_data.xlsx', output_directory='./output_plots')
```

### Command Line

```bash
python -c "from Verification import process_research_data; process_research_data('your_file.xlsx')"
```

## Algorithm: Dynamic Axis Selection

The script automatically determines plot axes based on parameter variability. **Only the 7 PARAMETER_COLUMNS are analyzed for axes; TEST_CONDITION_COLUMNS and ADDITIONAL_DATA_COLUMNS are handled separately.**

### Step 1: Hierarchical Batching
```
Data grouped by: Paper Title → Figure Number → Variable
```

### Step 2: Variability Analysis
For each variable in each figure, analyze only the **7 PARAMETER_COLUMNS**:
1. **Filter**: Ignore columns that are entirely "N/A"
2. **Identify Constants**: Parameters with only one unique value → displayed in title
3. **Identify Variables**: Parameters with 2+ unique values → candidates for axes

### Step 3: Extract Test Conditions
Extract values from **TEST_CONDITION_COLUMNS** ("Reading on", "Constant factor"):
- These are always shown in the subplot title
- These are NOT analyzed for variation
- These are NOT used as axes

### Step 4: Axis Assignment (from VARIABLES only)
- **X-Axis**: Parameter with the highest number of unique values
  - **Conflict Resolution**: If tied, Reynolds number (Re) gets priority
- **Legend (Hue)**: Parameter with second-highest number of unique values
- **Constants + Test Conditions**: All appear in subplot title

### Step 5: Scaling Detection
- **Log-X**: Applied if X-axis is "Reynolds number (Re)" OR data range > 1 order of magnitude
- **Log-Y**: Applied if Y-axis (Value) data range > 1 order of magnitude

### Step 6: Subplot Title Format
```
Variable | Parameter=value1, Parameter=value2, ..., Reading on=value, Constant factor=value
```

## Output

All figures are saved as PNG files with the naming convention:

```
[Paper_Title_Slug]_Fig[Figure_Number].png
```

Example outputs:
- `Flow_Dynamics_in_Ribbed_Channels_Fig1.png`
- `Heat_Transfer_Enhancement_Study_Fig2.png`
- `Pressure_Drop_Analysis_Fig3.png`

## Configuration

You can customize the script by editing these constants in `research_data_visualizer.py`:

```python
# Parameter columns to analyze for axis selection (7 columns)
PARAMETER_COLUMNS = [
    'Reynolds number (Re)',
    'Geometry',
    'P/e',
    'e/D',
    'Alpha',
    'Aspect ratio',
    'Number of ribbed walls'
]

# Test condition columns (shown in title, not used for axes) (2 columns)
TEST_CONDITION_COLUMNS = [
    'Reading on',
    'Constant factor'
]

# Additional data columns (not used in analysis) (1 column)
ADDITIONAL_DATA_COLUMNS = [
    'Dittus-Boelter Value'
]

# Marker styles and colors
MARKERS = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h', '+', 'x']
COLORS = sns.color_palette("husl", 12)
```

**Important Notes:**
- Only PARAMETER_COLUMNS are analyzed to determine X-axis and Legend
- TEST_CONDITION_COLUMNS values are always displayed in subplot titles
- ADDITIONAL_DATA_COLUMNS are completely ignored by the algorithm

## Example Output

### Input:
A figure with two variables (Nu and f), where:
- Re varies: 1000, 5000, 10000, 20000 (4 unique values)
- P/e is constant: 10
- Alpha varies: 30°, 45°, 60° (3 unique values)

### Output:
Two subplots:
1. **Subplot 1 - Nu**: X-axis = Re (log scale), Legend = Alpha
   - Title: "Nu | Conditions: P/e=10"
2. **Subplot 2 - f**: X-axis = Re (log scale), Legend = Alpha
   - Title: "f | Conditions: P/e=10"

## Handling Edge Cases

| Scenario | Behavior |
|----------|----------|
| Single data point per variable | Plots as single scatter point |
| All parameters are constant | Uses index as X-axis |
| Only one variable in figure | Creates single subplot (no legend) |
| Column entirely "N/A" | Column is completely ignored |
| Negative or zero values | Skipped in log-scale calculations |

## Troubleshooting

### Issue: "No valid data points"
**Solution**: Check for "N/A" values in X-axis or Value columns for that variable

### Issue: Incorrect log scaling
**Solution**: Verify that parameter values are numeric (not text) after "N/A" replacement

### Issue: Import errors
**Solution**: Run `pip install pandas openpyxl matplotlib seaborn numpy`

### Issue: Plot colors look wrong
**Solution**: Change `COLORS` palette in the configuration section (lines 33-34)

## Advanced Usage

### Custom Parameter List

### Adding Custom Parameters

To add new parameters for analysis, edit PARAMETER_COLUMNS:

```python
PARAMETER_COLUMNS = [
    'Reynolds number (Re)',
    'Geometry',
    'P/e',
    'e/D',
    'Alpha',
    'Aspect ratio',
    'Number of ribbed walls',
    'Custom_Parameter_1',  # Add your own (analyzed for axes)
    'Custom_Parameter_2',
]
```

To add new test condition columns (shown in titles only):

```python
TEST_CONDITION_COLUMNS = [
    'Reading on',
    'Constant factor',
    'Experimental_Setup',  # New test parameter
]
```

### Custom Styling

```python
# Use a different seaborn color palette
COLORS = sns.color_palette("Set2", 12)

# Add more marker styles
MARKERS = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h', '+', 'x', '.', ',']
```

### Batch Processing Multiple Files

```python
from pathlib import Path
import research_data_visualizer as viz

data_dir = Path('./data')
for excel_file in data_dir.glob('*.xlsx'):
    viz.process_research_data(str(excel_file), f'./plots/{excel_file.stem}')
```

## Function Reference

### Main Functions

#### `process_research_data(excel_file_path, output_directory=None)`
**Purpose**: Main entry point - loads data and generates all plots  
**Parameters**:
- `excel_file_path` (str): Path to Excel file
- `output_directory` (str): Output folder (default: './plots')

#### `load_research_data(file_path)`
**Purpose**: Load and preprocess Excel file  
**Returns**: Preprocessed DataFrame

#### `create_hierarchical_batches(df)`
**Purpose**: Group data by Paper Title and Figure Number  
**Returns**: Dictionary of batches

#### `analyze_parameter_variability(data_points, parameters)`
**Purpose**: Identify which parameters are constant vs. variable  
**Returns**: Dictionary with 'constants' and 'variables' keys

#### `select_axes(analysis, data_points)`
**Purpose**: Determine optimal X and Y axes based on variability  
**Returns**: Tuple of (x_axis_column, legend_column, constants_dict)

#### `check_need_log_scale(values)`
**Purpose**: Detect if data spans >1 order of magnitude  
**Returns**: Boolean

#### `create_figure_plot(batch_df, paper_title, fig_num, output_dir)`
**Purpose**: Generate and save a figure with subplots  
**Returns**: None (saves PNG file)

## License & Citation

This tool is provided as-is for research data visualization. If you use it in your publications, please acknowledge its use.

## Support

For issues or feature requests, please provide:
1. Sample of your Excel data structure
2. Error messages or unexpected output
3. Python version and OS information

---

**Version**: 1.0  
**Last Updated**: 2026-03-12  
**Author**: Data Visualization Tool
