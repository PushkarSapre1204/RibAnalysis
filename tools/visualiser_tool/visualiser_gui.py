"""
GUI Module for Exploratory Data Visualiser

Provides interactive Tkinter interface with 4 main panels:
- MultiPaperSelector: Select papers and merge data
- AxisConfigPanel: Configure plot axes and type
- BinningPanel: Configure binning parameters
- PlotDisplayPanel: Display and save plots
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import matplotlib.pyplot as plt
from matplotlib.backend_bases import MouseButton
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import json
import shutil

# Add parent directory to path for ribs_core imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ribs_core import data_loader
from ribs_core.config import MARKERS
from ribs_core.preprocessor import MetaAnalysisPreprocessor
from ribs_core.project_manager import (
    FigureSpec,
    ProjectState,
    build_project_paths,
    sanitize_project_name,
    load_project_file,
    save_project_file,
)

# Forward-declare ImportDialog name so static checks won't flag references
ImportDialog = None

# Define a set of distinct colors for binning visualization
COLORS = {
    'C0': '#1f77b4', 'C1': '#ff7f0e', 'C2': '#2ca02c', 'C3': '#d62728',
    'C4': '#9467bd', 'C5': '#8c564b', 'C6': '#e377c2', 'C7': '#7f7f7f',
    'C8': '#bcbd22', 'C9': '#17becf'
}

# ============================================================================
# HELPER FUNCTIONS FOR PLOTTING (placed here as per plan)
# ============================================================================

# ============================================================================
# BINNING HELPER FUNCTIONS
# ============================================================================

def validate_bin_continuity(bins):
    """Validate that bins are continuous, ordered, and non-overlapping."""
    if not bins:
        return False, "No bins defined"

    sorted_bins = sorted(bins, key=lambda x: x['lower'])

    for bin_dict in sorted_bins:
        if bin_dict['lower'] >= bin_dict['upper']:
            return False, f"Bin {bin_dict['bin_number']}: Lower bound must be less than upper bound"

    for i in range(len(sorted_bins) - 1):
        current_upper = sorted_bins[i]['upper']
        next_lower = sorted_bins[i + 1]['lower']
        if current_upper != next_lower:
            return False, f"Bins are not continuous: Bin {sorted_bins[i]['bin_number']} ends at {current_upper}, but Bin {sorted_bins[i + 1]['bin_number']} starts at {next_lower}"

    return True, ""


def assign_points_to_bins(df, param_col, bins):
    """Assign bin numbers to each row based on parameter value."""
    bin_assignment = np.zeros(len(df), dtype=int)

    # Use positional indexing to avoid out-of-bounds when df has non-consecutive index labels.
    for pos, (_, row) in enumerate(df.iterrows()):
        value = row[param_col]
        if pd.isna(value):
            bin_assignment[pos] = -1
            continue

        for bin_dict in bins:
            lower = bin_dict['lower']
            upper = bin_dict['upper']
            bin_num = bin_dict['bin_number']
            if lower <= value <= upper:
                bin_assignment[pos] = bin_num
                break

    return bin_assignment


def get_bin_colors_symbols(n_bins):
    """Return style mapping for each bin number using configured colors and markers."""
    colors_list = list(COLORS.values())
    markers_list = MARKERS.copy()

    bin_styles = {}
    for i in range(n_bins):
        bin_num = i + 1
        bin_styles[bin_num] = {
            'color': colors_list[i % len(colors_list)],
            'marker': markers_list[i % len(markers_list)]
        }

    return bin_styles


def _format_bin_value(value):
    """Format numeric values compactly for legend labels."""
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        if np.isclose(value, round(value)):
            return str(int(round(value)))
        return f"{value:g}"
    return str(value)


def get_bin_legend_label(parameter_name, bin_dict):
    """Build legend label with parameter and single value/range."""
    lower = bin_dict['lower']
    upper = bin_dict['upper']

    lower_text = _format_bin_value(lower)
    upper_text = _format_bin_value(upper)

    if np.isclose(lower, upper):
        return f"{parameter_name}: {lower_text}"
    return f"{parameter_name}: {lower_text} - {upper_text}"


DETAIL_FIELD_MAP = [
    ("Paper", "Paper Title"),
    ("Variable name", "Variable"),
    ("Value", "Value"),
    ("Reynolds number", "Reynolds number (Re)"),
    ("P/e", "P/e"),
    ("e/D", "e/D"),
    ("Alpha", "Alpha"),
    ("Aspect ratio", "Aspect ratio"),
]


def _display_value(value):
    """Return a raw display value while normalizing missing data."""
    if pd.isna(value):
        return "N/A"
    if isinstance(value, np.generic):
        return value.item()
    return value


def _display_value_3dp(value):
    """Return a value formatted to three decimal places when numeric."""
    if pd.isna(value):
        return "N/A"
    if isinstance(value, (int, float, np.integer, np.floating)):
        return f"{float(value):.3f}"
    return str(_display_value(value))


def _attach_point_metadata(fig, artist, df_subset, x_axis, y_axis, z_axis=None, x_label=None, y_label=None, z_label=None):
    """Attach row-level metadata to a plotted artist so clicks can be resolved back to data rows."""
    point_records = []

    for row_index, row in df_subset.iterrows():
        record = row.to_dict()
        record['_row_index'] = row_index
        record['_coordinates'] = {
            'x': _display_value(row[x_axis]),
            'y': _display_value(row[y_axis]),
        }
        if z_axis is not None:
            record['_coordinates']['z'] = _display_value(row[z_axis])
        point_records.append(record)

    artist._point_records = point_records
    artist._plot_axes = {
        'x_axis': x_axis,
        'y_axis': y_axis,
        'z_axis': z_axis,
        'x_label': x_label if x_label else x_axis,
        'y_label': y_label if y_label else y_axis,
        'z_label': z_label if z_label else z_axis,
    }
    artist.set_picker(5)

    if not hasattr(fig, '_clickable_artists'):
        fig._clickable_artists = []
    fig._clickable_artists.append(artist)

    return artist


def create_custom_2d_scatter(df, x_axis, y_axis, x_label=None, y_label=None, bins_config=None):
    """Create 2D scatter plot with optional binning."""
    fig = Figure(figsize=(8, 6), dpi=100)
    ax = fig.add_subplot(111)
    fig._clickable_artists = []
    
    # Use display labels if provided, otherwise use column names
    x_display = x_label if x_label else x_axis
    y_display = y_label if y_label else y_axis
    
    if bins_config and bins_config['enabled']:
        bin_assignment = assign_points_to_bins(df, bins_config['parameter'], bins_config['bins'])
        bin_styles = get_bin_colors_symbols(len(bins_config['bins']))

        for bin_dict in bins_config['bins']:
            bin_num = bin_dict['bin_number']
            mask = bin_assignment == bin_num
            if mask.any():
                style = bin_styles[bin_num]
                subset = df.iloc[np.flatnonzero(mask)].copy()
                scatter = ax.scatter(
                    subset[x_axis],
                    subset[y_axis],
                    label=get_bin_legend_label(bins_config['parameter'], bin_dict),
                    alpha=0.6,
                    color=style['color'],
                    marker=style['marker'],
                    s=70
                )
                _attach_point_metadata(fig, scatter, subset, x_axis, y_axis, None, x_label, y_label, None)

        ax.legend(loc='best', framealpha=0.9)
    else:
        scatter = ax.scatter(df[x_axis], df[y_axis], alpha=0.6)
        _attach_point_metadata(fig, scatter, df, x_axis, y_axis, None, x_label, y_label, None)
    
    ax.set_xlabel(x_display)
    ax.set_ylabel(y_display)
    ax.set_title(f'{x_display} vs {y_display}')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    
    return fig


def create_custom_2d_line(df, x_axis, y_axis, x_label=None, y_label=None, bins_config=None):
    """Create 2D line plot with optional binning."""
    fig = Figure(figsize=(8, 6), dpi=100)
    ax = fig.add_subplot(111)
    fig._clickable_artists = []
    
    # Use display labels if provided, otherwise use column names
    x_display = x_label if x_label else x_axis
    y_display = y_label if y_label else y_axis
    
    # Sort by x_axis for sensible line
    df_sorted = df.sort_values(x_axis)
    
    if bins_config and bins_config['enabled']:
        bin_assignment = assign_points_to_bins(df_sorted, bins_config['parameter'], bins_config['bins'])
        bin_styles = get_bin_colors_symbols(len(bins_config['bins']))

        for bin_dict in bins_config['bins']:
            bin_num = bin_dict['bin_number']
            mask = bin_assignment == bin_num
            if mask.any():
                style = bin_styles[bin_num]
                subset = df_sorted[mask].sort_values(x_axis)
                line = ax.plot(
                    subset[x_axis],
                    subset[y_axis],
                    label=get_bin_legend_label(bins_config['parameter'], bin_dict),
                    marker=style['marker'],
                    alpha=0.6,
                    color=style['color'],
                    linewidth=2
                )[0]
                line.set_pickradius(5)
                _attach_point_metadata(fig, line, subset, x_axis, y_axis, None, x_label, y_label, None)

        ax.legend(loc='best', framealpha=0.9)
    else:
        line = ax.plot(df_sorted[x_axis], df_sorted[y_axis], marker='o', alpha=0.6)[0]
        line.set_pickradius(5)
        _attach_point_metadata(fig, line, df_sorted, x_axis, y_axis, None, x_label, y_label, None)
    
    ax.set_xlabel(x_display)
    ax.set_ylabel(y_display)
    ax.set_title(f'{x_display} vs {y_display} (Line)')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    
    return fig


def create_custom_3d_scatter(df, x_axis, y_axis, z_axis, x_label=None, y_label=None, z_label=None, bins_config=None):
    """Create 3D scatter plot with optional binning."""
    from mpl_toolkits.mplot3d import Axes3D
    
    # Use display labels if provided, otherwise use column names
    x_display = x_label if x_label else x_axis
    y_display = y_label if y_label else y_axis
    z_display = z_label if z_label else z_axis
    
    fig = Figure(figsize=(10, 8), dpi=100)
    ax = fig.add_subplot(111, projection='3d')
    fig._clickable_artists = []
    
    if bins_config and bins_config['enabled']:
        bin_assignment = assign_points_to_bins(df, bins_config['parameter'], bins_config['bins'])
        bin_styles = get_bin_colors_symbols(len(bins_config['bins']))

        for bin_dict in bins_config['bins']:
            bin_num = bin_dict['bin_number']
            mask = bin_assignment == bin_num
            if mask.any():
                style = bin_styles[bin_num]
                subset = df.iloc[np.flatnonzero(mask)].copy()
                scatter = ax.scatter(
                    subset[x_axis],
                    subset[y_axis],
                    subset[z_axis],
                    label=get_bin_legend_label(bins_config['parameter'], bin_dict),
                    alpha=0.6,
                    color=style['color'],
                    marker=style['marker'],
                    s=70
                )
                _attach_point_metadata(fig, scatter, subset, x_axis, y_axis, z_axis, x_label, y_label, z_label)

        ax.legend(loc='best', framealpha=0.9)
    else:
        scatter = ax.scatter(df[x_axis], df[y_axis], df[z_axis], alpha=0.6)
        _attach_point_metadata(fig, scatter, df, x_axis, y_axis, z_axis, x_label, y_label, z_label)
    
    ax.set_xlabel(x_display)
    ax.set_ylabel(y_display)
    ax.set_zlabel(z_display)
    ax.set_title(f'3D Scatter: {x_display}, {y_display}, {z_display}')
    fig.tight_layout()
    
    return fig


def create_custom_3d_surface(df, x_axis, y_axis, z_axis, x_label=None, y_label=None, z_label=None, bins_config=None):
    """Create 3D surface plot using triangulation with optional binning."""
    from mpl_toolkits.mplot3d import Axes3D
    from scipy.interpolate import griddata
    from matplotlib.patches import Patch
    
    # Use display labels if provided, otherwise use column names
    x_display = x_label if x_label else x_axis
    y_display = y_label if y_label else y_axis
    z_display = z_label if z_label else z_axis
    
    fig = Figure(figsize=(10, 8), dpi=100)
    ax = fig.add_subplot(111, projection='3d')
    fig._clickable_artists = []
    
    if bins_config and bins_config['enabled']:
        bin_assignment = assign_points_to_bins(df, bins_config['parameter'], bins_config['bins'])
        bin_styles = get_bin_colors_symbols(len(bins_config['bins']))
        legend_handles = []

        for bin_dict in bins_config['bins']:
            bin_num = bin_dict['bin_number']
            mask = bin_assignment == bin_num
            if not mask.any():
                continue

            style = bin_styles[bin_num]
            subset = df.iloc[np.flatnonzero(mask)].copy()
            x = subset[x_axis].values
            y = subset[y_axis].values
            z = subset[z_axis].values

            # Surface per bin when there are enough unique coordinates; otherwise only points.
            if len(subset) >= 3 and np.unique(x).size > 1 and np.unique(y).size > 1:
                xi = np.linspace(x.min(), x.max(), 20)
                yi = np.linspace(y.min(), y.max(), 20)
                xi, yi = np.meshgrid(xi, yi)
                zi = griddata((x, y), z, (xi, yi), method='linear')

                if np.isnan(zi).all():
                    zi = griddata((x, y), z, (xi, yi), method='nearest')

                ax.plot_surface(
                    xi,
                    yi,
                    zi,
                    color=style['color'],
                    alpha=0.35,
                    linewidth=0,
                    antialiased=True
                )

            scatter = ax.scatter(x, y, z, color=style['color'], marker=style['marker'], s=35, alpha=0.55)
            _attach_point_metadata(fig, scatter, subset, x_axis, y_axis, z_axis, x_label, y_label, z_label)

            legend_handles.append(
                Patch(
                    facecolor=style['color'],
                    edgecolor=style['color'],
                    alpha=0.55,
                    label=get_bin_legend_label(bins_config['parameter'], bin_dict)
                )
            )

        if legend_handles:
            ax.legend(handles=legend_handles, loc='best', framealpha=0.9)
    else:
        # Create grid
        x = df[x_axis].values
        y = df[y_axis].values
        z = df[z_axis].values

        # Create regular grid
        xi = np.linspace(x.min(), x.max(), 20)
        yi = np.linspace(y.min(), y.max(), 20)
        xi, yi = np.meshgrid(xi, yi)

        # Interpolate z values
        zi = griddata((x, y), z, (xi, yi), method='linear')

        # Plot surface
        ax.plot_surface(xi, yi, zi, cmap='viridis', alpha=0.8)
        scatter = ax.scatter(x, y, z, color='red', s=35, alpha=0.5)
        _attach_point_metadata(fig, scatter, df, x_axis, y_axis, z_axis, x_label, y_label, z_label)
    
    ax.set_xlabel(x_display)
    ax.set_ylabel(y_display)
    ax.set_zlabel(z_display)
    ax.set_title(f'3D Surface: {x_display}, {y_display}, {z_display}')
    fig.tight_layout()
    
    return fig


# ============================================================================
# GUI PANELS
# ============================================================================

class MultiPaperSelector(ttk.Frame):
    """Panel for selecting and managing multiple papers."""
    
    def __init__(self, parent, on_selection_change=None):
        """
        Initialize paper selector.
        
        Args:
            parent: Parent widget
            on_selection_change: Callback when selection changes
        """
        super().__init__(parent)
        self.on_selection_change = on_selection_change
        self.selected_papers = []
        self.all_papers = []
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create GUI widgets for paper selection."""
        # Title
        title = ttk.Label(self, text="Paper Selection", font=("Arial", 10, "bold"))
        title.pack(pady=5)
        
        # Paper dropdown with search
        frame_dropdown = ttk.Frame(self)
        frame_dropdown.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(frame_dropdown, text="Available Papers:").pack(side=tk.LEFT)
        self.paper_var = tk.StringVar()
        self.paper_dropdown = ttk.Combobox(frame_dropdown, textvariable=self.paper_var, 
                                           state="readonly", width=40)
        self.paper_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.paper_dropdown.bind("<<ComboboxSelected>>", self._on_paper_selected)
        
        # Buttons frame
        frame_buttons = ttk.Frame(self)
        frame_buttons.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(frame_buttons, text="Add", 
                  command=self._add_paper).pack(side=tk.LEFT, padx=2)
        ttk.Button(frame_buttons, text="Add All", 
                  command=self._add_all_papers).pack(side=tk.LEFT, padx=2)
        ttk.Button(frame_buttons, text="Remove", 
                  command=self._remove_paper).pack(side=tk.LEFT, padx=2)
        ttk.Button(frame_buttons, text="Clear All", 
                  command=self._clear_all).pack(side=tk.LEFT, padx=2)
        
        # Selected papers listbox
        ttk.Label(self, text="Selected Papers:").pack(anchor=tk.W, padx=5, pady=(5, 0))
        
        frame_listbox = ttk.Frame(self)
        frame_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(frame_listbox)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.selected_listbox = tk.Listbox(frame_listbox, yscrollcommand=scrollbar.set, 
                                           height=6)
        self.selected_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.selected_listbox.yview)
    
    def set_available_papers(self, papers):
        """Set list of available papers."""
        self.all_papers = sorted(papers)
        self.paper_dropdown['values'] = self.all_papers
    
    def _on_paper_selected(self, event):
        """Handle paper selection from dropdown."""
        pass
    
    def _add_paper(self):
        """Add selected paper to list."""
        paper = self.paper_var.get()
        if paper and paper not in self.selected_papers:
            self.selected_papers.append(paper)
            self._update_listbox()
            if self.on_selection_change:
                self.on_selection_change()
    
    def _add_all_papers(self):
        """Add all papers to selection."""
        self.selected_papers = self.all_papers.copy()
        self._update_listbox()
        if self.on_selection_change:
            self.on_selection_change()
    
    def _remove_paper(self):
        """Remove selected paper from list."""
        selection = self.selected_listbox.curselection()
        if selection:
            idx = selection[0]
            self.selected_papers.pop(idx)
            self._update_listbox()
            if self.on_selection_change:
                self.on_selection_change()
    
    def _clear_all(self):
        """Clear all selected papers."""
        self.selected_papers = []
        self._update_listbox()
        if self.on_selection_change:
            self.on_selection_change()
    
    def _update_listbox(self):
        """Update the listbox display."""
        self.selected_listbox.delete(0, tk.END)
        for i, paper in enumerate(self.selected_papers, 1):
            self.selected_listbox.insert(tk.END, f"{i}. {paper}")
    
    def get_selected_papers(self):
        """Get list of selected papers."""
        return self.selected_papers.copy()


class AxisConfigPanel(ttk.Frame):
    """Panel for configuring plot axes and type."""
    
    def __init__(self, parent, on_config_change=None):
        """
        Initialize axis configuration panel.
        
        Args:
            parent: Parent widget
            on_config_change: Callback when configuration changes
        """
        super().__init__(parent)
        self.on_config_change = on_config_change
        self.available_columns = []
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create GUI widgets for axis configuration."""
        # Title
        title = ttk.Label(self, text="Plot Configuration", font=("Arial", 10, "bold"))
        title.pack(pady=5)
        
        # Plot type frame
        frame_type = ttk.LabelFrame(self, text="Plot Type", padding=5)
        frame_type.pack(fill=tk.X, padx=5, pady=5)
        
        self.plot_type_var = tk.StringVar(value="2d_scatter")
        ttk.Radiobutton(frame_type, text="2D", variable=self.plot_type_var, 
                       value="2d", command=self._on_plot_type_change).pack(anchor=tk.W)
        ttk.Radiobutton(frame_type, text="3D", variable=self.plot_type_var, 
                       value="3d", command=self._on_plot_type_change).pack(anchor=tk.W)
        
        # Plot mode frame
        frame_mode = ttk.LabelFrame(self, text="Plot Mode", padding=5)
        frame_mode.pack(fill=tk.X, padx=5, pady=5)
        
        self.plot_mode_var = tk.StringVar(value="scatter")
        self.mode_buttons = {}
        
        self.mode_buttons['scatter'] = ttk.Radiobutton(frame_mode, text="Scatter", 
                                                        variable=self.plot_mode_var, 
                                                        value="scatter")
        self.mode_buttons['scatter'].pack(anchor=tk.W)
        
        self.mode_buttons['line'] = ttk.Radiobutton(frame_mode, text="Line", 
                                                     variable=self.plot_mode_var, 
                                                     value="line")
        self.mode_buttons['line'].pack(anchor=tk.W)
        
        self.mode_buttons['surface'] = ttk.Radiobutton(frame_mode, text="Surface", 
                                                        variable=self.plot_mode_var, 
                                                        value="surface", state=tk.DISABLED)
        self.mode_buttons['surface'].pack(anchor=tk.W)
        
        # Axis selection frame
        frame_axes = ttk.LabelFrame(self, text="Axes Selection", padding=5)
        frame_axes.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # X axis
        ttk.Label(frame_axes, text="X Axis:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.x_axis_var = tk.StringVar()
        self.x_axis_dropdown = ttk.Combobox(frame_axes, textvariable=self.x_axis_var, 
                                            state="readonly", width=20)
        self.x_axis_dropdown.grid(row=0, column=1, sticky=tk.EW, padx=5)
        
        # Y axis
        ttk.Label(frame_axes, text="Y Axis:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.y_axis_var = tk.StringVar()
        self.y_axis_dropdown = ttk.Combobox(frame_axes, textvariable=self.y_axis_var, 
                                            state="readonly", width=20)
        self.y_axis_dropdown.grid(row=1, column=1, sticky=tk.EW, padx=5)
        
        # Z axis (3D only)
        ttk.Label(frame_axes, text="Z Axis:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self.z_axis_var = tk.StringVar()
        self.z_axis_dropdown = ttk.Combobox(frame_axes, textvariable=self.z_axis_var, 
                                            state="readonly", width=20)
        self.z_axis_dropdown.grid(row=2, column=1, sticky=tk.EW, padx=5)
        self.z_axis_dropdown.config(state=tk.DISABLED)
        
        frame_axes.columnconfigure(1, weight=1)
    
    def _on_plot_type_change(self):
        """Handle plot type change (2D vs 3D)."""
        is_3d = self.plot_type_var.get() == "3d"
        
        # Enable/disable Z axis
        self.z_axis_dropdown.config(state=tk.NORMAL if is_3d else tk.DISABLED)
        
        # Update mode buttons
        self.mode_buttons['line'].config(state=tk.NORMAL if not is_3d else tk.DISABLED)
        self.mode_buttons['surface'].config(state=tk.NORMAL if is_3d else tk.DISABLED)
        
        # Reset mode if needed
        if is_3d and self.plot_mode_var.get() == "line":
            self.plot_mode_var.set("scatter")
        elif not is_3d and self.plot_mode_var.get() == "surface":
            self.plot_mode_var.set("scatter")
        
        if self.on_config_change:
            self.on_config_change()
    
    def set_available_columns(self, columns):
        """Set list of available columns for axes."""
        self.available_columns = sorted(columns)
        self.x_axis_dropdown['values'] = self.available_columns
        self.y_axis_dropdown['values'] = self.available_columns
        self.z_axis_dropdown['values'] = self.available_columns
        
        # Set defaults
        if len(self.available_columns) > 0:
            self.x_axis_dropdown.current(0)
        if len(self.available_columns) > 1:
            self.y_axis_dropdown.current(1)
        if len(self.available_columns) > 2:
            self.z_axis_dropdown.current(2)
    
    def get_config(self):
        """Get current plot configuration."""
        return {
            'plot_type': self.plot_type_var.get(),
            'plot_mode': self.plot_mode_var.get(),
            'x_axis': self.x_axis_var.get(),
            'y_axis': self.y_axis_var.get(),
            'z_axis': self.z_axis_var.get(),
        }


class BinningConfigPanel(ttk.Frame):
    """Panel for configuring automatic/manual binning with validation."""
    
    def __init__(self, parent, on_bins_set=None):
        """
        Initialize binning panel.
        
        Args:
            parent: Parent widget
            on_binning_change: Callback when binning config changes
        """
        super().__init__(parent)
        self.on_bins_set = on_bins_set
        self.df = None
        self.current_bins = None  # Stores validated bins
        self.bin_frames = []  # Store bin input frames for manual mode
        self.bins_container = None  # Container for bin input rows
        self.selected_papers = []  # Track which papers are currently selected
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create GUI widgets for binning configuration."""
        # Main horizontal frame
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.X, padx=0, pady=0)
        
        # Enable binning checkbox
        self.binning_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(main_frame, text="Enable Binning", 
                       variable=self.binning_enabled_var,
                       command=self._on_binning_toggle).pack(side=tk.LEFT, padx=5, pady=2)
        
        # Separator
        ttk.Separator(main_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Parameter selection (horizontal)
        ttk.Label(main_frame, text="Parameter:").pack(side=tk.LEFT, padx=2)
        self.bin_param_var = tk.StringVar()
        self.bin_param_dropdown = ttk.Combobox(main_frame, 
                                               textvariable=self.bin_param_var,
                                               state="disabled", width=15)
        self.bin_param_dropdown.pack(side=tk.LEFT, padx=2)
        self.bin_param_dropdown.bind("<<ComboboxSelected>>", self._on_param_selected)
        
        # Separator
        ttk.Separator(main_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Binning mode selection (horizontal)
        ttk.Label(main_frame, text="Mode:").pack(side=tk.LEFT, padx=2)
        self.binning_mode_var = tk.StringVar(value="automatic")
        ttk.Radiobutton(main_frame, text="Auto", 
                       variable=self.binning_mode_var, value="automatic", 
                       state=tk.DISABLED, command=self._on_mode_changed).pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(main_frame, text="Manual", 
                       variable=self.binning_mode_var, value="manual", 
                       state=tk.DISABLED, command=self._on_mode_changed).pack(side=tk.LEFT, padx=2)
        
        # Separator
        ttk.Separator(main_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Set Bins button
        ttk.Button(main_frame, text="Set Bins", command=self._on_set_bins).pack(side=tk.LEFT, padx=2)
        
        # Separator
        ttk.Separator(main_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Validation message
        self.validation_label = ttk.Label(main_frame, text="", foreground="green")
        self.validation_label.pack(side=tk.LEFT, padx=2)
        
        # Container for mode-specific widgets (initially hidden, shown below main frame if needed)
        self.mode_frame = ttk.Frame(self)
        self.mode_frame.pack(fill=tk.X, padx=0, pady=0)
        
        # Automatic mode info frame
        self.auto_frame = ttk.Frame(self.mode_frame)
        
        # Manual mode frame (initially hidden)
        self.manual_frame = ttk.Frame(self.mode_frame)
        self.manual_canvas = tk.Canvas(self.manual_frame, bg='white', highlightthickness=0, height=80)
        self.manual_scrollbar = ttk.Scrollbar(self.manual_frame, orient='vertical', command=self.manual_canvas.yview)
        self.manual_scrollable_frame = ttk.Frame(self.manual_canvas)
        
        # Bind canvas resize to update scrollable frame width
        def _on_canvas_configure(event):
            # Update scroll region and make frame fill canvas width
            self.manual_canvas.configure(scrollregion=self.manual_canvas.bbox("all"))
            # Make scrollable_frame take full canvas width
            canvas_width = self.manual_canvas.winfo_width()
            if canvas_width > 1:
                self.manual_canvas.itemconfig(self.canvas_window, width=canvas_width)
        
        self.manual_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.manual_canvas.configure(scrollregion=self.manual_canvas.bbox("all"))
        )
        
        self.canvas_window = self.manual_canvas.create_window((0, 0), window=self.manual_scrollable_frame, anchor="nw")
        self.manual_canvas.bind("<Configure>", _on_canvas_configure)
        self.manual_canvas.configure(yscrollcommand=self.manual_scrollbar.set)
    
    def _on_binning_toggle(self):
        """Handle binning enable/disable toggle."""
        is_enabled = self.binning_enabled_var.get()
        new_state = tk.NORMAL if is_enabled else tk.DISABLED
        
        self.bin_param_dropdown.config(state="readonly" if is_enabled else tk.DISABLED)
        
        # Find and update radio buttons in main_frame
        for widget in self.winfo_children()[0].winfo_children():  # main_frame children
            if isinstance(widget, ttk.Radiobutton):
                widget.config(state=new_state)
    
    def _on_param_selected(self, event=None):
        """Handle parameter selection - show automatic mode info for now."""
        # Mode frame can show info if needed in the future
        self.validation_label.config(text="")
    
    def _on_mode_changed(self):
        """Handle mode change between automatic and manual."""
        mode = self.binning_mode_var.get()
        
        if mode == "automatic":
            # Hide manual frame and reset canvas completely
            if self.manual_frame.winfo_ismapped():
                self.manual_frame.pack_forget()
                self.manual_canvas.pack_forget()
                self.manual_scrollbar.pack_forget()
        else:  # manual
            self._create_manual_bin_inputs()
            self.manual_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.manual_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.manual_frame.pack(fill=tk.X, padx=0, pady=(2, 0))
        
        self.validation_label.config(text="")
    
    def _create_manual_bin_inputs(self):
        """Create input fields for manual bin definition."""
        # Clear previous inputs
        for widget in self.manual_scrollable_frame.winfo_children():
            widget.destroy()
        self.bin_frames = []
        
        # Configure scrollable frame to fill canvas
        self.manual_scrollable_frame.columnconfigure(0, weight=0)  # Buttons column - fixed width
        self.manual_scrollable_frame.columnconfigure(1, weight=1)  # Bins column - flexible
        self.manual_scrollable_frame.rowconfigure(0, weight=1)
        
        # Left column: buttons frame (stacked vertically)
        buttons_frame = ttk.Frame(self.manual_scrollable_frame)
        buttons_frame.grid(row=0, column=0, sticky='nw', padx=2, pady=3)
        
        ttk.Button(buttons_frame, text="\u002b Add", command=self._add_bin_input).pack(pady=2, fill=tk.X)
        ttk.Button(buttons_frame, text="\u2212 Remove", command=self._remove_bin_input).pack(pady=2, fill=tk.X)
        
        # Right column: bins container frame
        self.bins_container = ttk.Frame(self.manual_scrollable_frame)
        self.bins_container.grid(row=0, column=1, sticky='nsew', padx=2, pady=3)
        
        # Add 1 default bin
        self._add_bin_input()
        
        # Update canvas scroll region
        self.manual_scrollable_frame.update_idletasks()
        self.manual_canvas.configure(scrollregion=self.manual_canvas.bbox("all"))
    
    def _add_bin_input(self):
        """Add a new bin input row."""
        bin_number = len(self.bin_frames) + 1
        
        bin_frame = ttk.Frame(self.bins_container, relief=tk.SUNKEN, borderwidth=1)
        bin_frame.pack(fill=tk.X, padx=0, pady=2)
        
        ttk.Label(bin_frame, text=f"Bin {bin_number}:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(bin_frame, text="Lower:").pack(side=tk.LEFT, padx=2)
        lower_var = tk.StringVar()
        lower_entry = ttk.Entry(bin_frame, textvariable=lower_var, width=10)
        lower_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(bin_frame, text="Upper:").pack(side=tk.LEFT, padx=2)
        upper_var = tk.StringVar()
        upper_entry = ttk.Entry(bin_frame, textvariable=upper_var, width=10)
        upper_entry.pack(side=tk.LEFT, padx=2)
        
        self.bin_frames.append({
            'frame': bin_frame,
            'bin_number': bin_number,
            'lower_var': lower_var,
            'upper_var': upper_var
        })
        
        # Update canvas scroll region
        self.manual_scrollable_frame.update_idletasks()
        self.manual_canvas.configure(scrollregion=self.manual_canvas.bbox("all"))
    
    def _remove_bin_input(self):
        """Remove the last bin input row."""
        if len(self.bin_frames) > 1:  # Always keep at least 1 bin
            bin_data = self.bin_frames.pop()
            bin_data['frame'].destroy()
            
            # Renumber remaining bins
            for i, bin_data in enumerate(self.bin_frames):
                # Update label text
                for widget in bin_data['frame'].winfo_children():
                    if isinstance(widget, ttk.Label) and "Bin" in str(widget.cget("text")):
                        widget.config(text=f"Bin {i+1}:")
                        bin_data['bin_number'] = i + 1
                        break
            
            # Update canvas scroll region
            self.manual_scrollable_frame.update_idletasks()
            self.manual_canvas.configure(scrollregion=self.manual_canvas.bbox("all"))
    
    def _on_set_bins(self):
        """Validate and set bins."""
        if not self.binning_enabled_var.get():
            return
        
        param = self.bin_param_var.get()
        if not param:
            self.validation_label.config(text="Error: Please select a parameter", foreground="red")
            return
        
        mode = self.binning_mode_var.get()
        
        if mode == "automatic":
            self._create_automatic_bins(param)
        else:  # manual
            self._create_manual_bins()
    
    def _create_automatic_bins(self, param):
        """Create automatic bins from unique values in selected papers."""
        # Validate that papers are selected
        if not self.selected_papers:
            self.validation_label.config(text="Error: Please select at least one paper", foreground="red")
            return
        
        if self.df is None or param not in self.df.columns:
            self.validation_label.config(text="Error: Parameter not found in data", foreground="red")
            return
        
        # Filter dataframe by selected papers
        df_filtered = self.df[self.df['Paper Title'].isin(self.selected_papers)]
        
        unique_values = sorted(df_filtered[param].dropna().unique().tolist())
        
        if len(unique_values) == 0:
            self.validation_label.config(text="Error: No valid values for parameter", foreground="red")
            return
        
        # Create bins: one per unique value
        bins = []
        for i, val in enumerate(unique_values):
            bins.append({
                'bin_number': i + 1,
                'lower': val,
                'upper': val,
                'label': f'Bin {i+1}: {val}'
            })
        
        self.current_bins = bins
        self.validation_label.config(text=f"✓ {len(bins)} bins created successfully", foreground="green")
        
        if self.on_bins_set:
            self.on_bins_set()
    
    def _create_manual_bins(self):
        """Create manual bins from user input."""
        bins = []
        
        try:
            for bin_data in self.bin_frames:
                lower_str = bin_data['lower_var'].get().strip()
                upper_str = bin_data['upper_var'].get().strip()
                
                if not lower_str or not upper_str:
                    continue  # Skip empty rows
                
                lower = float(lower_str)
                upper = float(upper_str)
                bin_num = bin_data['bin_number']
                
                bins.append({
                    'bin_number': bin_num,
                    'lower': lower,
                    'upper': upper,
                    'label': f'Bin {bin_num}'
                })
        
        except ValueError as e:
            self.validation_label.config(text=f"Error: Invalid numeric input - {str(e)}", foreground="red")
            return
        
        if not bins:
            self.validation_label.config(text="Error: No bins defined", foreground="red")
            return
        
        # Validate continuity
        is_valid, error_msg = validate_bin_continuity(bins)
        if not is_valid:
            self.validation_label.config(text=f"Error: {error_msg}", foreground="red")
            return
        
        self.current_bins = bins
        self.validation_label.config(text=f"✓ {len(bins)} bins set successfully", foreground="green")
        
        if self.on_bins_set:
            self.on_bins_set()
    
    def set_available_parameters(self, parameters):
        """Set available parameters for binning."""
        self.bin_param_dropdown['values'] = sorted(parameters)
        if len(parameters) > 0:
            self.bin_param_dropdown.current(0)
    
    def set_dataframe(self, df):
        """Set dataframe for automatic bin generation."""
        self.df = df
    
    def set_selected_papers(self, papers):
        """Set the currently selected papers for binning filtering."""
        self.selected_papers = papers.copy() if papers else []
    
    def get_bins_config(self):
        """Get current bins configuration."""
        if not self.binning_enabled_var.get() or self.current_bins is None:
            return None
        
        return {
            'enabled': True,
            'parameter': self.bin_param_var.get(),
            'mode': self.binning_mode_var.get(),
            'bins': self.current_bins
        }


class PlotDisplayPanel(ttk.Frame):
    """Panel for displaying plots (canvas only)."""
    
    def __init__(self, parent):
        """
        Initialize plot display panel.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.current_fig = None
        self.canvas = None
        self._pick_cid = None
        self._active_point_records = []
        self._active_plot_axes = {}
        self._tooltip_window = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create GUI widgets for plot display."""
        self.layout_frame = ttk.Frame(self)
        self.layout_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.layout_frame.columnconfigure(0, weight=1)
        self.layout_frame.columnconfigure(1, weight=0, minsize=150)
        self.layout_frame.rowconfigure(0, weight=1)

        # Canvas frame for plot area
        self.canvas_frame = ttk.Frame(self.layout_frame)
        self.canvas_frame.grid(row=0, column=0, sticky=tk.NSEW)

        # Details frame for clicked point information
        self.details_frame = ttk.LabelFrame(self.layout_frame, text="Point Details", padding=8)
        self.details_frame.grid(row=0, column=1, sticky=tk.NSEW, padx=(10, 0))
        self.details_frame.configure(width=150)
        self.details_frame.grid_propagate(False)
        self.details_frame.grid_remove()

        self.details_frame.columnconfigure(0, weight=1)

        self.detail_value_labels = {}
        for display_label, source_key in DETAIL_FIELD_MAP:
            row_frame = ttk.Frame(self.details_frame)
            row_frame.pack(fill=tk.X, pady=1)

            label = ttk.Label(row_frame, text=f"{display_label}:", width=18)
            label.pack(side=tk.LEFT, anchor=tk.W)

            value_label = ttk.Label(row_frame, text="", wraplength=240, justify=tk.LEFT)
            value_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.detail_value_labels[display_label] = value_label

        self.matches_frame = ttk.Frame(self.details_frame)
        self.matches_label = ttk.Label(self.matches_frame, text="Matching points")
        self.matches_label.pack(anchor=tk.W, pady=(8, 2))

        matches_list_frame = ttk.Frame(self.matches_frame)
        matches_list_frame.pack(fill=tk.BOTH, expand=False)

        self.matches_scrollbar = ttk.Scrollbar(matches_list_frame)
        self.matches_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.matches_listbox = tk.Listbox(
            matches_list_frame,
            height=5,
            yscrollcommand=self.matches_scrollbar.set,
        )
        self.matches_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.matches_scrollbar.config(command=self.matches_listbox.yview)
        self.matches_listbox.bind("<<ListboxSelect>>", self._on_match_selected)

        self.matches_frame.pack_forget()
    
    def display_plot(self, fig):
        """Display a matplotlib figure."""
        self._destroy_tooltip()
        self._clear_details(hide=True)

        self.current_fig = fig
        
        # Clear previous canvas
        if self.canvas is not None:
            if self._pick_cid is not None:
                self.canvas.mpl_disconnect(self._pick_cid)
            self.canvas.get_tk_widget().destroy()
        
        # Create new canvas
        self.canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self._pick_cid = self.canvas.mpl_connect("button_press_event", self._on_canvas_click)
    
    def clear_plot(self):
        """Clear the displayed plot."""
        if self.canvas is not None:
            if self._pick_cid is not None:
                self.canvas.mpl_disconnect(self._pick_cid)
                self._pick_cid = None
            self.canvas.get_tk_widget().destroy()
            self.canvas = None
        self.current_fig = None
        self._destroy_tooltip()
        self._clear_details(hide=True)
    
    def _on_generate_click(self):
        """Handle generate plot button click."""
        # This will be called by the main app
        pass

    def _on_canvas_click(self, event):
        """Resolve clicked artists back to their source rows."""
        if self.current_fig is None or event.button not in (1, MouseButton.LEFT):
            return

        if event.inaxes is None:
            self._clear_details(hide=True)
            return

        matches = self._collect_point_matches(event)
        if not matches:
            self._clear_details(hide=True)
            return

        self._show_point_records(matches, event)

    def _collect_point_matches(self, event):
        """Collect all point records hit by a canvas click."""
        clickable_artists = getattr(self.current_fig, '_clickable_artists', [])
        matches = []

        for artist in clickable_artists:
            contains, info = artist.contains(event)
            if not contains:
                continue

            point_records = getattr(artist, '_point_records', [])
            plot_axes = getattr(artist, '_plot_axes', {})
            for index in info.get('ind', []):
                if 0 <= index < len(point_records):
                    matches.append((point_records[index], plot_axes))

        unique_matches = []
        seen_rows = set()
        for record, plot_axes in matches:
            row_index = record.get('_row_index')
            if row_index in seen_rows:
                continue
            seen_rows.add(row_index)
            unique_matches.append((record, plot_axes))

        return unique_matches

    def _show_point_records(self, matches, event):
        """Display the selected point data in the right-side details frame."""
        self._active_point_records = [record for record, _ in matches]
        self._active_plot_axes = matches[0][1] if matches else {}

        self.details_frame.grid()

        if len(self._active_point_records) > 1:
            self.matches_frame.pack(fill=tk.X, pady=(8, 0))
            self.matches_listbox.delete(0, tk.END)
            for index, record in enumerate(self._active_point_records, start=1):
                self.matches_listbox.insert(tk.END, self._format_match_entry(index, record))
            self.matches_listbox.selection_clear(0, tk.END)
            self.matches_listbox.selection_set(0)
            self.matches_listbox.activate(0)
            self.matches_listbox.see(0)
        else:
            self.matches_frame.pack_forget()

        self._render_point_details(self._active_point_records[0])
        self._show_tooltip(event, self._active_point_records[0])

    def _render_point_details(self, record):
        """Render the selected row fields into the details labels."""
        for display_label, source_key in DETAIL_FIELD_MAP:
            if source_key == "Value":
                value = _display_value_3dp(record.get(source_key))
            else:
                value = _display_value(record.get(source_key))
            self.detail_value_labels[display_label].config(text=str(value))

    def _format_match_entry(self, index, record):
        """Build a compact label for a matched point list entry."""
        coordinates = record.get('_coordinates', {})
        x_label = self._active_plot_axes.get('x_label', self._active_plot_axes.get('x_axis', 'X'))
        y_label = self._active_plot_axes.get('y_label', self._active_plot_axes.get('y_axis', 'Y'))
        z_label = self._active_plot_axes.get('z_label', self._active_plot_axes.get('z_axis'))
        coordinate_parts = [
            f"{x_label}={_display_value(coordinates.get('x'))}",
            f"{y_label}={_display_value(coordinates.get('y'))}",
        ]
        if 'z' in coordinates and z_label:
            coordinate_parts.append(f"{z_label}={_display_value(coordinates.get('z'))}")

        paper = _display_value(record.get('Paper Title'))
        variable = _display_value(record.get('Variable'))
        value = _display_value(record.get('Value'))
        return f"{index}. {paper} | {variable} | {value} | {', '.join(coordinate_parts)}"

    def _on_match_selected(self, event):
        """Update the details section when a user selects a different match."""
        if not self._active_point_records:
            return

        selection = self.matches_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        if 0 <= index < len(self._active_point_records):
            self._render_point_details(self._active_point_records[index])

    def _clear_details(self, hide=False):
        """Clear the point details view."""
        self._active_point_records = []
        self._active_plot_axes = {}
        for value_label in self.detail_value_labels.values():
            value_label.config(text="")
        self.matches_listbox.delete(0, tk.END)
        self.matches_frame.pack_forget()
        if hide:
            self.details_frame.grid_remove()

    def _show_tooltip(self, event, record):
        """Show a transient tooltip with the selected point summary."""
        self._destroy_tooltip()

        tooltip_text = self._build_tooltip_text(record)
        if not tooltip_text:
            return

        tooltip = tk.Toplevel(self)
        tooltip.withdraw()
        tooltip.overrideredirect(True)
        tooltip.attributes("-topmost", True)
        try:
            x_pos, y_pos = self._resolve_tooltip_position(event)

            frame = ttk.Frame(tooltip, padding=6, relief=tk.SOLID, borderwidth=1)
            frame.pack(fill=tk.BOTH, expand=True)
            ttk.Label(frame, text=tooltip_text, justify=tk.LEFT).pack()

            tooltip.geometry(f"+{x_pos}+{y_pos}")
            tooltip.deiconify()

            self._tooltip_window = tooltip
            tooltip.after(1800, lambda win=tooltip: self._destroy_specific_tooltip(win))
        except Exception:
            try:
                tooltip.destroy()
            except Exception:
                pass
            self._tooltip_window = None

    def _resolve_tooltip_position(self, event):
        """Resolve safe screen coordinates for tooltip placement."""
        x_root = getattr(event, 'x_root', None)
        y_root = getattr(event, 'y_root', None)

        if x_root is None or y_root is None:
            gui_event = getattr(event, 'guiEvent', None)
            x_root = getattr(gui_event, 'x_root', x_root)
            y_root = getattr(gui_event, 'y_root', y_root)

        if x_root is None or y_root is None:
            if self.canvas is not None:
                widget = self.canvas.get_tk_widget()
                x_root = widget.winfo_pointerx()
                y_root = widget.winfo_pointery()
            else:
                x_root = self.winfo_pointerx()
                y_root = self.winfo_pointery()

        return int(x_root) + 15, int(y_root) + 15

    def _build_tooltip_text(self, record):
        """Build short tooltip text for the selected point."""
        paper = _display_value(record.get('Paper Title'))
        variable = _display_value(record.get('Variable'))
        coordinates = record.get('_coordinates', {})
        x_label = self._active_plot_axes.get('x_label', self._active_plot_axes.get('x_axis', 'X'))
        y_label = self._active_plot_axes.get('y_label', self._active_plot_axes.get('y_axis', 'Y'))
        z_label = self._active_plot_axes.get('z_label', self._active_plot_axes.get('z_axis'))

        lines = [f"Paper: {paper}", f"Variable: {variable}"]
        lines.append(f"{x_label}: {_display_value(coordinates.get('x'))}")
        lines.append(f"{y_label}: {_display_value(coordinates.get('y'))}")
        if 'z' in coordinates and z_label:
            lines.append(f"{z_label}: {_display_value(coordinates.get('z'))}")
        return "\n".join(lines)

    def _destroy_tooltip(self):
        """Destroy the current tooltip if one is visible."""
        if self._tooltip_window is not None:
            try:
                self._tooltip_window.destroy()
            except tk.TclError:
                pass
            self._tooltip_window = None

    def _destroy_specific_tooltip(self, tooltip):
        """Destroy a specific tooltip instance only if it is still current."""
        if self._tooltip_window is tooltip:
            self._destroy_tooltip()
    
    def _on_save_click(self):
        """Handle save plot button click."""
        if self.current_fig is None:
            messagebox.showwarning("No Plot", "Please generate a plot first.")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                # Save at 300 DPI for publication quality
                self.current_fig.savefig(file_path, dpi=300, bbox_inches='tight')
                messagebox.showinfo("Success", f"Plot saved to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save plot:\n{str(e)}")


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class VisualisierApp(tk.Tk):
    """Main application window."""
    
    def __init__(self):
        """Initialize the application."""
        super().__init__()
        self.title("Exploratory Data Visualiser")
        self.geometry("1400x900")
        
        # Data
        self.df = None
        self.data_file = None
        self.selected_papers = []
        self.all_papers = []
        self.axis_mapping = {}  # Maps display names to actual column names or symbols
        self.project = ProjectState.blank()
        
        # Create menu and UI
        self._create_menu_bar()
        # Create main layout
        self._create_layout()
        
        # Load initial data
        self._load_initial_data()

    def _create_menu_bar(self):
        """Create the main File/Edit menu bar."""
        menu_bar = tk.Menu(self)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="New Project", command=lambda: self._new_project())
        file_menu.add_command(label="Open Project...", command=lambda: self._open_project())
        file_menu.add_command(label="Save Project", command=lambda: self._save_project())
        file_menu.add_command(label="Save As...", command=lambda: self._save_project_as())
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)

        edit_menu = tk.Menu(menu_bar, tearoff=0)
        edit_menu.add_command(label="Import Papers", command=lambda: self._import_project_data())
        edit_menu.add_command(label="Export Figures", command=lambda: self._export_figures())

        menu_bar.add_cascade(label="File", menu=file_menu)
        menu_bar.add_cascade(label="Edit", menu=edit_menu)
        self.config(menu=menu_bar)
    
    def _find_data_file(self):
        """Find the research data file (clean_data_master.csv from preprocessing pipeline)."""
        workspace_root = Path(__file__).parent.parent.parent

        staging_dir = workspace_root / "Staging"
        master_file = staging_dir / "clean_data_master.csv"

        if master_file.exists():
            self.data_file = str(master_file)
            return

        if staging_dir.exists():
            csv_files = list(staging_dir.glob("clean_data*.csv"))
            if csv_files:
                csv_files = sorted(csv_files, key=lambda x: (x.name != "clean_data_master.csv", x.name))
                self.data_file = str(csv_files[0])
                return
    
    def _create_layout(self):
        """Create the main application layout with ribbon toolbar."""
        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # ====== RIBBON TOOLBAR (TOP) ======
        ribbon = ttk.LabelFrame(main_frame, text="Controls", padding=5)
        ribbon.pack(fill=tk.BOTH, expand=False, padx=0, pady=(0, 5))
        
        # Create a container for left controls and right selected papers list
        ribbon_container = ttk.Frame(ribbon)
        ribbon_container.pack(fill=tk.BOTH, expand=True)
        
        # Configure columns for equal widths
        ribbon_container.columnconfigure(0, weight=1, minsize=100)  # Left panel
        ribbon_container.columnconfigure(1, weight=1, minsize=200)  # Right panel
        ribbon_container.rowconfigure(0, weight=1)
        
        # LEFT SIDE: All controls
        left_side = ttk.Frame(ribbon_container)
        left_side.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
        # Row 1: Paper Selection
        row1 = ttk.Frame(left_side)
        row1.pack(fill=tk.X, pady=2)
        
        ttk.Label(row1, text="Papers:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        self.paper_var = tk.StringVar()
        self.paper_dropdown = ttk.Combobox(row1, textvariable=self.paper_var, 
                                           state="readonly")
        self.paper_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(row1, text="Add", command=self._add_paper).pack(side=tk.LEFT, padx=2)
        ttk.Button(row1, text="Remove", command=self._remove_paper).pack(side=tk.LEFT, padx=2)
        ttk.Button(row1, text="Add All", command=self._add_all_papers).pack(side=tk.LEFT, padx=2)
        ttk.Button(row1, text="Clear", command=self._clear_papers).pack(side=tk.LEFT, padx=2)
        
        # ====== Row 2: Plot Type and Mode ======
        row2 = ttk.Frame(left_side)
        row2.pack(fill=tk.X, pady=2)    
        
        ttk.Label(row2, text="Plot Type:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        self.plot_type_var = tk.StringVar(value="2d")
        ttk.Radiobutton(row2, text="2D", variable=self.plot_type_var, 
                       value="2d", command=self._on_plot_type_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(row2, text="3D", variable=self.plot_type_var, 
                       value="3d", command=self._on_plot_type_change).pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(row2, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        ttk.Label(row2, text="Mode:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        self.plot_mode_var = tk.StringVar(value="scatter")
        ttk.Radiobutton(row2, text="Scatter", variable=self.plot_mode_var, 
                       value="scatter").pack(side=tk.LEFT, padx=5)
        self.mode_line_button = ttk.Radiobutton(row2, text="Line", variable=self.plot_mode_var, 
                       value="line")
        self.mode_line_button.pack(side=tk.LEFT, padx=5)
        self.mode_surface_button = ttk.Radiobutton(row2, text="Surface", variable=self.plot_mode_var, 
                       value="surface", state=tk.DISABLED)
        self.mode_surface_button.pack(side=tk.LEFT, padx=5)
        
        # ====== Row 3: Axes Configuration ======
        row3 = ttk.Frame(left_side)
        row3.pack(fill=tk.X, pady=2)
        
        ttk.Label(row3, text="X Axis:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        self.x_axis_var = tk.StringVar()
        self.x_axis_dropdown = ttk.Combobox(row3, textvariable=self.x_axis_var, 
                                            state="readonly", width=15)
        self.x_axis_dropdown.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(row3, text="Y Axis:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        self.y_axis_var = tk.StringVar()
        self.y_axis_dropdown = ttk.Combobox(row3, textvariable=self.y_axis_var, 
                                            state="readonly", width=15)
        self.y_axis_dropdown.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(row3, text="Z Axis:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        self.z_axis_var = tk.StringVar()
        self.z_axis_dropdown = ttk.Combobox(row3, textvariable=self.z_axis_var, 
                                            state="readonly", width=15)
        self.z_axis_dropdown.config(state=tk.DISABLED)
        self.z_axis_dropdown.pack(side=tk.LEFT, padx=5)
        
        # ====== Row 5: Action Buttons ======
        row5 = ttk.Frame(left_side)
        row5.pack(fill=tk.X, pady=2)
        
        ttk.Button(row5, text="Generate Plot", command=lambda: self._generate_plot()).pack(side=tk.LEFT, padx=5)
        ttk.Button(row5, text="Save Plot", command=lambda: self._save_plot()).pack(side=tk.LEFT, padx=5)
        ttk.Button(row5, text="Clear", command=lambda: self._clear_plot()).pack(side=tk.LEFT, padx=5)
        
        # ====== Binning Controls (below plot controls in left_side) ======
        self.binning_panel = BinningConfigPanel(left_side, on_bins_set=lambda: self._on_bins_set())
        self.binning_panel.pack(fill=tk.X, pady=(5, 0))
        
        # RIGHT SIDE: Selected Papers List
        right_side = ttk.LabelFrame(ribbon_container, text="Selected Papers", padding=5)
        right_side.grid(row=0, column=1, sticky='nsew', padx=(5, 0), ipadx=5)
        
        # Create scrollable listbox for selected papers
        scrollbar = ttk.Scrollbar(right_side)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.selected_papers_listbox = tk.Listbox(right_side, yscrollcommand=scrollbar.set, 
                                                   height=8)
        self.selected_papers_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.selected_papers_listbox.yview)
        
        # ====== CONTENT AREA (BLUE REGION - PLOT CANVAS ONLY) ======
        content_area = ttk.LabelFrame(main_frame, text="Plot Display", padding=0)
        content_area.pack(fill=tk.BOTH, expand=True, padx=0, pady=(5, 0))
        
        # ====== PLOT DISPLAY AREA (CANVAS ONLY) ======
        self.plot_display = PlotDisplayPanel(content_area)
        self.plot_display.pack(fill=tk.BOTH, expand=True)
    
    def _add_paper(self):
        """Add selected paper to list."""
        paper = self.paper_var.get()
        if paper and paper not in self.selected_papers:
            self.selected_papers.append(paper)
            self._update_selected_papers_display_listbox()
            self._refresh_axis_dropdowns()
            self.binning_panel.set_selected_papers(self.selected_papers)
    
    def _add_all_papers(self):
        """Add all papers to selection."""
        self.selected_papers = self.all_papers.copy()
        self._update_selected_papers_display_listbox()
        self._refresh_axis_dropdowns()
        self.binning_panel.set_selected_papers(self.selected_papers)

    def _remove_paper(self):
        """Remove last selected paper from list."""
        if self.selected_papers:
            self.selected_papers.pop()
            self._update_selected_papers_display_listbox()
            self._refresh_axis_dropdowns()
            self.binning_panel.set_selected_papers(self.selected_papers)

    def _clear_papers(self):
        """Clear all selected papers."""
        self.selected_papers = []
        self._update_selected_papers_display_listbox()
        self._refresh_axis_dropdowns()
        self.binning_panel.set_selected_papers(self.selected_papers)
    
    def _update_selected_papers_display_listbox(self):
        """Update the listbox display of selected papers."""
        self.selected_papers_listbox.delete(0, tk.END)
        for i, paper in enumerate(self.selected_papers, 1):
            self.selected_papers_listbox.insert(tk.END, f"{i}. {paper}")

    def _refresh_axis_dropdowns(self):
        """Refresh axis dropdowns based on currently selected papers."""
        if not self.selected_papers:
            papers_for_symbols = self.all_papers
        else:
            papers_for_symbols = self.selected_papers

        input_vars = [
            'Reynolds number (Re)',
            'P/e',
            'e/D',
            'Alpha',
            'Aspect ratio',
            'Number of ribbed walls'
        ]

        output_vars = data_loader.get_available_symbols(self.df, papers_for_symbols)

        axis_display_list = (
            ['INPUT VARIABLES:'] +
            input_vars +
            ['─────────────────'] +
            ['OUTPUT VARIABLES:'] +
            output_vars
        )

        self.axis_mapping = {col: col for col in input_vars}
        for symbol in output_vars:
            self.axis_mapping[symbol] = ('symbol', symbol)

        self.x_axis_dropdown['values'] = axis_display_list
        self.y_axis_dropdown['values'] = axis_display_list
        self.z_axis_dropdown['values'] = axis_display_list
    
    def _on_plot_type_change(self):
        """Handle plot type change (2D vs 3D)."""
        is_3d = self.plot_type_var.get() == "3d"
        
        # Enable/disable Z axis
        self.z_axis_dropdown.config(state=tk.NORMAL if is_3d else tk.DISABLED)
        
        # Enable/disable plot mode buttons based on plot type
        if is_3d:
            # For 3D: enable Surface, disable Line
            self.mode_line_button.config(state=tk.DISABLED)
            self.mode_surface_button.config(state=tk.NORMAL)
        else:
            # For 2D: enable Line, disable Surface
            self.mode_line_button.config(state=tk.NORMAL)
            self.mode_surface_button.config(state=tk.DISABLED)
        
        # Reset mode if needed
        if is_3d and self.plot_mode_var.get() == "line":
            self.plot_mode_var.set("scatter")
        elif not is_3d and self.plot_mode_var.get() == "surface":
            self.plot_mode_var.set("scatter")
    
    def _save_plot(self):
        """Save the current plot."""
        self.plot_display._on_save_click()
    
    def _clear_plot(self):
        """Clear the current plot."""
        self.plot_display.clear_plot()
    
    def _load_initial_data(self):
        """Initialize the UI in a blank project state."""
        self.df = None
        self.data_file = None
        self.selected_papers = []
        self.all_papers = []
        self.axis_mapping = {}

        self.paper_dropdown['values'] = []
        self.x_axis_dropdown['values'] = []
        self.y_axis_dropdown['values'] = []
        self.z_axis_dropdown['values'] = []
        self.x_axis_var.set('')
        self.y_axis_var.set('')
        self.z_axis_var.set('')

        self.binning_panel.set_dataframe(None)
        self.binning_panel.set_available_parameters([])
        self.binning_panel.set_selected_papers([])
        self._update_selected_papers_display_listbox()

    def _new_project(self):
        """Create a new blank project and set up its folder structure."""
        base_dir = filedialog.askdirectory(title="Select project directory")
        if not base_dir:
            return

        project_name = simpledialog.askstring("New Project", "Enter project name:", parent=self)
        if not project_name:
            return

        project_root, data_dir, project_file = build_project_paths(Path(base_dir), project_name)
        project_root.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)

        self.project = ProjectState(
            name=sanitize_project_name(project_name),
            root_dir=project_root,
            data_dir=data_dir,
            project_file=project_file,
        )
        self._load_initial_data()
        self._sync_project_from_ui()
        save_project_file(self.project)
        self.project.dirty = False

    def _open_project(self):
        """Open an existing project from a .prj file."""
        project_file = filedialog.askopenfilename(
            title="Open project file",
            filetypes=[("Project files", "*.prj")],
        )
        if not project_file:
            return

        try:
            self.project = load_project_file(Path(project_file))
            self._reload_project_data()
            self.selected_papers = list(self.project.selected_papers)
            self._update_selected_papers_display_listbox()
            self._refresh_axis_dropdowns()
            self.binning_panel.set_selected_papers(self.selected_papers)
            self.project.dirty = False
        except Exception as e:
            messagebox.showerror("Open Project", f"Failed to open project:\n{str(e)}")

    def _save_project(self):
        """Save the active project state to its current location."""
        if not self.project.is_loaded():
            self._save_project_as()
            return

        self._sync_project_from_ui()
        save_project_file(self.project)
        self.project.dirty = False
        messagebox.showinfo("Project Saved", f"Saved project to {self.project.project_file}")

    def _save_project_as(self):
        """Save the active project state into a new project directory."""
        base_dir = filedialog.askdirectory(title="Choose project save location")
        if not base_dir:
            return

        project_name = simpledialog.askstring("Save Project As", "Enter project name:", parent=self)
        if not project_name:
            return

        project_root, data_dir, project_file = build_project_paths(Path(base_dir), project_name)
        project_root.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)

        if self.project.data_dir and self.project.data_dir.exists():
            for item in self.project.data_dir.iterdir():
                destination = data_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, destination, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, destination)

        self.project.name = sanitize_project_name(project_name)
        self.project.root_dir = project_root
        self.project.data_dir = data_dir
        self.project.project_file = project_file
        self._sync_project_from_ui()
        save_project_file(self.project)
        self.project.dirty = False
        messagebox.showinfo("Project Saved", f"Saved project to {self.project.project_file}")

    def _import_project_data(self):
        """Open the import dialog to select raw data and metadata files."""
        if not self.project.is_loaded():
            messagebox.showwarning("No Project", "Create or open a project before importing data.")
            return

        ImportDialog(self, on_complete=self._perform_import)

    def _perform_import(self, raw_file: str, metadata_files: list):
        """Perform the actual import after the dialog completes."""
        try:
            if not raw_file or not metadata_files:
                return

            paper_folder = self.project.next_paper_name()
            paper_dir = self.project.data_dir / paper_folder
            paper_dir.mkdir(parents=True, exist_ok=True)

            # Normalize raw file to CSV filename for pipeline compatibility
            dest_raw = paper_dir / "raw_data.csv"
            shutil.copy2(raw_file, dest_raw)

            for index, metadata_file in enumerate(metadata_files):
                destination_name = "manifest.json" if index == 0 else f"metadata_{index + 1}.json"
                shutil.copy2(metadata_file, paper_dir / destination_name)

            # Run preprocessing on the project's Data folder
            self._run_project_preprocessor()
            # Reload master file if generated
            self._reload_project_data()
            self.project.dirty = True
            messagebox.showinfo("Import Complete", f"Imported into {paper_dir}")

        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import files:\n{e}")


class ImportDialog(tk.Toplevel):
    """Two-step dialog for importing a raw data file and metadata JSON files.

    Step 1: Show message "Select raw data file (.xlsx, .csv)" with a Browse
    button. Browse opens a folder chooser; files in the folder are listed and the
    user picks a CSV/XLSX file from the list.

    Step 2: Ask the user to pick one or more metadata JSON files, then confirm.
    """

    def __init__(self, parent, on_complete=None):
        super().__init__(parent)
        self.title("Import Data")
        self.parent = parent
        self.on_complete = on_complete
        self.raw_file = None
        self.metadata_files = []

        self._build_ui()
        self.transient(parent)
        self.grab_set()
        # do not block the caller; return to allow mainloop to continue

    def _build_ui(self):
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Select raw data file (.xlsx, .csv)").pack(anchor=tk.W)

        browse_row = ttk.Frame(frm)
        browse_row.pack(fill=tk.X, pady=5)
        self.folder_var = tk.StringVar()
        ttk.Entry(browse_row, textvariable=self.folder_var, width=60, state='readonly').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(browse_row, text="Browse", command=self._on_browse_folder).pack(side=tk.LEFT)

        self.files_listbox = tk.Listbox(frm, height=6)
        self.files_listbox.pack(fill=tk.BOTH, expand=True, pady=(5, 5))

        select_row = ttk.Frame(frm)
        select_row.pack(fill=tk.X)
        ttk.Button(select_row, text="Select Raw File", command=self._select_raw_from_list).pack(side=tk.LEFT)
        ttk.Button(select_row, text="Next: Select Metadata", command=self._on_next).pack(side=tk.RIGHT)

    def _on_browse_folder(self):
        folder = filedialog.askdirectory(title="Browse folder containing raw data")
        if not folder:
            return

        self.folder_var.set(folder)
        p = Path(folder)
        candidates = sorted([str(f.name) for f in p.iterdir() if f.is_file() and f.suffix.lower() in ('.csv', '.xlsx', '.xls')])
        self.files_listbox.delete(0, tk.END)
        for f in candidates:
            self.files_listbox.insert(tk.END, f)

    def _select_raw_from_list(self):
        sel = self.files_listbox.curselection()
        if not sel:
            messagebox.showwarning("Select File", "Please select a raw data file from the list.")
            return

        filename = self.files_listbox.get(sel[0])
        folder = self.folder_var.get()
        self.raw_file = str(Path(folder) / filename)
        messagebox.showinfo("Raw File Selected", f"Selected: {self.raw_file}")

    def _on_next(self):
        if not self.raw_file:
            messagebox.showwarning("No Raw File", "Please select a raw data file first.")
            return

        metadata = filedialog.askopenfilenames(title="Select metadata files (.json)", filetypes=[("JSON files", "*.json")])
        if not metadata:
            return

        self.metadata_files = list(metadata)

        if messagebox.askyesno("Confirm Import", f"Import raw file:\n{self.raw_file}\nwith {len(self.metadata_files)} metadata file(s)?"):
            if self.on_complete:
                self.on_complete(self.raw_file, self.metadata_files)
            self.destroy()

    def _export_figures(self):
        """Export the currently displayed figure as an image file."""
        self.plot_display._on_save_click()

    def _sync_project_from_ui(self):
        """Store the current UI state into the project model."""
        self.project.selected_papers = list(self.selected_papers)
        self.project.available_papers = list(self.all_papers)

        figure_spec = self._build_active_figure_spec()
        self.project.figures = [figure_spec] if figure_spec else []

    def _build_active_figure_spec(self):
        """Build a project figure definition from the current plot controls."""
        if not self.selected_papers or not self.x_axis_var.get() or not self.y_axis_var.get():
            return None

        return FigureSpec(
            papers_included=list(self.selected_papers),
            x_variable=self.x_axis_var.get(),
            y_variable=self.y_axis_var.get(),
            z_variable=self.z_axis_var.get(),
            plot_representation=f"{self.plot_type_var.get()}_{self.plot_mode_var.get()}",
            binning_data=self.binning_panel.get_bins_config() or {},
        )

    def _run_project_preprocessor(self):
        """Run preprocessing against the project's Data folder."""
        if not self.project.data_dir:
            return

        preprocessor = MetaAnalysisPreprocessor(self.project.data_dir, verbose=False)
        preprocessor.run_all_papers()

    def _reload_project_data(self):
        """Reload the project dataframe and UI from the project's master CSV."""
        if not self.project.data_dir:
            return

        master_file = self.project.data_dir / "clean_data_master.csv"
        if not master_file.exists():
            return

        try:
            self.df = data_loader.load_research_data(str(master_file))
            if 'Paper Title' in self.df.columns:
                self.all_papers = sorted(self.df['Paper Title'].unique().tolist())
                self.paper_dropdown['values'] = self.all_papers

            input_vars = [
                'Reynolds number (Re)',
                'P/e',
                'e/D',
                'Alpha',
                'Aspect ratio',
                'Number of ribbed walls'
            ]
            output_vars = data_loader.get_available_symbols(self.df, self.all_papers)

            axis_display_list = (
                ['INPUT VARIABLES:'] +
                input_vars +
                ['─────────────────'] +
                ['OUTPUT VARIABLES:'] +
                output_vars
            )

            self.axis_mapping = {col: col for col in input_vars}
            for symbol in output_vars:
                self.axis_mapping[symbol] = ('symbol', symbol)

            self.x_axis_dropdown['values'] = axis_display_list
            self.y_axis_dropdown['values'] = axis_display_list
            self.z_axis_dropdown['values'] = axis_display_list
            self.binning_panel.set_dataframe(self.df)
            self.binning_panel.set_available_parameters(input_vars)
            self.binning_panel.set_selected_papers(self.selected_papers)
            self.paper_dropdown['values'] = self.all_papers

            if self.selected_papers:
                self._update_selected_papers_display_listbox()
                self._refresh_axis_dropdowns()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to reload project data:\n{str(e)}")
    
    def _on_config_change(self):
        """Handle configuration changes."""
        # Could enable/disable generate button based on validation
        pass

    def _on_bins_set(self):
        """Callback when bins are set in binning panel."""
        pass
    
    def _generate_plot(self):
        """Generate plot based on current configuration."""
        try:
            # Get selected papers
            if not self.selected_papers:
                messagebox.showwarning("No Papers", "Please select at least one paper.")
                return
            
            # Filter data by selected papers
            filtered_df = self.df[self.df['Paper Title'].isin(self.selected_papers)].copy()
            
            # Get axes configuration (display values)
            x_axis_display = self.x_axis_var.get()
            y_axis_display = self.y_axis_var.get()
            z_axis_display = self.z_axis_var.get()
            plot_type = self.plot_type_var.get()
            plot_mode = self.plot_mode_var.get()
            
            # Validate axes
            if not x_axis_display or not y_axis_display:
                messagebox.showwarning("Missing Axes", 
                                       "Please select X and Y axes.")
                return
            
            if plot_type == '3d' and not z_axis_display:
                messagebox.showwarning("Missing Axis", 
                                       "Please select Z axis for 3D plots.")
                return
            
            # Resolve axis display names to actual column names
            x_axis, x_is_symbol = self._resolve_axis(x_axis_display)
            y_axis, y_is_symbol = self._resolve_axis(y_axis_display)
            z_axis, z_is_symbol = self._resolve_axis(z_axis_display) if z_axis_display else (None, False)
            
            if not x_axis or not y_axis:
                messagebox.showwarning("Invalid Axis", "Please select valid axes (not section headers).")
                return
            
            # Prepare display labels (to preserve original names in plot titles)
            x_label = x_axis_display if x_axis_display not in [' ', '─────────────────', 'INPUT VARIABLES:', 'OUTPUT VARIABLES:'] else x_axis
            y_label = y_axis_display if y_axis_display not in [' ', '─────────────────', 'INPUT VARIABLES:', 'OUTPUT VARIABLES:'] else y_axis
            z_label = z_axis_display if z_axis_display and z_axis_display not in [' ', '─────────────────', 'INPUT VARIABLES:', 'OUTPUT VARIABLES:'] else (z_axis if z_axis else None)
            
            # Filter by symbols if selected
            if x_is_symbol:
                filtered_df = filtered_df[filtered_df['Variable'] == x_axis].copy()
                x_axis = 'Value'
            
            if y_is_symbol:
                filtered_df = filtered_df[filtered_df['Variable'] == y_axis].copy()
                y_axis = 'Value'
            
            if z_axis and z_is_symbol:
                filtered_df = filtered_df[filtered_df['Variable'] == z_axis].copy()
                z_axis = 'Value'
            
            # Validate that we have data after filtering
            if filtered_df.empty:
                messagebox.showwarning("No Data", "No data available for selected papers and symbols.")
                return
            
            # Remove rows with NaN values in the axis columns to ensure valid plotting data
            axis_cols = [x_axis, y_axis]
            if z_axis:
                axis_cols.append(z_axis)
            
            filtered_df = filtered_df.dropna(subset=axis_cols, how='any')
            
            # Validate we still have data after dropping NaN
            if filtered_df.empty:
                messagebox.showwarning("No Valid Data", 
                                       f"No valid numeric data available for the selected axes.\n"
                                       f"Some axis columns may contain non-numeric or missing values.")
                return
            
            # Prepare binning configuration from panel
            bins_config = self.binning_panel.get_bins_config()
            
            # Generate plot
            if plot_type == '2d':
                if plot_mode == 'scatter':
                    fig = create_custom_2d_scatter(filtered_df, x_axis, y_axis, x_label, y_label, bins_config)
                else:  # line
                    fig = create_custom_2d_line(filtered_df, x_axis, y_axis, x_label, y_label, bins_config)
            else:  # 3d
                if plot_mode == 'scatter':
                    fig = create_custom_3d_scatter(filtered_df, x_axis, y_axis, z_axis, x_label, y_label, z_label, bins_config)
                else:  # surface
                    fig = create_custom_3d_surface(filtered_df, x_axis, y_axis, z_axis, x_label, y_label, z_label, bins_config)
            
            # Display plot
            self.plot_display.display_plot(fig)
            
        except Exception as e:
            messagebox.showerror("Plot Error", f"Failed to generate plot:\n{str(e)}")
    
    def _resolve_axis(self, axis_display):
        """
        Resolve axis display name to actual column name.
        
        Args:
            axis_display: Display name from dropdown
            
        Returns:
            Tuple of (actual_column_name, is_symbol)
            - is_symbol: True if it's an output variable (symbol), False if input variable
        """
        if axis_display in [' ', '─────────────────', 'INPUT VARIABLES:', 'OUTPUT VARIABLES:']:
            return None, False
        
        if axis_display in self.axis_mapping:
            mapping = self.axis_mapping[axis_display]
            if isinstance(mapping, tuple):
                # It's a symbol: ('symbol', 'Nu')
                return mapping[1], True
            else:
                # It's a regular column name
                return mapping, False
        
        return axis_display, False


def main():
    """Main entry point."""
    app = VisualisierApp()
    app.mainloop()


if __name__ == "__main__":
    main()
