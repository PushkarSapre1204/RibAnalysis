
# QUICK START GUIDE

## 30-Second Setup

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Prepare Your Data
Create an Excel file with these **15 columns**:

**Required (5):** Paper Title, Figure Number, Point ID, Variable, Value

**Parameters (7):** Reynolds number (Re), Geometry, P/e, e/D, Alpha, Aspect ratio, Number of ribbed walls

**Test Conditions (2):** Reading on, Constant factor

**Additional (1):** Dittus-Boelert Value

Use `N/A` for missing parameter values.

### Step 3: Run the Script
```bash
python -c "from Verification import process_research_data; process_research_data('your_data.xlsx')"
```

**Output**: PNG files in `./plots/` directory

---

## Example: Step-by-Step

### Create Sample Data
```python
from example_usage import create_sample_data
create_sample_data('my_data.xlsx')
```

### Visualize
```python
from research_data_visualizer import process_research_data
process_research_data('my_data.xlsx', 'output_plots')
```

### Check Results
Look in `output_plots/` for PNG files!

---

## Common Tasks

### Change Output Folder
```python
process_research_data('data.xlsx', output_directory='my_plots')
```

### Add Custom Parameters
Edit `research_data_visualizer.py` to change column categorization:

```python
# Only these 7 are analyzed for axes
PARAMETER_COLUMNS = [
    'Reynolds number (Re)',
    'Geometry',
    'P/e',
    'e/D',
    'Alpha',
    'Aspect ratio',
    'Number of ribbed walls'
]

# These 2 appear in titles only
TEST_CONDITION_COLUMNS = [
    'Reading on',
    'Constant factor'
]
```

### Change Plot Style
Edit `research_data_visualizer.py`:
```python
COLORS = sns.color_palette("Set2")      # Try different color palettes
MARKERS = ['o', 's', '^', ...]  # Add/remove marker styles
```

### Process Multiple Files
```python
from pathlib import Path
import research_data_visualizer as viz

for excel_file in Path('data').glob('*.xlsx'):
    viz.process_research_data(str(excel_file))
```

---

## Troubleshooting

**Q: Script says "No module named pandas"**  
A: Run `pip install -r requirements.txt`

**Q: Excel file not found**  
A: Check file path is correct and file exists

**Q: Plots look strange**  
A: Make sure Value column is numeric (not text)

**Q: Only one color in plot**  
A: Increase the number of legend categories (more variable parameters)

---

## Full Example: Custom Excel Data

### Your Excel File (`experiments.xlsx`):
```
Paper Title              | Fig | Variable | Value  | Re    | P/e | e/D
Heat Transfer Study     | 1   | Nu       | 12.5   | 1000  | 10  | 0.1
Heat Transfer Study     | 1   | Nu       | 15.2   | 5000  | 10  | 0.1
Heat Transfer Study     | 1   | Nu       | 18.7   | 10000 | 10  | 0.1
```

### Python Code:
```python
from research_data_visualizer import process_research_data

# Run once - generates all plots automatically
process_research_data('experiments.xlsx', 'results')
```

### Output:
```
results/
├── Heat_Transfer_Study_Fig1.png
└── [More figures...]
```

---

## Python API Reference

### Basic Usage
```python
from research_data_visualizer import process_research_data

process_research_data(
    excel_file_path='master_data.xlsx',
    output_directory='./plots'
)
```

### Advanced: Manual Analysis
```python
from research_data_visualizer import (
    load_research_data,
    create_hierarchical_batches,
    analyze_parameter_variability,
    select_axes
)

# Load data
df = load_research_data('data.xlsx')

# Create batches
batches = create_hierarchical_batches(df)

# Analyze specific batch
paper, fig_num = list(batches.keys())[0]
batch_data = batches[(paper, fig_num)]

# Analyze variability
var_data = batch_data[batch_data['Variable'] == 'Nu']
analysis = analyze_parameter_variability(var_data, ['Re', 'P/e'])

# Select best axes
x_axis, legend_axis, constants = select_axes(analysis, var_data)
print(f"X-axis: {x_axis}")
print(f"Legend: {legend_axis}")
print(f"Constants: {constants}")
```

---

## Features at a Glance

✅ **Automatic Batching** - Groups by paper and figure  
✅ **Smart Axis Selection** - Based on data variability  
✅ **Log-Log Scaling** - Auto-detected for data range  
✅ **Publication Quality** - 300 DPI PNG output  
✅ **Missing Data Handling** - Graceful N/A value treatment  
✅ **Multi-Variable Subplots** - Stacked for complex figures  
✅ **Unique Styling** - Colors and markers per series  

---

## Next Steps

1. **Prepare your Excel file** with the required columns
2. **Run the script** with your data
3. **Check the output** in the plots directory
4. **Customize if needed** using `config.py`

Enjoy! 🎉

---

For detailed documentation, see `README.md`
