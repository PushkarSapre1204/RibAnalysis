"""GUI for Research Data Visualization with Tabbed Interface and Autocomplete

Provides an interactive interface to:
- Select papers from an autocomplete dropdown
- Select figures for a paper from an autocomplete dropdown
- Generate and display plots in tabbed interface
- Generate all figures for a paper in separate tabs
- Optionally save plots to disk
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import research_data_visualizer as rdv
from pathlib import Path
import traceback

class ResearchVisualizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Verification Tool")
        self.root.geometry("1400x800")
        
        self.df = None
        self.batches = None
        self.current_fig = None
        self.current_paper_title = None
        self.current_fig_num = None
        
        # Data structures for paper/figure mapping
        self.paper_keys = []  # List of unique paper titles
        self.paper_to_figures = {}  # {paper_title: [(fig_num, display_string, x_var, y_var), ...]}
        self.figure_keys = []  # Current list of (paper_title, fig_num) for selected paper
        self.full_paper_list = []  # Full unfiltered list of papers
        self.full_figure_list = []  # Full unfiltered list of figures for current paper
        self.plot_tabs = {}  # Store figure and canvas objects for each tab
        
        self._build_ui()
        self._load_data()
    
    def _build_ui(self):
        """Build the user interface."""
        # Main container
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        
        # --- Control Panel ---
        control_frame = ttk.LabelFrame(self.main_frame, text="Controls", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        control_frame.columnconfigure(1, weight=1)
        
        # Row 0: Paper dropdown
        ttk.Label(control_frame, text="Select Paper:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.paper_combo = ttk.Combobox(control_frame, width=70, state="normal")
        self.paper_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.paper_combo.bind("<<ComboboxSelected>>", self._on_paper_selected)
        self.paper_combo.bind("<KeyRelease>", self._filter_papers)
        
        # Generate All button
        self.generate_all_button = ttk.Button(control_frame, text="Generate All Figures", command=self.on_generate_all)
        self.generate_all_button.grid(row=0, column=2, sticky=tk.E, padx=(0, 5))
        
        # Row 1: Figure dropdown
        ttk.Label(control_frame, text="Select Figure:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.figure_combo = ttk.Combobox(control_frame, width=70, state="normal")
        self.figure_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.figure_combo.bind("<KeyRelease>", self._filter_figures)
        
        # Buttons for single figure
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=1, column=2, sticky=tk.E)
        
        self.generate_button = ttk.Button(button_frame, text="Generate", command=self.on_generate_plot)
        self.generate_button.pack(side=tk.LEFT, padx=5)
        
        self.save_button = ttk.Button(button_frame, text="Save Plot", command=self.on_save_plot, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        self.save_all_button = ttk.Button(button_frame, text="Save All", command=self.on_save_all, state=tk.DISABLED)
        self.save_all_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = ttk.Button(button_frame, text="Clear", command=self.on_clear)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # --- Plot Display Area with Tabs ---
        plot_frame = ttk.LabelFrame(self.main_frame, text="Plot Preview", padding="5")
        plot_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        plot_frame.columnconfigure(0, weight=1)
        plot_frame.rowconfigure(0, weight=1)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(plot_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # --- Status Bar ---
        self.status_var = tk.StringVar(value="Ready. Load data to begin.")
        status_bar = ttk.Label(self.main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def _analyze_figure_axes(self, batch_df):
        """Pre-analyze a figure to determine X and Y axes for descriptive naming.
        
        Returns:
            Tuple of (x_axis_label, y_axis_label)
        """
        try:
            # Get the first variable
            variables = rdv.get_variables_in_batch(batch_df)
            y_var = variables[0] if variables else "Value"
            
            # Analyze variability to get X axis
            var_data = batch_df[batch_df['Variable'] == y_var].copy()
            analysis = rdv.analyze_parameter_variability(var_data, rdv.PARAMETER_COLUMNS)
            x_axis, _, _, _ = rdv.select_axes(analysis, var_data)
            x_var = x_axis if x_axis else "Index"
            
            return x_var, y_var
        except Exception:
            return "Unknown", "Value"
    
    def _filter_papers(self, event=None):
        """Filter papers as user types in the paper dropdown."""
        text = self.paper_combo.get().lower()
        if not text:
            self.paper_combo['values'] = self.full_paper_list
            return
        
        filtered = [p for p in self.full_paper_list if text in p.lower()]
        self.paper_combo['values'] = filtered
        self.paper_combo.event_generate("<Down>")  # Show dropdown
    
    def _filter_figures(self, event=None):
        """Filter figures as user types in the figure dropdown."""
        text = self.figure_combo.get().lower()
        if not text:
            self.figure_combo['values'] = self.full_figure_list
            return
        
        filtered = [f for f in self.full_figure_list if text in f.lower()]
        self.figure_combo['values'] = filtered
        self.figure_combo.event_generate("<Down>")  # Show dropdown
    
    def _load_data(self):
        """Load data from Excel file."""
        try:
            self.status_var.set("Loading data from Rib Data.xlsx...")
            self.root.update()
            
            self.df = rdv.load_research_data('Rib Data.xlsx')
            self.batches = rdv.create_hierarchical_batches(self.df)
            
            # Build paper mapping with pre-analyzed axes
            self.paper_to_figures = {}
            for paper_title, fig_num in sorted(self.batches.keys()):
                if paper_title not in self.paper_to_figures:
                    self.paper_to_figures[paper_title] = []
                
                # Analyze this figure to determine X and Y axes
                batch_df = self.batches[(paper_title, fig_num)]
                x_var, y_var = self._analyze_figure_axes(batch_df)
                
                # Strip "Fig " prefix for display
                fig_display_num = str(fig_num).replace("Fig ", "").strip()
                display_string = f"Fig {fig_display_num} - {x_var} vs {y_var}"
                
                self.paper_to_figures[paper_title].append((fig_num, display_string, x_var, y_var))
            
            # Get unique paper titles
            self.paper_keys = sorted(self.paper_to_figures.keys())
            self.full_paper_list = self.paper_keys.copy()
            self.paper_combo['values'] = self.paper_keys
            
            if self.paper_keys:
                self.paper_combo.current(0)
                self._on_paper_selected(None)
                self.status_var.set(f"Ready. Loaded {len(self.batches)} figure(s) from {len(self.paper_keys)} paper(s).")
            else:
                self.status_var.set("No data found in Excel file.")
                messagebox.showwarning("Warning", "No data batches found in the Excel file.")
        
        except FileNotFoundError:
            messagebox.showerror("Error", "Rib Data.xlsx not found.\n\nPlease place it in the same directory as this script.")
            self.status_var.set("Error: Data file not found.")
            self.root.quit()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data:\n{str(e)}")
            self.status_var.set(f"Error: {str(e)}")
            print(traceback.format_exc())
    
    def _on_paper_selected(self, event):
        """Populate figure dropdown when paper is selected."""
        selected_paper = self.paper_combo.get()
        if not selected_paper or selected_paper not in self.paper_to_figures:
            self.figure_combo['values'] = []
            self.figure_keys = []
            self.full_figure_list = []
            return
        
        # Build figure list for this paper
        figures = self.paper_to_figures[selected_paper]
        self.figure_keys = [(selected_paper, fig_num) for fig_num, display, _, _ in figures]
        figure_displays = [display for _, display, _, _ in figures]
        
        self.full_figure_list = figure_displays.copy()
        self.figure_combo['values'] = figure_displays
        self.figure_combo.delete(0, tk.END)  # Clear text input
        if figure_displays:
            self.figure_combo.current(0)
    
    def _create_tab(self, tab_name):
        """Create a new tab with a canvas for plotting.
        
        Returns:
            Tuple of (figure, canvas) objects for drawing
        """
        # Create a frame for this tab
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text=tab_name)
        tab_frame.columnconfigure(0, weight=1)
        tab_frame.rowconfigure(0, weight=1)
        
        # Create matplotlib figure and canvas
        fig = Figure(figsize=(12, 6), dpi=100)
        canvas = FigureCanvasTkAgg(fig, master=tab_frame)
        canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.plot_tabs[tab_name] = {'fig': fig, 'canvas': canvas}
        self._update_button_states()
        return fig, canvas
    
    def _update_button_states(self):
        """Update button states based on number of tabs."""
        tab_count = len(self.notebook.tabs())
        
        # Enable Save All only if there are multiple tabs
        if tab_count > 1:
            self.save_all_button.config(state=tk.NORMAL)
        else:
            self.save_all_button.config(state=tk.DISABLED)
    
    def _clear_tabs(self):
        """Clear all tabs from the notebook."""
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)
        self.plot_tabs.clear()
        self._update_button_states()
    
    def on_generate_plot(self):
        """Generate plot for selected paper and figure in a new tab."""
        selected_figure = self.figure_combo.get()
        if not selected_figure:
            messagebox.showwarning("Warning", "Please select a figure.")
            return
        
        try:
            self.status_var.set("Generating plot...")
            self.root.update()
            
            # Get the selected key from the stored keys
            selected_index = self.figure_combo.current()
            if selected_index < 0 or selected_index >= len(self.figure_keys):
                raise ValueError("Invalid selection")
            
            self.current_paper_title, self.current_fig_num = self.figure_keys[selected_index]
            batch_df = self.batches[(self.current_paper_title, self.current_fig_num)]
            
            # Get number of variables to determine subplot layout
            n_vars = len(rdv.get_variables_in_batch(batch_df))
            
            # Clear existing tabs (single plot mode)
            self._clear_tabs()
            
            # Create new tab
            tab_name = selected_figure.split(" - ")[0]  # Use just "Fig X" as tab name
            fig, canvas = self._create_tab(tab_name)
            
            # Create subplots
            axes = fig.subplots(n_vars, 1) if n_vars > 1 else fig.add_subplot(111)
            
            # Generate plot on the new figure
            self.current_fig = rdv.create_figure_plot(
                batch_df,
                self.current_paper_title,
                self.current_fig_num,
                output_dir=None,
                fig=fig,
                axes=axes
            )
            
            # Redraw canvas
            canvas.draw()
            self.save_button.config(state=tk.NORMAL)
            self.status_var.set(f"Plot generated: {self.current_paper_title} - Fig {self.current_fig_num}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate plot:\n{str(e)}")
            self.status_var.set(f"Error: {str(e)}")
            print(traceback.format_exc())
    
    def on_generate_all(self):
        """Generate all figures for the selected paper in separate tabs."""
        selected_paper = self.paper_combo.get()
        if not selected_paper or selected_paper not in self.paper_to_figures:
            messagebox.showwarning("Warning", "Please select a paper first.")
            return
        
        try:
            self.status_var.set("Generating all figures...")
            self.root.update()
            
            # Clear existing tabs
            self._clear_tabs()
            
            figures = self.paper_to_figures[selected_paper]
            total = len(figures)
            
            for idx, (fig_num, display_string, _, _) in enumerate(figures):
                batch_df = self.batches[(selected_paper, fig_num)]
                
                # Get number of variables
                n_vars = len(rdv.get_variables_in_batch(batch_df))
                
                # Create new tab
                tab_name = display_string.split(" - ")[0]  # Use just "Fig X" as tab name
                fig, canvas = self._create_tab(tab_name)
                
                # Create subplots
                axes = fig.subplots(n_vars, 1) if n_vars > 1 else fig.add_subplot(111)
                
                # Generate plot
                plot_fig = rdv.create_figure_plot(
                    batch_df,
                    selected_paper,
                    fig_num,
                    output_dir=None,
                    fig=fig,
                    axes=axes
                )
                
                # Redraw canvas
                canvas.draw()
                self.status_var.set(f"Generated {idx + 1}/{total} figures for {selected_paper[:50]}...")
                self.root.update()
                
                # Store the last figure for potential saving
                self.current_fig = plot_fig
                self.current_paper_title = selected_paper
                self.current_fig_num = fig_num
            
            self.status_var.set(f"Completed! Generated all {total} figures for {selected_paper}")
            self.save_button.config(state=tk.NORMAL)
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate plots:\n{str(e)}")
            self.status_var.set(f"Error: {str(e)}")
            print(traceback.format_exc())
    
    def on_save_plot(self):
        """Save the current plot to disk."""
        if not self.current_fig:
            messagebox.showwarning("Warning", "No plot to save. Generate a plot first.")
            return
        
        try:
            output_dir = filedialog.askdirectory(title="Select Folder to Save Plot")
            if not output_dir:
                return  # User cancelled
            
            self.status_var.set("Saving plot...")
            self.root.update()
            
            rdv.save_figure_plot(
                self.current_fig,
                self.current_paper_title,
                self.current_fig_num,
                Path(output_dir)
            )
            
            self.status_var.set(f"Plot saved to {output_dir}")
            messagebox.showinfo("Success", f"Plot saved successfully to:\n{output_dir}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save plot:\n{str(e)}")
            self.status_var.set(f"Error: {str(e)}")
            print(traceback.format_exc())
    
    def on_save_all(self):
        """Save all plots currently in tabs."""
        if len(self.plot_tabs) <= 1:
            messagebox.showwarning("Warning", "No plots to save. Generate multiple plots first.")
            return
        
        try:
            output_dir = filedialog.askdirectory(title="Select Folder to Save All Plots")
            if not output_dir:
                return  # User cancelled
            
            self.status_var.set("Saving all plots...")
            self.root.update()
            
            saved_count = 0
            for tab_name, tab_data in self.plot_tabs.items():
                try:
                    fig = tab_data['fig']
                    # Extract paper title and fig num from internal storage
                    rdv.save_figure_plot(
                        fig,
                        self.current_paper_title,
                        self.current_fig_num,
                        Path(output_dir)
                    )
                    saved_count += 1
                except Exception as e:
                    print(f"Failed to save tab {tab_name}: {str(e)}")
            
            self.status_var.set(f"Saved {saved_count} plot(s) to {output_dir}")
            messagebox.showinfo("Success", f"Saved {saved_count} plot(s) successfully to:\n{output_dir}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save plots:\n{str(e)}")
            self.status_var.set(f"Error: {str(e)}")
            print(traceback.format_exc())
    
    def on_clear(self):
        """Clear all plots (close all tabs)."""
        self._clear_tabs()
        self.save_button.config(state=tk.DISABLED)
        self.status_var.set("All plots cleared.")


def main():
    root = tk.Tk()
    app = ResearchVisualizerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
