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
    copy_default_config_to_project,
    get_project_config_path,
    load_project_config,
    save_project_config,
)

# Forward-declare ImportDialog name so static checks won't flag references
ImportDialog = None

# Define a set of distinct colors for binning visualization
DEFAULT_COLORS = {
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


def get_bin_colors_symbols(n_bins, project_config=None):
    """Return style mapping for each bin number using configured colors and markers.

    Args:
        n_bins: Number of bins
        project_config: Optional dict from project-local config (keys: MARKERS, etc.)
    """
    colors_list = list(DEFAULT_COLORS.values())
    if project_config and project_config.get('MARKERS'):
        markers_list = list(project_config['MARKERS'])
    else:
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

def _extract_plot_style(project_config, default_alpha=0.6):
    """Extract common plot styling from project configuration."""
    return {
        'scatter_size': (project_config or {}).get('SCATTER_SIZE', 70),
        'scatter_alpha': (project_config or {}).get('SCATTER_ALPHA', default_alpha),
        'legend_loc': (project_config or {}).get('LEGEND_LOCATION', 'best'),
        'grid_style': (project_config or {}).get('GRID_STYLE', '--'),
        'grid_alpha': (project_config or {}).get('GRID_ALPHA', 0.3)
    }

def _prepare_bin_groups(df, bins_config, project_config, sort_by=None):
    """Prepare dataframe subsets and styles for binned plotting."""
    bin_assignment = assign_points_to_bins(df, bins_config['parameter'], bins_config['bins'])
    bin_styles = get_bin_colors_symbols(len(bins_config['bins']), project_config)
    
    groups = []
    for bin_dict in bins_config['bins']:
        bin_num = bin_dict['bin_number']
        mask = bin_assignment == bin_num
        if mask.any():
            subset = df.iloc[np.flatnonzero(mask)].copy()
            if sort_by:
                subset = subset.sort_values(sort_by)
            style = bin_styles[bin_num]
            label = get_bin_legend_label(bins_config['parameter'], bin_dict)
            groups.append((subset, style, label))
    return groups

def create_custom_2d_scatter(df, x_axis, y_axis, x_label=None, y_label=None, bins_config=None, project_config=None):
    """Create 2D scatter plot with optional binning."""
    style = _extract_plot_style(project_config)
    scatter_size, scatter_alpha, legend_loc, grid_style, grid_alpha = (
        style['scatter_size'], style['scatter_alpha'], style['legend_loc'],
        style['grid_style'], style['grid_alpha']
    )

    fig = Figure(figsize=(8, 6), dpi=100)
    ax = fig.add_subplot(111)
    fig._clickable_artists = []
    
    # Use display labels if provided, otherwise use column names
    x_display = x_label if x_label else x_axis
    y_display = y_label if y_label else y_axis
    
    if bins_config and bins_config['enabled']:
        for subset, bin_style, label in _prepare_bin_groups(df, bins_config, project_config):
            scatter = ax.scatter(
                subset[x_axis],
                subset[y_axis],
                label=label,
                alpha=scatter_alpha,
                color=bin_style['color'],
                marker=bin_style['marker'],
                s=scatter_size
            )
            _attach_point_metadata(fig, scatter, subset, x_axis, y_axis, None, x_label, y_label, None)

        ax.legend(loc=legend_loc, framealpha=0.9)
    else:
        scatter = ax.scatter(df[x_axis], df[y_axis], alpha=scatter_alpha, s=scatter_size)
        _attach_point_metadata(fig, scatter, df, x_axis, y_axis, None, x_label, y_label, None)
    
    ax.set_xlabel(x_display)
    ax.set_ylabel(y_display)
    ax.set_title(f'{x_display} vs {y_display}')
    ax.grid(True, linestyle=grid_style, alpha=grid_alpha)
    fig.tight_layout()
    
    return fig


def create_custom_2d_line(df, x_axis, y_axis, x_label=None, y_label=None, bins_config=None, project_config=None):
    """Create 2D line plot with optional binning."""
    style = _extract_plot_style(project_config)
    scatter_alpha, legend_loc, grid_style, grid_alpha = (
        style['scatter_alpha'], style['legend_loc'],
        style['grid_style'], style['grid_alpha']
    )

    fig = Figure(figsize=(8, 6), dpi=100)
    ax = fig.add_subplot(111)
    fig._clickable_artists = []
    
    # Use display labels if provided, otherwise use column names
    x_display = x_label if x_label else x_axis
    y_display = y_label if y_label else y_axis
    
    # Sort by x_axis for sensible line
    df_sorted = df.sort_values(x_axis)
    
    if bins_config and bins_config['enabled']:
        for subset, bin_style, label in _prepare_bin_groups(df_sorted, bins_config, project_config, sort_by=x_axis):
            line = ax.plot(
                subset[x_axis],
                subset[y_axis],
                label=label,
                marker=bin_style['marker'],
                alpha=scatter_alpha,
                color=bin_style['color'],
                linewidth=2
            )[0]
            line.set_pickradius(5)
            _attach_point_metadata(fig, line, subset, x_axis, y_axis, None, x_label, y_label, None)

        ax.legend(loc=legend_loc, framealpha=0.9)
    else:
        line = ax.plot(df_sorted[x_axis], df_sorted[y_axis], marker='o', alpha=scatter_alpha)[0]
        line.set_pickradius(5)
        _attach_point_metadata(fig, line, df_sorted, x_axis, y_axis, None, x_label, y_label, None)
    
    ax.set_xlabel(x_display)
    ax.set_ylabel(y_display)
    ax.set_title(f'{x_display} vs {y_display} (Line)')
    ax.grid(True, linestyle=grid_style, alpha=grid_alpha)
    fig.tight_layout()
    
    return fig


def create_custom_3d_scatter(df, x_axis, y_axis, z_axis, x_label=None, y_label=None, z_label=None, bins_config=None, project_config=None):
    """Create 3D scatter plot with optional binning."""
    from mpl_toolkits.mplot3d import Axes3D
    style = _extract_plot_style(project_config)
    scatter_size, scatter_alpha, legend_loc = (
        style['scatter_size'], style['scatter_alpha'], style['legend_loc']
    )
    
    # Use display labels if provided, otherwise use column names
    x_display = x_label if x_label else x_axis
    y_display = y_label if y_label else y_axis
    z_display = z_label if z_label else z_axis
    
    fig = Figure(figsize=(10, 8), dpi=100)
    ax = fig.add_subplot(111, projection='3d')
    fig._clickable_artists = []
    
    if bins_config and bins_config['enabled']:
        for subset, bin_style, label in _prepare_bin_groups(df, bins_config, project_config):
            scatter = ax.scatter(
                subset[x_axis],
                subset[y_axis],
                subset[z_axis],
                label=label,
                alpha=scatter_alpha,
                color=bin_style['color'],
                marker=bin_style['marker'],
                s=scatter_size
            )
            _attach_point_metadata(fig, scatter, subset, x_axis, y_axis, z_axis, x_label, y_label, z_label)

        ax.legend(loc=legend_loc, framealpha=0.9)
    else:
        scatter = ax.scatter(df[x_axis], df[y_axis], df[z_axis], alpha=scatter_alpha, s=scatter_size)
        _attach_point_metadata(fig, scatter, df, x_axis, y_axis, z_axis, x_label, y_label, z_label)
    
    ax.set_xlabel(x_display)
    ax.set_ylabel(y_display)
    ax.set_zlabel(z_display)
    ax.set_title(f'3D Scatter: {x_display}, {y_display}, {z_display}')
    fig.tight_layout()
    
    return fig


def create_custom_3d_surface(df, x_axis, y_axis, z_axis, x_label=None, y_label=None, z_label=None, bins_config=None, project_config=None):
    """Create 3D surface plot using triangulation with optional binning."""
    from mpl_toolkits.mplot3d import Axes3D
    from scipy.interpolate import griddata
    from matplotlib.patches import Patch
    style = _extract_plot_style(project_config, default_alpha=0.55)
    scatter_alpha, legend_loc = style['scatter_alpha'], style['legend_loc']
    
    # Use display labels if provided, otherwise use column names
    x_display = x_label if x_label else x_axis
    y_display = y_label if y_label else y_axis
    z_display = z_label if z_label else z_axis
    
    fig = Figure(figsize=(10, 8), dpi=100)
    ax = fig.add_subplot(111, projection='3d')
    fig._clickable_artists = []
    
    if bins_config and bins_config['enabled']:
        legend_handles = []
        for subset, bin_style, label in _prepare_bin_groups(df, bins_config, project_config):
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
                    color=bin_style['color'],
                    alpha=0.35,
                    linewidth=0,
                    antialiased=True
                )

            scatter = ax.scatter(x, y, z, color=bin_style['color'], marker=bin_style['marker'], s=35, alpha=scatter_alpha)
            _attach_point_metadata(fig, scatter, subset, x_axis, y_axis, z_axis, x_label, y_label, z_label)

            legend_handles.append(
                Patch(
                    facecolor=bin_style['color'],
                    edgecolor=bin_style['color'],
                    alpha=scatter_alpha,
                    label=label
                )
            )

        if legend_handles:
            ax.legend(handles=legend_handles, loc=legend_loc, framealpha=0.9)
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
        scatter = ax.scatter(x, y, z, color='red', s=35, alpha=scatter_alpha)
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
    
    def load_binning_config(self, config_dict):
        """Load binning configuration from a dict."""
        if not config_dict:
            self.binning_enabled_var.set(False)
            return
        
        self.binning_enabled_var.set(config_dict.get('enabled', False))
        if config_dict.get('enabled'):
            self.bin_param_var.set(config_dict.get('parameter', ''))
            self.binning_mode_var.set(config_dict.get('mode', 'automatic'))
            self.current_bins = config_dict.get('bins', [])
    
    def reset(self):
        """Reset binning configuration to defaults."""
        self.binning_enabled_var.set(False)
        self.bin_param_var.set('')
        self.binning_mode_var.set('automatic')
        self.current_bins = None
        
        # Clear manual bin inputs
        for bin_data in self.bin_frames:
            bin_data['frame'].destroy()
        self.bin_frames = []
        
        # Add 1 default bin
        self._add_bin_input()


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
# PLOT TAB WRAPPER
# ============================================================================

class PlotTab(ttk.Frame):
    """Wrapper for a figure with metadata and unsaved changes tracking."""
    
    def __init__(self, parent, figure_spec=None):
        """
        Initialize plot tab.
        
        Args:
            parent: Parent widget
            figure_spec: FigureSpec associated with this tab (None for unsaved)
        """
        super().__init__(parent)
        self.figure_spec = figure_spec
        self.has_unsaved_changes = False
        self.plot_display = PlotDisplayPanel(self)
        self.plot_display.pack(fill=tk.BOTH, expand=True)


# ============================================================================
# PROJECT BROWSER PANEL
# ============================================================================

class ProjectBrowser(ttk.Frame):
    """Panel for browsing and managing figures in the current project."""
    
    def __init__(self, parent, on_figure_selected=None, on_figure_double_clicked=None, on_figure_deleted=None, on_new_figure=None):
        """
        Initialize project browser panel.
        
        Args:
            parent: Parent widget
            on_figure_selected: Callback when a figure is selected (receives FigureSpec)
            on_figure_double_clicked: Callback when a figure is double-clicked (receives FigureSpec)
            on_figure_deleted: Callback when a figure is deleted (receives figure index)
            on_new_figure: Callback when "New Figure" button is clicked
        """
        super().__init__(parent)
        self.on_figure_selected = on_figure_selected
        self.on_figure_double_clicked = on_figure_double_clicked
        self.on_figure_deleted = on_figure_deleted
        self.on_new_figure = on_new_figure
        self.figures = []  # List of FigureSpec objects
        self.selected_index = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create GUI widgets for project browser."""
        # Header frame
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(header_frame, text="Figures", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        ttk.Button(header_frame, text="+ New", command=lambda: self.on_new_figure() if self.on_new_figure else None).pack(side=tk.RIGHT, padx=2)
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.figures_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=10)
        self.figures_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.figures_listbox.yview)
        
        self.figures_listbox.bind("<<ListboxSelect>>", self._on_select)
        self.figures_listbox.bind("<Button-3>", self._on_right_click)  # Right-click context menu
        self.figures_listbox.bind("<Double-Button-1>", self._on_double_click)  # Double-click to open in tab
    
    def _on_double_click(self, event):
        """Handle double-click on figure to open in tab."""
        idx = self.figures_listbox.nearest(event.y)
        if 0 <= idx < len(self.figures):
            if self.on_figure_double_clicked:
                self.on_figure_double_clicked(self.figures[idx])


    
    def _on_select(self, event):
        """Handle figure selection."""
        selection = self.figures_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        self.selected_index = idx
        
        if self.on_figure_selected and idx < len(self.figures):
            self.on_figure_selected(self.figures[idx])
    
    def _on_right_click(self, event):
        """Handle right-click context menu."""
        # Get the item under cursor
        idx = self.figures_listbox.nearest(event.y)
        if idx < 0 or idx >= len(self.figures):
            return
        
        # Create context menu
        menu = tk.Menu(self, tearoff=False)
        menu.add_command(label="Open in Tab", command=lambda: self._open_from_menu(idx))
        menu.add_separator()
        menu.add_command(label="Delete", command=lambda: self._delete_figure_with_confirmation(idx))
        menu.post(event.x_root, event.y_root)
    
    def _open_from_menu(self, idx):
        """Open figure from context menu."""
        if 0 <= idx < len(self.figures):
            if self.on_figure_double_clicked:
                self.on_figure_double_clicked(self.figures[idx])
    
    def _delete_figure_with_confirmation(self, idx):
        """Delete figure with confirmation dialog."""
        if 0 <= idx < len(self.figures):
            import tkinter.messagebox as mb
            if mb.askyesno("Delete Figure", f"Are you sure you want to delete Figure {idx + 1}?"):
                self._delete_figure(idx)
    
    def _delete_figure(self, idx):
        """Delete figure at given index."""
        if 0 <= idx < len(self.figures):
            self.figures.pop(idx)
            self._refresh_listbox()
            if self.on_figure_deleted:
                self.on_figure_deleted(idx)
    
    def _refresh_listbox(self):
        """Refresh the listbox display."""
        self.figures_listbox.delete(0, tk.END)
        for i, fig in enumerate(self.figures):
            # Create a descriptive label: "Fig 1: X vs Y (2D Scatter)"
            x_name = fig.x_variable or '?'
            y_name = fig.y_variable or '?'
            # Format plot_representation from e.g. '2d_scatter' to '2D Scatter'
            rep = fig.plot_representation.replace('_', ' ').title() if fig.plot_representation else 'Plot'
            label = f"Fig {i+1}: {x_name} vs {y_name} ({rep})"
            self.figures_listbox.insert(tk.END, label)
    
    def set_figures(self, figures):
        """Update the figures list."""
        self.figures = list(figures)
        self._refresh_listbox()
    
    def add_figure(self, figure_spec):
        """Add a new figure to the list."""
        self.figures.append(figure_spec)
        self._refresh_listbox()


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class VisualisierApp(tk.Tk):
    """Main application window."""
    
    def __init__(self):
        """Initialize the application."""
        super().__init__()
        self.title("Rib Analyser")
        self.geometry("1400x900")
        
        # Data
        self.df = None
        self.data_file = None
        self.selected_papers = []
        self.all_papers = []
        self.axis_mapping = {}  # Maps display names to actual column names or symbols
        self.project = ProjectState.blank()
        self.project_config = {}  # Project-local style config loaded from config.py
        
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
        edit_menu.add_command(label="Export Figures", command=lambda: self._save_plot())
        
        view_menu = tk.Menu(menu_bar, tearoff=0)
        view_menu.add_command(label="Plot Properties", command=lambda: self._open_view_config())

        menu_bar.add_cascade(label="File", menu=file_menu)
        menu_bar.add_cascade(label="Edit", menu=edit_menu)
        menu_bar.add_cascade(label="View", menu=view_menu)
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
        ttk.Button(row5, text="Save to Project", command=lambda: self._save_figure_to_project()).pack(side=tk.LEFT, padx=5)
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
        
        # ====== CONTENT AREA (SPLIT VIEW: BROWSER + TABS) ======
        split_view = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        split_view.pack(fill=tk.BOTH, expand=True, padx=0, pady=(5, 0))
        
        # LEFT: Project Browser
        self.project_browser = ProjectBrowser(
            split_view,
            on_figure_selected=lambda fig: self._on_figure_selected_from_browser(fig),
            on_figure_double_clicked=lambda fig: self._open_figure_in_tab(fig),
            on_figure_deleted=lambda idx: self._on_figure_deleted(idx),
            on_new_figure=lambda: self._on_new_figure_clicked()
        )
        split_view.add(self.project_browser, weight=0)  # Fixed width for browser
        
        # RIGHT: Notebook with figure tabs + plot display
        self.figure_notebook = ttk.Notebook(split_view)
        split_view.add(self.figure_notebook, weight=1)  # Expandable plot area
        
        # Create a tab for the plot display
        plot_tab = ttk.Frame(self.figure_notebook)
        self.figure_notebook.add(plot_tab, text="Plot Display")
        
        # Add plot display to the tab
        self.plot_display = PlotDisplayPanel(plot_tab)
        self.plot_display.pack(fill=tk.BOTH, expand=True)

        # Bind tab close via middle-click
        self.figure_notebook.bind('<Button-2>', self._on_tab_middle_click)
    
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

    def _build_axis_list(self, papers):
        """Build input/output variables list and update dropdowns."""
        input_vars = [
            'Reynolds number (Re)',
            'P/e',
            'e/D',
            'Alpha',
            'Aspect ratio',
            'Number of ribbed walls'
        ]

        output_vars = data_loader.get_available_symbols(self.df, papers)

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
        
        return input_vars

    def _refresh_axis_dropdowns(self):
        """Refresh axis dropdowns based on currently selected papers."""
        papers_for_symbols = self.selected_papers if self.selected_papers else self.all_papers
        self._build_axis_list(papers_for_symbols)
    
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
        
        # Copy default config to project
        try:
            copy_default_config_to_project(project_root)
        except Exception as e:
            messagebox.showwarning("Config Copy", f"Warning: Could not copy default config:\n{str(e)}")

        self.project = ProjectState(
            name=sanitize_project_name(project_name),
            root_dir=project_root,
            data_dir=data_dir,
            project_file=project_file,
        )
        # Load the freshly copied config
        self._load_project_config()
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
            # Load project-local config if it exists
            self._load_project_config()
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
        # Also persist project config
        self._save_project_config()
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
        # Also persist project config
        self._save_project_config()
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


    def _sync_project_from_ui(self):
        """Store the current UI state into the project model.

        Preserves the existing figures list (managed by Save to Project /
        browser delete).  Only syncs paper selection and available papers.
        """
        self.project.selected_papers = list(self.selected_papers)
        self.project.available_papers = list(self.all_papers)
        # NOTE: figures list is NOT overwritten here; it is managed by
        # _save_figure_to_project / browser delete.

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

            input_vars = self._build_axis_list(self.all_papers)
            self.binning_panel.set_dataframe(self.df)
            self.binning_panel.set_available_parameters(input_vars)
            self.binning_panel.set_selected_papers(self.selected_papers)
            self.paper_dropdown['values'] = self.all_papers

            if self.selected_papers:
                self._update_selected_papers_display_listbox()
                self._refresh_axis_dropdowns()
            
            # Load figures from project into the browser
            if self.project.figures:
                self.project_browser.set_figures(self.project.figures)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to reload project data:\n{str(e)}")

    # (duplicate _perform_import removed — kept only the version near line 1969)

    def _on_config_change(self):
        """Handle configuration changes."""
        # Could enable/disable generate button based on validation
        pass

    def _on_bins_set(self):
        """Callback when bins are set in binning panel."""
        pass

    def _build_plot(self, papers, x_disp, y_disp, z_disp, plot_type, plot_mode, bins_config, show_warnings=True):
        """Core pipeline to filter data, resolve axes, and dispatch plot creation."""
        if self.df is None or not papers:
            if show_warnings: messagebox.showwarning("Missing Data", "No data or papers selected.")
            return None

        filtered_df = self.df[self.df['Paper Title'].isin(papers)].copy()

        # Resolve axes
        x_col, x_sym = self._resolve_axis(x_disp)
        y_col, y_sym = self._resolve_axis(y_disp)
        z_col, z_sym = self._resolve_axis(z_disp) if z_disp else (None, False)

        if not x_col or not y_col:
            if show_warnings: messagebox.showwarning("Invalid Axis", "Please select valid X and Y axes.")
            return None
        if plot_type == '3d' and not z_col:
            if show_warnings: messagebox.showwarning("Invalid Axis", "Please select valid Z axis for 3D plots.")
            return None

        # Prepare labels
        def get_label(disp, col):
            return disp if disp and disp not in [' ', '─────────────────', 'INPUT VARIABLES:', 'OUTPUT VARIABLES:'] else col
        x_label = get_label(x_disp, x_col)
        y_label = get_label(y_disp, y_col)
        z_label = get_label(z_disp, z_col) if z_col else None

        if x_sym:
            filtered_df = filtered_df[filtered_df['Variable'] == x_col].copy()
            x_col = 'Value'
        if y_sym:
            filtered_df = filtered_df[filtered_df['Variable'] == y_col].copy()
            y_col = 'Value'
        if z_col and z_sym:
            filtered_df = filtered_df[filtered_df['Variable'] == z_col].copy()
            z_col = 'Value'

        if filtered_df.empty:
            if show_warnings: messagebox.showwarning("No Data", "No data available after filtering.")
            return None

        axis_cols = [x_col, y_col]
        if z_col:
            axis_cols.append(z_col)
        filtered_df = filtered_df.dropna(subset=axis_cols, how='any')

        if filtered_df.empty:
            if show_warnings: messagebox.showwarning("No Valid Data", "No valid numeric data available.")
            return None

        pc = self.project_config or None
        if plot_type == '2d':
            if plot_mode == 'scatter':
                return create_custom_2d_scatter(filtered_df, x_col, y_col, x_label, y_label, bins_config, pc)
            else:
                return create_custom_2d_line(filtered_df, x_col, y_col, x_label, y_label, bins_config, pc)
        else:
            if plot_mode == 'scatter':
                return create_custom_3d_scatter(filtered_df, x_col, y_col, z_col, x_label, y_label, z_label, bins_config, pc)
            else:
                return create_custom_3d_surface(filtered_df, x_col, y_col, z_col, x_label, y_label, z_label, bins_config, pc)

    def _generate_plot(self):
        """Generate plot based on current configuration."""
        try:
            fig = self._build_plot(
                self.selected_papers,
                self.x_axis_var.get(),
                self.y_axis_var.get(),
                self.z_axis_var.get(),
                self.plot_type_var.get(),
                self.plot_mode_var.get(),
                self.binning_panel.get_bins_config(),
                show_warnings=True
            )
            if fig:
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
                return mapping[1], True
            return mapping, False

        return axis_display, False

    def _on_figure_selected_from_browser(self, figure_spec):
        """Handle figure selection from the project browser."""
        # Load the figure's configuration into the UI
        if figure_spec.papers_included:
            self.selected_papers = figure_spec.papers_included
            self._update_selected_papers_display_listbox()
            self.binning_panel.set_selected_papers(self.selected_papers)
        
        # Set plot type and mode
        plot_type, plot_mode = figure_spec.plot_representation.split('_')
        self.plot_type_var.set(plot_type)
        self.plot_mode_var.set(plot_mode)
        self._on_plot_type_change()
        
        # Set axes
        if figure_spec.x_variable:
            self.x_axis_var.set(figure_spec.x_variable)
        if figure_spec.y_variable:
            self.y_axis_var.set(figure_spec.y_variable)
        if figure_spec.z_variable:
            self.z_axis_var.set(figure_spec.z_variable)
        
        # Load binning data if present
        if figure_spec.binning_data:
            self.binning_panel.load_binning_config(figure_spec.binning_data)
    
    def _on_figure_deleted(self, index):
        """Handle figure deletion from the browser."""
        # Update project state
        if self.project and 0 <= index < len(self.project.figures):
            self.project.figures.pop(index)
            self.project.dirty = True
    
    def _on_new_figure_clicked(self):
        """Handle new figure button click."""
        # Clear the current selection to start fresh
        self.selected_papers = []
        self._update_selected_papers_display_listbox()
        self.plot_type_var.set("2d")
        self.plot_mode_var.set("scatter")
        self._on_plot_type_change()
        self.x_axis_var.set("")
        self.y_axis_var.set("")
        self.z_axis_var.set("")
        self.binning_panel.reset()
        self.plot_display.clear_plot()
        messagebox.showinfo("New Figure", "Configure your figure using the controls above, then click 'Generate Plot'")
    
    def _save_current_figure(self):
        """Build a FigureSpec from the current UI state (does NOT add to project)."""
        return self._build_active_figure_spec()
    
    def _regenerate_figure_from_spec(self, figure_spec):
        """Regenerate a matplotlib Figure from a FigureSpec.

        Handles symbol-based output variables correctly by filtering the
        dataframe before passing to plot functions.
        """
        parts = figure_spec.plot_representation.split('_', 1)
        plot_type = parts[0] if len(parts) > 0 else '2d'
        plot_mode = parts[1] if len(parts) > 1 else 'scatter'
        bins_config = figure_spec.binning_data if figure_spec.binning_data else None

        return self._build_plot(
            figure_spec.papers_included,
            figure_spec.x_variable,
            figure_spec.y_variable,
            figure_spec.z_variable,
            plot_type, plot_mode, bins_config, show_warnings=False
        )

    def _open_figure_in_tab(self, figure_spec):
        """Open a figure in a new tab based on its FigureSpec."""
        tab = PlotTab(self.figure_notebook, figure_spec=figure_spec)
        tab_index = self.figure_notebook.index("end")

        # Build descriptive tab name
        x_name = figure_spec.x_variable or '?'
        y_name = figure_spec.y_variable or '?'
        tab_name = f"{x_name} vs {y_name}"
        self.figure_notebook.add(tab, text=tab_name)

        # Load the figure configuration into the UI controls
        self._on_figure_selected_from_browser(figure_spec)

        # Regenerate and display in the tab
        try:
            fig = self._regenerate_figure_from_spec(figure_spec)
            if fig is None:
                messagebox.showwarning("No Data", "Could not regenerate figure (no matching data).")
                self.figure_notebook.forget(tab_index)
                return

            tab.plot_display.display_plot(fig)
            self.figure_notebook.select(tab_index)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open figure:\n{str(e)}")
            try:
                self.figure_notebook.forget(tab_index)
            except Exception:
                pass

    def _save_figure_to_project(self):
        """Save the current figure to the project and create a tab for it."""
        if not self.project or not self.project.is_loaded():
            messagebox.showwarning("No Project", "Please open or create a project first.")
            return

        if not self.plot_display.current_fig:
            messagebox.showwarning("No Plot", "Generate a plot first before saving.")
            return

        # Build the FigureSpec and add it to the project
        figure_spec = self._save_current_figure()
        self.project.figures.append(figure_spec)
        self.project.dirty = True
        self.project_browser.set_figures(self.project.figures)

        # Open the figure in a new tab
        try:
            self._open_figure_in_tab(figure_spec)
            messagebox.showinfo("Success", "Figure saved to project and opened in a new tab.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save figure:\n{str(e)}")

    def _on_tab_middle_click(self, event):
        """Handle middle-click on a notebook tab to close it."""
        try:
            clicked_tab = self.figure_notebook.identify(event.x, event.y)
            if not clicked_tab:
                return
            tab_index = self.figure_notebook.index(f"@{event.x},{event.y}")
        except Exception:
            return

        # Never close the first "Plot Display" tab
        if tab_index == 0:
            return

        tab_widget = self.figure_notebook.nametowidget(self.figure_notebook.tabs()[tab_index])
        if isinstance(tab_widget, PlotTab) and tab_widget.has_unsaved_changes:
            if not messagebox.askyesno("Close Tab", "This tab has unsaved changes. Close anyway?"):
                return

        self.figure_notebook.forget(tab_index)

    def _load_project_config(self):
        """Load the project-local config file into self.project_config."""
        if not self.project.is_loaded():
            self.project_config = {}
            return

        config_path = self.project.get_config_file_path()
        if config_path and config_path.exists():
            try:
                self.project_config = load_project_config(config_path)
            except Exception:
                self.project_config = {}
        else:
            self.project_config = {}

    def _save_project_config(self):
        """Persist the current project_config dict to the project-local config file."""
        if not self.project.is_loaded() or not self.project_config:
            return

        config_path = self.project.get_config_file_path()
        if config_path:
            try:
                save_project_config(config_path, self.project_config)
            except Exception:
                pass  # non-fatal

    def _open_view_config(self):
        """Open the View/Plot Properties configuration dialog."""
        PlotPropertiesDialog(
            self,
            project=self.project if self.project.is_loaded() else None,
            on_apply=self._on_view_config_applied,
        )

    def _on_view_config_applied(self, config_dict):
        """Called when the user clicks Apply in the Plot Properties dialog."""
        self.project_config = config_dict
        # Regenerate the current plot if one exists
        if self.plot_display.current_fig:
            self._generate_plot()


# ============================================================================
# PLOT PROPERTIES DIALOG
# ============================================================================

class PlotPropertiesDialog(tk.Toplevel):
    """Dialog for configuring plot styling properties."""
    
    def __init__(self, parent, project=None, on_apply=None):
        """
        Initialize plot properties dialog.
        
        Args:
            parent: Parent window
            project: ProjectState object (None if no project loaded)
            on_apply: Callback receiving the updated config dict on Apply
        """
        super().__init__(parent)
        self.title("Plot Properties")
        self.geometry("400x500")
        self.project = project
        self.on_apply = on_apply
        self.config_dict = {}
        
        # Load config from project if available
        if project and project.is_loaded():
            config_path = project.get_config_file_path()
            if config_path and config_path.exists():
                try:
                    self.config_dict = load_project_config(config_path)
                except Exception as e:
                    messagebox.showwarning("Config Load", f"Could not load project config:\n{str(e)}")
                    self.config_dict = self._get_default_config()
            else:
                self.config_dict = self._get_default_config()
        else:
            self.config_dict = self._get_default_config()
        
        self._create_widgets()
    
    def _get_default_config(self):
        """Get default plot configuration."""
        from ribs_core import config as default_config
        return {
            "MARKERS": getattr(default_config, "MARKERS", []),
            "SEABORN_PALETTE": getattr(default_config, "SEABORN_PALETTE", "husl"),
            "N_COLORS": getattr(default_config, "N_COLORS", 12),
            "SCATTER_SIZE": getattr(default_config, "SCATTER_SIZE", 80),
            "SCATTER_ALPHA": getattr(default_config, "SCATTER_ALPHA", 0.7),
            "LEGEND_LOCATION": getattr(default_config, "LEGEND_LOCATION", "best"),
            "GRID_STYLE": getattr(default_config, "GRID_STYLE", "--"),
            "GRID_ALPHA": getattr(default_config, "GRID_ALPHA", 0.3),
            "OUTPUT_DPI": getattr(default_config, "OUTPUT_DPI", 300),
        }
    
    def _create_widgets(self):
        """Create dialog widgets."""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(main_frame, text="Plot Style Configuration", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        # Notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Markers tab
        markers_frame = ttk.Frame(notebook, padding=10)
        notebook.add(markers_frame, text="Markers")
        
        ttk.Label(markers_frame, text="Marker Symbol:", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.marker_var = tk.StringVar(value=str(self.config_dict.get("MARKERS", ["o"])[0]))
        marker_combo = ttk.Combobox(markers_frame, textvariable=self.marker_var, 
                                     values=self.config_dict.get("MARKERS", ["o", "s", "^", "D", "v"]),
                                     state="readonly", width=30)
        marker_combo.pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(markers_frame, text="Marker Size:", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.size_var = tk.StringVar(value=str(self.config_dict.get("SCATTER_SIZE", 80)))
        ttk.Spinbox(markers_frame, from_=10, to=200, textvariable=self.size_var, width=10).pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(markers_frame, text="Marker Opacity (0.0-1.0):", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.alpha_var = tk.StringVar(value=str(self.config_dict.get("SCATTER_ALPHA", 0.7)))
        ttk.Spinbox(markers_frame, from_=0.0, to=1.0, increment=0.1, textvariable=self.alpha_var, width=10).pack(anchor=tk.W, pady=(0, 10))
        
        # Lines tab
        lines_frame = ttk.Frame(notebook, padding=10)
        notebook.add(lines_frame, text="Lines")

        ttk.Label(lines_frame, text="Grid Style:", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.grid_style_var = tk.StringVar(value=self.config_dict.get("GRID_STYLE", "--"))
        ttk.Combobox(lines_frame, textvariable=self.grid_style_var,
                     values=["--", ":", "-", "-."],
                     state="readonly", width=10).pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(lines_frame, text="Grid Opacity (0.0-1.0):", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.grid_alpha_var = tk.StringVar(value=str(self.config_dict.get("GRID_ALPHA", 0.3)))
        ttk.Spinbox(lines_frame, from_=0.0, to=1.0, increment=0.1, textvariable=self.grid_alpha_var, width=10).pack(anchor=tk.W, pady=(0, 10))

        # Colors tab
        colors_frame = ttk.Frame(notebook, padding=10)
        notebook.add(colors_frame, text="Colors")
        
        ttk.Label(colors_frame, text="Color Palette:", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.palette_var = tk.StringVar(value=self.config_dict.get("SEABORN_PALETTE", "husl"))
        palette_combo = ttk.Combobox(colors_frame, textvariable=self.palette_var,
                                     values=["husl", "Set1", "Set2", "viridis", "plasma", "coolwarm"],
                                     state="readonly", width=30)
        palette_combo.pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(colors_frame, text="Number of Colors:", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.n_colors_var = tk.StringVar(value=str(self.config_dict.get("N_COLORS", 12)))
        ttk.Spinbox(colors_frame, from_=5, to=30, textvariable=self.n_colors_var, width=10).pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(colors_frame, text="Legend Location:", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.legend_var = tk.StringVar(value=self.config_dict.get("LEGEND_LOCATION", "best"))
        legend_combo = ttk.Combobox(colors_frame, textvariable=self.legend_var,
                                    values=["best", "upper left", "upper right", "lower left", "lower right"],
                                    state="readonly", width=30)
        legend_combo.pack(anchor=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Apply", command=self._apply_config).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Reset to Defaults", command=self._reset_to_defaults).pack(side=tk.LEFT)
    
    def _build_config_dict(self):
        """Build a config dict from the current widget values."""
        return {
            "MARKERS": self.config_dict.get("MARKERS", []),
            "SEABORN_PALETTE": self.palette_var.get(),
            "N_COLORS": int(self.n_colors_var.get()),
            "SCATTER_SIZE": int(self.size_var.get()),
            "SCATTER_ALPHA": float(self.alpha_var.get()),
            "LEGEND_LOCATION": self.legend_var.get(),
            "GRID_STYLE": self.grid_style_var.get(),
            "GRID_ALPHA": float(self.grid_alpha_var.get()),
            "OUTPUT_DPI": self.config_dict.get("OUTPUT_DPI", 300),
        }

    def _apply_config(self):
        """Save the current configuration and notify the parent."""
        updated_config = self._build_config_dict()
        
        if self.project and self.project.is_loaded():
            config_path = self.project.get_config_file_path()
            if config_path:
                try:
                    save_project_config(config_path, updated_config)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save config:\n{str(e)}")
                    return

        # Notify the parent app so it can update plots
        if self.on_apply:
            self.on_apply(updated_config)

        messagebox.showinfo("Success", "Plot properties applied.")
        self.destroy()

    def _reset_to_defaults(self):
        """Reset all fields to the global defaults from ribs_core/config.py."""
        defaults = self._get_default_config()
        markers = defaults.get("MARKERS", ["o"])
        self.marker_var.set(str(markers[0]) if markers else "o")
        self.size_var.set(str(defaults.get("SCATTER_SIZE", 80)))
        self.alpha_var.set(str(defaults.get("SCATTER_ALPHA", 0.7)))
        self.palette_var.set(defaults.get("SEABORN_PALETTE", "husl"))
        self.n_colors_var.set(str(defaults.get("N_COLORS", 12)))
        self.legend_var.set(defaults.get("LEGEND_LOCATION", "best"))
        self.grid_style_var.set(defaults.get("GRID_STYLE", "--"))
        self.grid_alpha_var.set(str(defaults.get("GRID_ALPHA", 0.3)))
        self.config_dict = defaults


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


def main():
    """Main entry point."""
    app = VisualisierApp()
    app.mainloop()


if __name__ == "__main__":
    main()
