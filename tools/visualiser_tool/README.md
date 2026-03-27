# Exploratory Data Visualiser Tool

## Overview

The Exploratory Data Visualiser is an interactive Tkinter GUI for exploring rib analysis research data across multiple papers. It provides custom axis selection, multiple plot types (2D/3D), and binning visualization capabilities.

## Features

✅ **Multi-Paper Data Handling**
- Select single or multiple papers
- Add/Remove individual papers or add all at once
- Merge data from selected papers

✅ **Custom Axis Selection**
- Choose any numeric column as X, Y, or Z axis
- Not limited to predefined parameters

✅ **Plot Modes**
- **2D**: Scatter or Line plots
- **3D**: Scatter or Surface plots

✅ **Binning Visualization**
- Enable/disable binning as 4th dimension
- Quantile-based or manual binning
- Color coding by bin for easy identification

✅ **Publication-Quality Output**
- Save plots as PNG (300 DPI), PDF, or other formats
- Professional figure styling

## Requirements

- Python 3.8+
- tkinter (typically included with Python)
- matplotlib
- pandas
- numpy
- scipy

All dependencies are included in the project's `requirements.txt`.

## Installation

1. Ensure the RibAnalysis project is set up with a virtual environment
2. Install dependencies:
   ```
   pip install -r ../../requirements.txt
   ```

3. Place your research data file in the `data/` directory as `Rib Data.xlsx`

## Usage

### Via Launcher Script (Windows)

```bash
double-click launch_gui.bat
```

### Via Python Command

```bash
python -m visualiser_tool.visualiser_gui
```

### Via Python Script

```python
from tools.visualiser_tool import VisualisierApp

app = VisualisierApp()
app.mainloop()
```

## Workflow

1. **Select Papers**
   - Use the "Paper Selection" panel on the left
   - Add papers one by one, or click "Add All" for all papers
   - Papers appear in the numbered list below

2. **Configure Plot**
   - Choose plot type: 2D or 3D
   - Select plot mode: Scatter, Line, or Surface
   - Select X, Y (and Z for 3D) axes from available numeric columns

3. **Optional: Configure Binning**
   - Check "Enable Binning"
   - Select which parameter to bin by
   - Choose binning method: Quantile or Manual
   - Specify number of bins (2-10)

4. **Generate Plot**
   - Click "Generate Plot" button
   - Plot appears in the right panel with legend

5. **Save Plot**
   - Click "Save Plot" to export as PNG (300 DPI), PDF, etc.
   - Choose file location and format

## Plot Types

### 2D Scatter
- Simple scatter plot of two variables
- Optional binning with color coding

### 2D Line
- Line plot connecting data points
- Sorted by X axis for sensible line ordering
- Optional binning with different colored lines

### 3D Scatter
- Three-dimensional scatter plot
- Rotate and zoom with mouse
- Optional binning with color coding

### 3D Surface
- Interpolated surface from scattered data
- Shows underlying surface + individual data points
- No binning for surface plots

## Binning

Binning adds a 4th dimension to your plots by grouping data into bins and using color or line style to differentiate them.

**Quantile Binning**: Automatically divides data into N equal-sized groups based on the selected parameter's distribution.

**Manual Binning** (future): Define custom bin ranges

## Troubleshooting

**"Could not find research data file"**
- Ensure `Rib Data.xlsx` exists in the `data/` directory
- File is expected at: `RibAnalysis/data/Rib Data.xlsx`

**"Failed to load data"**
- Check that the Excel file is not corrupted
- Ensure Excel file has a column named "Paper Title"
- Check file permissions

**Plot generation fails**
- Verify all selected axes exist in the data
- For 3D plots, ensure Z axis is selected
- Check that selected papers have data for chosen axes

**3D surface plot looks weird**
- Surface plots require scattered data across X-Y space
- If data is clustered, results may be poor
- Try 3D scatter plot instead

## Technical Details

### Architecture

The tool follows a modular design:

- **MultiPaperSelector**: Paper selection and management
- **AxisConfigPanel**: Plot configuration (type, mode, axes)
- **BinningPanel**: Binning configuration
- **PlotDisplayPanel**: Plot display and export
- **VisualisierApp**: Main application orchestrator

### Data Flow

```
Research Data (ribs_core.data_loader)
        ↓
    Filter by Papers
        ↓
    Apply Binning (if enabled)
        ↓
    Generate Plot (matplotlib)
        ↓
    Display on Canvas
```

### Reusing ribs_core

The visualiser imports core functionality from `ribs_core.data_loader`:
- Data loading and validation
- Column identification and analysis

This avoids code duplication and maintains consistency with other tools.

## Development

### Adding New Plot Types

Add new plot generation functions to `visualiser_gui.py`:

```python
def create_custom_heatmap(df, x_axis, y_axis, value_axis):
    fig = Figure(figsize=(8, 6), dpi=100)
    ax = fig.add_subplot(111)
    # ... implementation
    return fig
```

Then update `_generate_plot()` to handle the new type.

### Extending Binning

Modify `apply_custom_binning()` to support additional binning strategies:

```python
if method == 'custom_method':
    # ... custom implementation
    df_copy['Bin'] = ...
```

## License

Part of the RibAnalysis project.

## Contact

For issues or questions, refer to the main RibAnalysis documentation.
