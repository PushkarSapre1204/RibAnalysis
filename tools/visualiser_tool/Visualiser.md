# visualiser_gui.py — Exploratory Data Visualiser GUI Reference

## Overview

The **visualiser_gui.py** module provides the interactive Tkinter graphical user interface (GUI) for the Exploratory Data Visualiser tool. It allows users to explore research data from multiple papers seamlessly without manual plotting. 

The application is composed of four main panels managed by a central application orchestrator:
- **MultiPaperSelector**: Select and combine data from various papers.
- **AxisConfigPanel**: Choose plot types (2D/3D) and axis variables dynamically.
- **BinningConfigPanel**: Configure a 4th dimension of data visualization using automatic or manual binning rules.
- **PlotDisplayPanel**: Display and export matplotlib-generated charts.

**Key Responsibility**: Provide an intuitive, interactive environment to configure, generate, and save customizable publication-quality 2D and 3D plots from aggregated meta-analysis data.

---

## Plotting & Binning Helper Functions

### validate_bin_continuity(bins) → Tuple[bool, str]

Validates that a provided list of bin definitions is continuous, properly ordered, and non-overlapping.

**Signature:**
```python
def validate_bin_continuity(bins: List[Dict]) -> Tuple[bool, str]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `bins` | List[Dict] | A list of dictionaries containing 'lower', 'upper', and 'bin_number' keys |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| `is_valid` | bool | True if bins are properly contiguous |
| `error_message` | str | Empty string if valid, error details if invalid |

**Behavior:**
- ✓ Sorts bins by lower bound
- ✓ Checks that `lower < upper` for each bin
- ✓ Verifies that `current_upper == next_lower` to ensure contiguous intervals

---

### assign_points_to_bins(df, param_col, bins) → np.ndarray

Maps data points in a DataFrame to specific bin numbers based on a parameter's values.

**Signature:**
```python
def assign_points_to_bins(df: pd.DataFrame, param_col: str, bins: List[Dict]) -> np.ndarray:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `df` | pd.DataFrame | The data to assign |
| `param_col` | str | The column name containing the parameter to evaluate |
| `bins` | List[Dict] | Validated list of bin dictionaries |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| `bin_assignment` | np.ndarray | Integer array mapping each row in `df` to a `bin_number` |

**Behavior:**
- ✓ Skips `NaN` values (assigns -1)
- ✓ Uses inclusive bounding `lower <= value <= upper`
- ✓ Ensures safe positional indexing for filtered DataFrames

---

### get_bin_colors_symbols(n_bins) → Dict[int, Dict[str, str]]

Generates a distinct color and marker style dictionary mapping for a given number of bins.

**Signature:**
```python
def get_bin_colors_symbols(n_bins: int) -> Dict[int, Dict[str, str]]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `n_bins` | int | Total number of bins requiring unique styling |

**Returns:**
| Return | Type | Description |
|--------|------|-------------|
| `bin_styles` | Dict | Mapping of `bin_number` -> `{'color': hex_str, 'marker': str}` |

---

### get_bin_legend_label(parameter_name, bin_dict) → str

Constructs a human-readable legend label for a specific bin.

**Signature:**
```python
def get_bin_legend_label(parameter_name: str, bin_dict: Dict) -> str:
```

**Behavior:**
- ✓ Formats numbers cleanly via `_format_bin_value` helper
- ✓ Outputs `{parameter}: {val}` if lower/upper bound is identical (e.g., discrete parameters)
- ✓ Outputs `{parameter}: {lower} - {upper}` for continuous ranges

---

### Plot Generation Functions

These functions instantiate and return matplotlib `Figure` objects corresponding to the user's GUI configuration.

**Signatures:**
```python
def create_custom_2d_scatter(df, x_axis, y_axis, x_label=None, y_label=None, bins_config=None) -> Figure:
def create_custom_2d_line(df, x_axis, y_axis, x_label=None, y_label=None, bins_config=None) -> Figure:
def create_custom_3d_scatter(df, x_axis, y_axis, z_axis, x_label=None, y_label=None, z_label=None, bins_config=None) -> Figure:
def create_custom_3d_surface(df, x_axis, y_axis, z_axis, x_label=None, y_label=None, z_label=None, bins_config=None) -> Figure:
```

**Common Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `df` | pd.DataFrame | Dataframe filtered for the active papers |
| `x_axis`, `y_axis`, `z_axis` | str | Data column names for coordinates |
| `x_label`, `y_label`, `z_label` | str | Optional display-friendly labels |
| `bins_config` | Dict | Optional bin configuration mapping to group data visually |

**Behavior Specifics:**
- **2D Line**: Automatically sorts points by the `x_axis` before connecting lines to prevent scribbling.
- **3D Surface**: Generates an interpolated grid mesh via `scipy.interpolate.griddata`. If bins are active, renders distinct semi-transparent surfaces per bin group.

---

## GUI Classes

### MultiPaperSelector

Panel responsible for selecting, adding, and removing research papers from the data pool.

**Signature:**
```python
class MultiPaperSelector(ttk.Frame):
    def __init__(self, parent, on_selection_change=None):
```

**Key Methods:**

#### `set_available_papers(papers: List[str])`
Populates the available papers dropdown menu.

#### `get_selected_papers() → List[str]`
Returns the currently active papers selected by the user.

---

### AxisConfigPanel

Panel managing the dimensionality (2D/3D), plot styling (Scatter/Line/Surface), and axis assignment.

**Signature:**
```python
class AxisConfigPanel(ttk.Frame):
    def __init__(self, parent, on_config_change=None):
```

**Key Methods:**

#### `set_available_columns(columns: List[str])`
Updates the dropdown lists for X, Y, and Z axes. Automatically defaults Z to disabled until 3D mode is toggled.

#### `get_config() → Dict[str, str]`
Retrieves the current configurations for the plot.
**Returns:** Dictionary with keys: `plot_type`, `plot_mode`, `x_axis`, `y_axis`, `z_axis`.

---

### BinningConfigPanel

Panel coordinating the creation of data bins, which adds a visual 4th dimension (color/marker).

**Signature:**
```python
class BinningConfigPanel(ttk.Frame):
    def __init__(self, parent, on_bins_set=None):
```

**Key Methods:**

#### `set_available_parameters(parameters: List[str])`
Defines which parameters the user can bin across.

#### `get_bins_config() → Dict | None`
Extracts the validated binning configuration.
**Returns:** Returns `None` if binning is disabled, else returns a dictionary containing `enabled`, `parameter`, `mode`, and the specific `bins`.

**Internal Operations:**
- `_create_automatic_bins`: Automatically calculates distinct values for a selected parameter and maps each unique value to a bin.
- `_create_manual_bins`: Validates dynamically added manual UI entries and registers the user-defined boundaries.

---

### PlotDisplayPanel

A Tkinter canvas wrapper that handles Matplotlib figure rendering and exporting.

**Signature:**
```python
class PlotDisplayPanel(ttk.Frame):
    def __init__(self, parent):
```

**Key Methods:**

#### `display_plot(fig: Figure)`
Clears the old canvas and mounts the newly generated Matplotlib figure using `FigureCanvasTkAgg`.

#### `clear_plot()`
Destroys the current canvas to reclaim memory and clear the visual space.

#### `_on_save_click()`
Triggers the standard OS file dialogue, allowing the user to export the plot to disk (defaulting to publication-ready 300 DPI `.png`).

#### Point click inspection
When a user clicks a plotted point, the panel shows a right-side details frame with the clicked row data and coordinates.

- The details frame stays hidden until the first successful point click.
- If multiple points overlap the click target, the panel lists them and updates the details view when one is selected.
- Empty-space clicks clear and hide the details panel.
- The current implementation keeps points clickable across 2D scatter, 2D line, 3D scatter, and the raw point overlay used in 3D surface plots.

---

### VisualisierApp

The main application window orchestrator. Ties the panels together and handles data filtration before plotting.

**Signature:**
```python
class VisualisierApp(tk.Tk):
    def __init__(self):
```

**Key Methods:**

#### `_find_data_file() → None`
Searches upward through parent directories to locate the output of the preprocessing module (`Staging/clean_data_master.csv`). 

#### `_load_initial_data() → None`
Loads the found dataset via `ribs_core.data_loader`, identifies all unique paper titles, parses variables vs. output symbols, and primes the GUI dropdowns.

#### `_generate_plot() → None`
**Behavior:**
- ✓ Gathers configurations from `AxisConfigPanel` and `BinningConfigPanel`.
- ✓ Isolates data based on the `MultiPaperSelector`.
- ✓ Identifies whether the selected axes are raw parameters vs. extracted variables (symbols).
- ✓ Filters and reshapes the dataset logically if variables/symbols are chosen (e.g., extracting "Nu" values from the generic "Value" column).
- ✓ Purges any `NaN` coordinate values dynamically based on selected dimensions.
- ✓ Submits data to the corresponding `create_custom_...` plot generation function.
- ✓ Dispatches the generated figure to `PlotDisplayPanel`.

#### `main()`
Entry point wrapping the application initialization and execution of the Tkinter event loop.