"""
GUI Module for Exploratory Data Visualiser

Provides interactive Tkinter interface with 4 main panels:
- MultiPaperSelector: Select papers and merge data
- AxisConfigPanel: Configure plot axes and type
- BinningPanel: Configure binning parameters
- PlotDisplayPanel: Display and save plots
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add parent directory to path for ribs_core imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ribs_core import data_loader
from ribs_core.config import MARKERS

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
    """
    Validate that bins are continuous, ordered, and non-overlapping.
    
    Args:
        bins: List of bin dicts with 'lower', 'upper', 'bin_number' keys
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not bins or len(bins) == 0:
        return False, "No bins defined"
    
    # Sort by lower bound
    sorted_bins = sorted(bins, key=lambda x: x['lower'])
    
    # Check ordering
    for i, bin_dict in enumerate(sorted_bins):
        if bin_dict['lower'] >= bin_dict['upper']:
            return False, f"Bin {bin_dict['bin_number']}: Lower bound must be less than upper bound"
    
    # Check continuity (upper of one bin should equal or connect to lower of next)
    for i in range(len(sorted_bins) - 1):
        current_upper = sorted_bins[i]['upper']
        next_lower = sorted_bins[i + 1]['lower']
        if current_upper != next_lower:
            return False, f"Bins are not continuous: Bin {sorted_bins[i]['bin_number']} ends at {current_upper}, but Bin {sorted_bins[i + 1]['bin_number']} starts at {next_lower}"
    
    return True, ""


def assign_points_to_bins(df, param_col, bins):
    """
    Assign bin numbers to data points based on parameter values.
    
    Args:
        df: DataFrame
        param_col: Column name containing parameter values
        bins: List of bin dicts with 'lower', 'upper', 'bin_number' keys
    
    Returns:
        Series with bin numbers for each row
    """
    bin_assignment = np.zeros(len(df), dtype=int)
    
    for idx, row in df.iterrows():
        value = row[param_col]
        if pd.isna(value):
            bin_assignment[idx] = -1  # No bin for NaN
            continue
        
        for bin_dict in bins:
            lower = bin_dict['lower']
            upper = bin_dict['upper']
            bin_num = bin_dict['bin_number']
            
            # Check if value falls in this bin (inclusive on both ends for last bin)
            if lower <= value <= upper:
                bin_assignment[idx] = bin_num
                break
    
    return bin_assignment


def get_bin_colors_symbols(n_bins):
    """
    Get colors and symbols from config for binning visualization.
    
    Args:
        n_bins: Number of bins needed
    
    Returns:
        Dict mapping bin_number -> {'color': color, 'marker': marker}
    """
    colors_list = list(COLORS.values())
    markers_list = MARKERS.copy()
    
    bin_styles = {}
    for i in range(n_bins):
        bin_num = i + 1
        color = colors_list[i % len(colors_list)]
        marker = markers_list[i % len(markers_list)]
        bin_styles[bin_num] = {'color': color, 'marker': marker}
    
    return bin_styles


# ============================================================================
# OLD CODE REMOVED - apply_custom_binning() deleted
# ============================================================================


def create_custom_2d_scatter(df, x_axis, y_axis, x_label=None, y_label=None, bins_config=None):
    """Create 2D scatter plot with optional binning."""
    fig = Figure(figsize=(8, 6), dpi=100)
    ax = fig.add_subplot(111)
    
    # Use display labels if provided, otherwise use column names
    x_display = x_label if x_label else x_axis
    y_display = y_label if y_label else y_axis
    
    if bins_config and bins_config['enabled']:
        # Apply binning
        bin_assignment = assign_points_to_bins(df, bins_config['parameter'], bins_config['bins'])
        bin_styles = get_bin_colors_symbols(len(bins_config['bins']))
        
        # Plot each bin with its color and symbol
        for bin_dict in bins_config['bins']:
            bin_num = bin_dict['bin_number']
            mask = bin_assignment == bin_num
            if mask.any():
                style = bin_styles[bin_num]
                ax.scatter(df[mask][x_axis], df[mask][y_axis], 
                          label=f"Bin {bin_num}", alpha=0.6, 
                          color=style['color'], marker=style['marker'], s=100)
        
        ax.legend(loc='best', framealpha=0.9)
    else:
        # No binning
        ax.scatter(df[x_axis], df[y_axis], alpha=0.6)
    
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
    
    # Use display labels if provided, otherwise use column names
    x_display = x_label if x_label else x_axis
    y_display = y_label if y_label else y_axis
    
    # Sort by x_axis for sensible line
    df_sorted = df.sort_values(x_axis)
    
    if bins_config and bins_config['enabled']:
        # Apply binning
        bin_assignment = assign_points_to_bins(df_sorted, bins_config['parameter'], bins_config['bins'])
        bin_styles = get_bin_colors_symbols(len(bins_config['bins']))
        
        # Plot each bin with its color and symbol
        for bin_dict in bins_config['bins']:
            bin_num = bin_dict['bin_number']
            mask = bin_assignment == bin_num
            if mask.any():
                style = bin_styles[bin_num]
                subset = df_sorted[mask].sort_values(x_axis)
                ax.plot(subset[x_axis], subset[y_axis], 
                       label=f"Bin {bin_num}", marker=style['marker'], alpha=0.6, 
                       color=style['color'], linewidth=2)
        
        ax.legend(loc='best', framealpha=0.9)
    else:
        # No binning
        ax.plot(df_sorted[x_axis], df_sorted[y_axis], marker='o', alpha=0.6)
    
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
    
    if bins_config and bins_config['enabled']:
        # Apply binning
        bin_assignment = assign_points_to_bins(df, bins_config['parameter'], bins_config['bins'])
        bin_styles = get_bin_colors_symbols(len(bins_config['bins']))
        
        # Plot each bin with its color and symbol
        for bin_dict in bins_config['bins']:
            bin_num = bin_dict['bin_number']
            mask = bin_assignment == bin_num
            if mask.any():
                style = bin_styles[bin_num]
                ax.scatter(df[mask][x_axis], df[mask][y_axis], df[mask][z_axis],
                          label=f"Bin {bin_num}", alpha=0.6, 
                          color=style['color'], marker=style['marker'], s=100)
        
        ax.legend(loc='best', framealpha=0.9)
    else:
        # No binning
        ax.scatter(df[x_axis], df[y_axis], df[z_axis], alpha=0.6)
    
    ax.set_xlabel(x_display)
    ax.set_ylabel(y_display)
    ax.set_zlabel(z_display)
    ax.set_title(f'3D Scatter: {x_display}, {y_display}, {z_display}')
    fig.tight_layout()
    
    return fig


def create_custom_3d_surface(df, x_axis, y_axis, z_axis, x_label=None, y_label=None, z_label=None):
    """Create 3D surface plot using triangulation."""
    from mpl_toolkits.mplot3d import Axes3D
    from scipy.interpolate import griddata
    
    # Use display labels if provided, otherwise use column names
    x_display = x_label if x_label else x_axis
    y_display = y_label if y_label else y_axis
    z_display = z_label if z_label else z_axis
    
    fig = Figure(figsize=(10, 8), dpi=100)
    ax = fig.add_subplot(111, projection='3d')
    
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
    ax.scatter(x, y, z, color='red', s=50, alpha=0.5)
    
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
        # Paper is selected from dropdown, user can add it with the Add button
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
        """Initialize binning configuration panel."""
        super().__init__(parent)
        self.on_bins_set = on_bins_set
        self.df = None
        self.current_bins = None  # Stores validated bins
        self.bin_frames = []  # Store bin input frames for manual mode
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create GUI widgets for binning configuration."""
        # Title
        title = ttk.Label(self, text="Binning Configuration", font=("Arial", 10, "bold"))
        title.pack(pady=5)
        
        # Enable binning checkbox
        self.binning_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self, text="Enable Binning", 
                       variable=self.binning_enabled_var,
                       command=self._on_binning_toggle).pack(anchor=tk.W, padx=5, pady=5)
        
        # Binning options frame
        self.frame_options = ttk.LabelFrame(self, text="Binning Options", padding=5)
        self.frame_options.pack(fill=tk.X, padx=5, pady=5)
        
        # Parameter selection
        ttk.Label(self.frame_options, text="Bin Parameter:").pack(anchor=tk.W, pady=3)
        self.bin_param_var = tk.StringVar()
        self.bin_param_dropdown = ttk.Combobox(self.frame_options, 
                                               textvariable=self.bin_param_var,
                                               state="disabled", width=25)
        self.bin_param_dropdown.pack(fill=tk.X, padx=5, pady=3)
        self.bin_param_dropdown.bind("<<ComboboxSelected>>", self._on_param_selected)
        
        # Binning mode selection
        ttk.Label(self.frame_options, text="Binning Mode:").pack(anchor=tk.W, pady=(10, 3))
        self.binning_mode_var = tk.StringVar(value="automatic")
        ttk.Radiobutton(self.frame_options, text="Automatic (one bin per unique value)", 
                       variable=self.binning_mode_var, value="automatic", 
                       state=tk.DISABLED, command=self._on_mode_changed).pack(anchor=tk.W, padx=20)
        ttk.Radiobutton(self.frame_options, text="Manual (define bin bounds)", 
                       variable=self.binning_mode_var, value="manual", 
                       state=tk.DISABLED, command=self._on_mode_changed).pack(anchor=tk.W, padx=20)
        
        # Container for mode-specific widgets
        self.mode_frame = ttk.Frame(self.frame_options)
        self.mode_frame.pack(fill=tk.X, padx=20, pady=5)
        
        # Automatic mode info frame
        self.auto_frame = ttk.Frame(self.mode_frame)
        ttk.Label(self.auto_frame, text="Unique values will be used as bins").pack(anchor=tk.W)
        
        # Manual mode frame (initially hidden)
        self.manual_frame = ttk.Frame(self.mode_frame)
        self.manual_canvas = tk.Canvas(self.manual_frame, bg='white', highlightthickness=0)
        self.manual_scrollbar = ttk.Scrollbar(self.manual_frame, orient='vertical', command=self.manual_canvas.yview)
        self.manual_scrollable_frame = ttk.Frame(self.manual_canvas)
        
        self.manual_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.manual_canvas.configure(scrollregion=self.manual_canvas.bbox("all"))
        )
        
        self.manual_canvas.create_window((0, 0), window=self.manual_scrollable_frame, anchor="nw")
        self.manual_canvas.configure(yscrollcommand=self.manual_scrollbar.set)
        
        # Set Bins button
        ttk.Button(self.frame_options, text="Set Bins", command=self._on_set_bins).pack(pady=5)
        
        # Validation message frame
        self.validation_frame = ttk.Frame(self.frame_options)
        self.validation_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.validation_label = ttk.Label(self.validation_frame, text="", foreground="red")
        self.validation_label.pack(anchor=tk.W)
    
    def _on_binning_toggle(self):
        """Handle binning enable/disable toggle."""
        is_enabled = self.binning_enabled_var.get()
        new_state = tk.NORMAL if is_enabled else tk.DISABLED
        
        self.bin_param_dropdown.config(state="readonly" if is_enabled else tk.DISABLED)
        
        # Enable/disable mode selection
        for widget in self.frame_options.winfo_children():
            if isinstance(widget, ttk.Radiobutton):
                widget.config(state=new_state)
    
    def _on_param_selected(self, event=None):
        """Handle parameter selection - show automatic mode info for now."""
        self.auto_frame.pack(fill=tk.X)
        if self.manual_frame.winfo_ismapped():
            self.manual_frame.pack_forget()
        self.validation_label.config(text="")
    
    def _on_mode_changed(self):
        """Handle mode change between automatic and manual."""
        mode = self.binning_mode_var.get()
        
        if mode == "automatic":
            self.auto_frame.pack(fill=tk.X)
            if self.manual_frame.winfo_ismapped():
                self.manual_frame.pack_forget()
        else:  # manual
            self.auto_frame.pack_forget()
            self._create_manual_bin_inputs()
            self.manual_frame.pack(fill=tk.BOTH, expand=True)
        
        self.validation_label.config(text="")
    
    def _create_manual_bin_inputs(self):
        """Create input fields for manual bin definition."""
        # Clear previous inputs
        for frame in self.bin_frames:
            frame.destroy()
        self.bin_frames = []
        
        # Add 4 default bins (user can add more later - TODO)
        for i in range(4):
            bin_frame = ttk.Frame(self.manual_scrollable_frame, relief=tk.SUNKEN, borderwidth=1)
            bin_frame.pack(fill=tk.X, padx=5, pady=3)
            
            ttk.Label(bin_frame, text=f"Bin {i+1}:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
            
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
                'bin_number': i + 1,
                'lower_var': lower_var,
                'upper_var': upper_var
            })
        
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
        """Create automatic bins from unique values."""
        if self.df is None or param not in self.df.columns:
            self.validation_label.config(text="Error: Parameter not found in data", foreground="red")
            return
        
        unique_values = sorted(self.df[param].dropna().unique().tolist())
        
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
    """Panel for displaying plots and save/clear buttons."""
    
    def __init__(self, parent):
        """
        Initialize plot display panel.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.current_fig = None
        self.canvas = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create GUI widgets for plot display."""
        # Canvas frame
        self.canvas_frame = ttk.Frame(self)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def display_plot(self, fig):
        """Display a matplotlib figure."""
        self.current_fig = fig
        
        # Clear previous canvas
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
        
        # Create new canvas
        self.canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def clear_plot(self):
        """Clear the displayed plot."""
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None
        self.current_fig = None
    
    def _on_generate_click(self):
        """Handle generate plot button click."""
        # This will be called by the main app
        pass
    
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
        
        # Find data file
        self._find_data_file()
        
        # Create main layout
        self._create_layout()
        
        # Load initial data
        self._load_initial_data()
    
    def _find_data_file(self):
        """Find the research data file (clean_data_master.csv from preprocessing pipeline)."""
        # Try to find clean_data_master.csv in Staging directory (preprocessor output)
        workspace_root = Path(__file__).parent.parent.parent
        
        # Primary: Look for clean_data_master.csv in Staging directory
        staging_dir = workspace_root / "Staging"
        master_file = staging_dir / "clean_data_master.csv"
        
        if master_file.exists():
            self.data_file = str(master_file)
            return
        
        # Fallback: Look for any CSV file in Staging directory
        if staging_dir.exists():
            csv_files = list(staging_dir.glob("clean_data*.csv"))
            if csv_files:
                # Sort to get the master file first if it exists
                csv_files = sorted(csv_files, key=lambda x: (x.name != "clean_data_master.csv", x.name))
                self.data_file = str(csv_files[0])
                return
    
    def _create_layout(self):
        """Create the main application layout with ribbon toolbar."""
        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # ====== RIBBON TOOLBAR (TOP) ======
        ribbon = ttk.LabelFrame(main_frame, text="Controls", padding=10)
        ribbon.pack(fill=tk.X, padx=0, pady=(0, 10))
        
        # Create a container for left controls and right selected papers list
        ribbon_container = ttk.Frame(ribbon)
        ribbon_container.pack(fill=tk.BOTH, expand=True)
        
        # Configure columns for equal widths
        ribbon_container.columnconfigure(0, weight=1, minsize=200)  # Left panel
        ribbon_container.columnconfigure(1, weight=1, minsize=200)  # Right panel
        ribbon_container.rowconfigure(0, weight=1)
        
        # LEFT SIDE: All controls
        left_side = ttk.Frame(ribbon_container)
        left_side.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
        # Row 1: Paper Selection
        row1 = ttk.Frame(left_side)
        row1.pack(fill=tk.X, pady=5)
        
        ttk.Label(row1, text="Papers:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        self.paper_var = tk.StringVar()
        self.paper_dropdown = ttk.Combobox(row1, textvariable=self.paper_var, 
                                           state="readonly")
        self.paper_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(row1, text="Add", command=self._add_paper).pack(side=tk.LEFT, padx=2)
        ttk.Button(row1, text="Remove", command=self._remove_paper).pack(side=tk.LEFT, padx=2)
        ttk.Button(row1, text="Add All", command=self._add_all_papers).pack(side=tk.LEFT, padx=2)
        ttk.Button(row1, text="Clear", command=self._clear_papers).pack(side=tk.LEFT, padx=2)
        
        # ====== Row 2: Plot Type and Binning Enable ======
        row2 = ttk.Frame(left_side)
        row2.pack(fill=tk.X, pady=5)
        
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
        
        ttk.Separator(row2, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        self.binning_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text="Enable Binning", 
                       variable=self.binning_enabled_var,
                       command=self._on_binning_toggle).pack(side=tk.LEFT, padx=5)
        
        # ====== Row 3: Axes Configuration ======
        row3 = ttk.Frame(left_side)
        row3.pack(fill=tk.X, pady=5)
        
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
        row5.pack(fill=tk.X, pady=5)
        
        ttk.Button(row5, text="Generate Plot", command=self._generate_plot).pack(side=tk.LEFT, padx=5)
        ttk.Button(row5, text="Save Plot", command=self._save_plot).pack(side=tk.LEFT, padx=5)
        ttk.Button(row5, text="Clear", command=self._clear_plot).pack(side=tk.LEFT, padx=5)
        
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
        
        # ====== BINNING CONFIGURATION PANEL ======
        self.binning_panel = BinningConfigPanel(main_frame, on_bins_set=self._on_bins_set)
        self.binning_panel.pack(fill=tk.X, padx=0, pady=(10, 10))
        
        # ====== PLOT DISPLAY AREA (BOTTOM, FULL WIDTH) ======
        self.plot_display = PlotDisplayPanel(main_frame)
        self.plot_display.pack(fill=tk.BOTH, expand=True)
    
    def _add_paper(self):
        """Add selected paper to list."""
        paper = self.paper_var.get()
        if paper and paper not in self.selected_papers:
            self.selected_papers.append(paper)
            self._update_selected_papers_display_listbox()
            self._refresh_axis_dropdowns()
    
    def _remove_paper(self):
        """Remove last selected paper from list."""
        if self.selected_papers:
            self.selected_papers.pop()
            self._update_selected_papers_display_listbox()
            self._refresh_axis_dropdowns()
    
    def _add_all_papers(self):
        """Add all papers to selection."""
        self.selected_papers = self.all_papers.copy()
        self._update_selected_papers_display_listbox()
        self._refresh_axis_dropdowns()
    
    def _clear_papers(self):
        """Clear all selected papers."""
        self.selected_papers = []
        self._update_selected_papers_display_listbox()
        self._refresh_axis_dropdowns()
    
    def _update_selected_papers_display_listbox(self):
        """Update the listbox display of selected papers."""
        self.selected_papers_listbox.delete(0, tk.END)
        for i, paper in enumerate(self.selected_papers, 1):
            self.selected_papers_listbox.insert(tk.END, f"{i}. {paper}")
    
    def _refresh_axis_dropdowns(self):
        """Refresh axis dropdowns based on currently selected papers."""
        if not self.selected_papers:
            # No papers selected - show all symbols from all papers
            papers_for_symbols = self.all_papers
        else:
            # Papers are selected - show only symbols common to selected papers
            papers_for_symbols = self.selected_papers
        
        # Get input variables (same for all configurations)
        input_vars = [
            'Reynolds number (Re)',
            'P/e',
            'e/D',
            'Alpha',
            'Aspect ratio',
            'Number of ribbed walls'
        ]
        
        # Get output variables (symbols) from selected/all papers
        output_vars = data_loader.get_available_symbols(self.df, papers_for_symbols)
        
        # Build combined display list with sections
        axis_display_list = (
            ['INPUT VARIABLES:'] + 
            input_vars + 
            ['─────────────────'] +  # Separator
            ['OUTPUT VARIABLES:'] + 
            output_vars
        )
        
        # Update axis mapping
        self.axis_mapping = {col: col for col in input_vars}
        for symbol in output_vars:
            self.axis_mapping[symbol] = ('symbol', symbol)
        
        # Update dropdowns
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
        """Load initial data and populate UI."""
        if not self.data_file:
            messagebox.showwarning("No Data", 
                                   "Could not find processed research data file.\n"
                                   "Please ensure clean_data_master.csv is in the Staging/ directory.\n"
                                   "Run the preprocessing pipeline to generate it.")
            return
        
        try:
            self.df = data_loader.load_research_data(self.data_file)
            
            # Get available papers
            if 'Paper Title' in self.df.columns:
                self.all_papers = sorted(self.df['Paper Title'].unique().tolist())
                self.paper_dropdown['values'] = self.all_papers
            
            # Build combined axis dropdown list with input and output variables
            input_vars = [
                'Reynolds number (Re)',
                'P/e',
                'e/D',
                'Alpha',
                'Aspect ratio',
                'Number of ribbed walls'
            ]
            
            # Get output variables (symbols) from the data
            output_vars = data_loader.get_available_symbols(self.df, self.all_papers)
            
            # Build combined display list with sections
            axis_display_list = (
                ['INPUT VARIABLES:'] + 
                input_vars + 
                ['─────────────────'] +  # Separator
                ['OUTPUT VARIABLES:'] + 
                output_vars
            )
            
            # Build mapping from display names to actual column names
            self.axis_mapping = {col: col for col in input_vars}
            # Output variables map to themselves (we'll handle them specially in plotting)
            for symbol in output_vars:
                self.axis_mapping[symbol] = ('symbol', symbol)  # Tuple to indicate it's a symbol
            
            # Set axis dropdowns with combined list
            self.x_axis_dropdown['values'] = axis_display_list
            self.y_axis_dropdown['values'] = axis_display_list
            self.z_axis_dropdown['values'] = axis_display_list
            
            # Set up binning panel with available parameters
            self.binning_panel.set_dataframe(self.df)
            self.binning_panel.set_available_parameters(input_vars)
            
            # Set defaults
            if len(input_vars) > 0:
                self.x_axis_dropdown.current(1)  # Skip header
            if len(input_vars) > 1:
                self.y_axis_dropdown.current(2)  # Skip header and first item
            if len(input_vars) > 2 and len(output_vars) > 0:
                # Set Z axis to first output variable
                z_idx = len(input_vars) + 2  # After input vars and separator
                if z_idx < len(axis_display_list):
                    self.z_axis_dropdown.current(z_idx)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data:\n{str(e)}")
    
    def _on_config_change(self):
        """Handle configuration changes."""
        # Could enable/disable generate button based on validation
        pass
    
    def _on_bins_set(self):
        """Callback when bins are set in binning panel."""
        # Could update UI or trigger actions here
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
                    fig = create_custom_3d_surface(filtered_df, x_axis, y_axis, z_axis, x_label, y_label, z_label)
            
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
