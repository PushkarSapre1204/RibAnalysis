"""
Automated Research Data Visualization Script

This script reads experimental data from an Excel file and automatically generates
publication-quality plots with parameter-agnostic axis selection based on data variability.

Features:
- Hierarchical batching by Paper Title and Figure Number
- Dynamic axis selection based on parameter variability
- Automatic log-log scaling detection
- Graceful handling of N/A values
- Multi-variable subplots with unified styling
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Tuple, Set
import numpy as np
import warnings

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

# Parameter columns that may vary across experiments (used for axis selection)
PARAMETER_COLUMNS = [
    'Reynolds number (Re)',
    'Geometry',
    'P/e',
    'e/D',
    'Alpha',
    'Aspect ratio',
    'Number of ribbed walls'
]

# Test condition columns (shown in title but not used for axes)
TEST_CONDITION_COLUMNS = [
    'Reading on',
    'Constant factor'
]

# Core data columns (not parameters)
CORE_COLUMNS = ['Paper Title', 'Figure Number', 'Point ID', 'Variable', 'Value']

# Additional data columns (not used in analysis)
ADDITIONAL_DATA_COLUMNS = ['Dittus-Boelter Value']

# Marker styles for legend differentiation
MARKERS = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h', '+', 'x']
COLORS = sns.color_palette("husl", 12)

# ============================================================================
# DATA LOADING & PREPROCESSING
# ============================================================================

def load_research_data(file_path: str) -> pd.DataFrame:
    """
    Load research data file (CSV or Excel) and preprocess data.
    
    Args:
        file_path: Path to the data file (CSV or Excel)
        
    Returns:
        DataFrame with cleaned data
    """
    # Determine file type and load accordingly
    if file_path.lower().endswith('.csv'):
        df = pd.read_csv(file_path)
    elif file_path.lower().endswith(('.xlsx', '.xls')):
        df = pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_path}. Expected CSV or Excel.")
    
    # Convert 'N/A' strings to NaN for easier handling
    df = df.replace('N/A', np.nan)
    
    # Convert parameter columns to numeric types (handle invalid values by converting to NaN)
    parameter_columns = [
        'Reynolds number (Re)',
        'P/e',
        'e/D',
        'Alpha',
        'Aspect ratio',
        'Number of ribbed walls'
    ]
    
    for col in parameter_columns:
        if col in df.columns:
            # Convert to numeric, coercing errors to NaN
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Also convert 'Value' column to numeric (for output variables)
    if 'Value' in df.columns:
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
    
    print(f"Loaded data: {df.shape[0]} rows, {df.shape[1]} columns")
    print(f"Columns: {list(df.columns)}")
    
    return df


# ============================================================================
# HIERARCHICAL BATCHING
# ============================================================================

def create_hierarchical_batches(df: pd.DataFrame) -> Dict[Tuple[str, int], pd.DataFrame]:
    """
    Group data hierarchically by Paper Title and Figure Number.
    
    Args:
        df: Input DataFrame
        
    Returns:
        Dictionary with (paper_title, figure_number) as keys and filtered DataFrames as values
    """
    batches = {}
    
    for (paper_title, fig_num), group in df.groupby(['Paper Title', 'Figure Number']):
        batches[(paper_title, fig_num)] = group.reset_index(drop=True)
    
    print(f"\nCreated {len(batches)} figure batches")
    for key in sorted(batches.keys()):
        print(f"  {key[0][:40]}... Fig {key[1]}: {len(batches[key])} points")
    
    return batches


def get_variables_in_batch(batch_df: pd.DataFrame) -> List[str]:
    """
    Get unique variables in a batch.
    
    Args:
        batch_df: DataFrame for a specific paper-figure combination
        
    Returns:
        List of unique variable names
    """
    return sorted(batch_df['Variable'].unique())


def get_available_symbols(df: pd.DataFrame, papers: List[str]) -> List[str]:
    """
    Get output variable symbols (from Variable column) that are available in ALL selected papers.
    
    Args:
        df: Input DataFrame
        papers: List of selected paper titles
        
    Returns:
        Sorted list of symbols present in all selected papers (e.g., ['Nu', 'f', 'St'])
    """
    if not papers:
        return []
    
    # Get symbols available in each paper
    paper_symbols = []
    for paper in papers:
        paper_df = df[df['Paper Title'] == paper]
        symbols = set(paper_df['Variable'].dropna().unique().tolist())
        paper_symbols.append(symbols)
    
    # Find intersection of symbols across all papers
    if paper_symbols:
        common_symbols = paper_symbols[0]
        for symbols_set in paper_symbols[1:]:
            common_symbols = common_symbols.intersection(symbols_set)
        return sorted(list(common_symbols))
    
    return []


def build_axis_dropdown_list() -> Tuple[List[str], Dict[str, str]]:
    """
    Build combined axis dropdown list with input and output variables.
    
    Returns:
        Tuple of (display_list, mapping_dict)
        - display_list: Formatted list for dropdown display
        - mapping_dict: Maps display names to actual column names
    """
    input_vars = [
        'Reynolds number (Re)',
        'P/e',
        'e/D',
        'Alpha',
        'Aspect ratio',
        'Number of ribbed walls'
    ]
    
    display_list = ['INPUT VARIABLES:'] + input_vars + ['', 'OUTPUT VARIABLES:']
    mapping = {col: col for col in input_vars}
    
    # Output variables (symbols) will be added dynamically in GUI
    # They'll be added after the separator
    
    return display_list, mapping


# ============================================================================
# VARIABILITY ANALYSIS (Dynamic Axis Selection)
# ============================================================================

def analyze_parameter_variability(
    data_points: pd.DataFrame,
    parameters: List[str]
) -> Dict[str, Dict]:
    """
    Analyze which parameters are constant vs. variable for a specific variable-batch.
    
    Args:
        data_points: DataFrame containing only data for one Variable
        parameters: List of parameter column names to analyze
        
    Returns:
        Dictionary with 'constants', 'variables', and 'test_conditions' keys
    """
    analysis = {
        'constants': {},      # {param_name: value} - from PARAMETER_COLUMNS
        'variables': {},      # {param_name: unique_count} - from PARAMETER_COLUMNS
        'test_conditions': {} # {param_name: value} - from TEST_CONDITION_COLUMNS
    }
    
    # Analyze PARAMETER_COLUMNS for axis selection
    for param in parameters:
        if param not in data_points.columns:
            continue
        
        # Filter out NaN values
        non_na_values = data_points[param].dropna()
        
        if len(non_na_values) == 0:
            # All values are N/A - ignore this parameter
            continue
        
        unique_count = len(non_na_values.unique())
        
        if unique_count == 1:
            # This is a constant parameter
            analysis['constants'][param] = non_na_values.iloc[0]
        else:
            # This is a variable parameter
            analysis['variables'][param] = unique_count
    
    # Analyze TEST_CONDITION_COLUMNS for title display
    for test_param in TEST_CONDITION_COLUMNS:
        if test_param not in data_points.columns:
            continue
        
        # Filter out NaN values
        non_na_values = data_points[test_param].dropna()
        
        if len(non_na_values) == 0:
            # All values are N/A - ignore this parameter
            continue
        
        # Get the value (typically constant within a figure)
        unique_value = non_na_values.iloc[0]
        analysis['test_conditions'][test_param] = unique_value
    
    return analysis


def select_axes(analysis: Dict[str, Dict], data_points: pd.DataFrame) -> Tuple[str, str, Dict, Dict]:
    """
    Determine X-axis, Legend (hue) axis, constants, and test conditions based on variability.
    
    Args:
        analysis: Output from analyze_parameter_variability
        data_points: The actual data points (for validation)
        
    Returns:
        Tuple of (x_axis_column, legend_column, constants_dict, test_conditions_dict)
    """
    variables = analysis['variables']
    constants = analysis['constants']
    test_conditions = analysis.get('test_conditions', {})
    
    if len(variables) == 0:
        # No variable parameters - single point or flat data
        return None, None, constants, test_conditions
    
    # Sort variables by unique count (descending)
    sorted_vars = sorted(variables.items(), key=lambda x: x[1], reverse=True)
    
    x_axis = None
    legend_axis = None
    
    # Priority: Check for ties and apply conflict resolution
    if len(sorted_vars) >= 1:
        highest_count = sorted_vars[0][1]
        
        # Find all parameters with the highest count
        tied_params = [name for name, count in sorted_vars if count == highest_count]
        
        if 'Reynolds number (Re)' in tied_params:
            x_axis = 'Reynolds number (Re)'
        else:
            x_axis = tied_params[0]
    
    if len(sorted_vars) >= 2:
        second_highest_count = sorted_vars[1][1]
        
        # Find all parameters with the second-highest count
        tied_params = [name for name, count in sorted_vars if count == second_highest_count]
        
        # Exclude the x_axis parameter
        tied_params = [name for name in tied_params if name != x_axis]
        
        if tied_params:
            legend_axis = tied_params[0]
    
    return x_axis, legend_axis, constants, test_conditions


# ============================================================================
# PLOTTING
# ============================================================================

def check_need_log_scale(values: np.ndarray) -> bool:
    """
    Determine if log scaling is needed based on data range.
    
    Data spans more than one order of magnitude if:
    max(values) / min(values) > 10
    
    Args:
        values: Array of numerical values
        
    Returns:
        True if log scaling should be applied
    """
    # Filter out non-positive values and NaN
    valid_values = values[(values > 0) & ~np.isnan(values)]
    
    if len(valid_values) < 2:
        return False
    
    data_range = valid_values.max() / valid_values.min()
    return data_range > 10


def prepare_plot_data(
    batch_df: pd.DataFrame,
    variable: str,
    x_axis: str,
    legend_axis: str
) -> pd.DataFrame:
    """
    Prepare data for plotting by removing N/A values and sorting.
    
    Args:
        batch_df: Full batch DataFrame
        variable: The specific variable to plot
        x_axis: X-axis parameter column name
        legend_axis: Legend parameter column name
        
    Returns:
        Cleaned DataFrame ready for plotting
    """
    # Filter to specific variable
    plot_data = batch_df[batch_df['Variable'] == variable].copy()
    
    # Remove rows where x_axis or legend_axis values are NaN
    if x_axis:
        plot_data = plot_data.dropna(subset=[x_axis])
    if legend_axis:
        plot_data = plot_data.dropna(subset=[legend_axis])
    
    # Ensure Value column has no NaN
    plot_data = plot_data.dropna(subset=['Value'])
    
    # Sort for better plotting
    sort_cols = [col for col in [x_axis, legend_axis] if col]
    if sort_cols:
        plot_data = plot_data.sort_values(by=sort_cols)
    
    return plot_data


def create_figure_plot(
    batch_df: pd.DataFrame,
    paper_title: str,
    fig_num: int,
    output_dir: Path = None,
    fig: plt.Figure = None,
    axes: np.ndarray = None
) -> plt.Figure:
    """
    Create a multi-variable figure with subplots for each variable.
    
    Args:
        batch_df: DataFrame for a specific paper-figure combination
        paper_title: Title of the paper
        fig_num: Figure number
        output_dir: Directory to save PNG output (optional)
        fig: Matplotlib Figure to draw on (optional)
        axes: Matplotlib Axes to draw on (optional)
        
    Returns:
        The generated Matplotlib Figure
    """
    variables = get_variables_in_batch(batch_df)
    n_vars = len(variables)
    
    # Create subplots if not provided
    if fig is None or axes is None:
        fig, axes = plt.subplots(n_vars, 1, figsize=(10, 4 * n_vars))
    
    # Handle single subplot case (axes is not a list)
    if n_vars == 1:
        axes = [axes] if not isinstance(axes, (list, np.ndarray)) else axes
    
    for idx, variable in enumerate(variables):
        ax = axes[idx]
        ax.clear()  # Clear previous content if reusing axes
        
        # Filter data for this variable
        var_data = batch_df[batch_df['Variable'] == variable].copy()
        
        # Analyze variability
        analysis = analyze_parameter_variability(var_data, PARAMETER_COLUMNS)
        x_axis, legend_axis, constants, test_conditions = select_axes(analysis, var_data)
        
        # Prepare plot data
        plot_data = prepare_plot_data(batch_df, variable, x_axis, legend_axis)
        
        if len(plot_data) == 0:
            ax.text(0.5, 0.5, f'{variable}\nNo valid data points',
                   ha='center', va='center', transform=ax.transAxes)
            continue
        
        # Determine log scaling
        use_log_x = (x_axis == 'Reynolds number (Re)') or \
                    (x_axis and check_need_log_scale(plot_data[x_axis].values))
        use_log_y = check_need_log_scale(plot_data['Value'].values)
        
        # Plot data
        if legend_axis is None:
            # No legend axis - single line/scatter
            ax.scatter(plot_data[x_axis], plot_data['Value'],
                      color=COLORS[0], marker=MARKERS[0], s=80, alpha=0.7, label=None)
        else:
            # Multiple series based on legend axis
            groups = plot_data.groupby(legend_axis, sort=False)
            for color_idx, (legend_val, group) in enumerate(groups):
                marker = MARKERS[color_idx % len(MARKERS)]
                color = COLORS[color_idx % len(COLORS)]
                
                ax.scatter(group[x_axis], group['Value'],
                          color=color, marker=marker, s=80, alpha=0.7,
                          label=f'{legend_axis}={legend_val}')
            
            ax.legend(title=legend_axis, loc='best', framealpha=0.9)
        
        # Apply log scaling
        if use_log_x:
            ax.set_xscale('log')
        if use_log_y:
            ax.set_yscale('log')
        
        # Labels
        ax.set_xlabel(x_axis if x_axis else 'Index', fontsize=11, fontweight='bold')
        ax.set_ylabel(variable, fontsize=11, fontweight='bold')
        
        # Build subplot title with constants and test conditions
        const_parts = []
        if constants:
            const_parts.extend([f'{k}={v}' for k, v in sorted(constants.items())])
        if test_conditions:
            const_parts.extend([f'{k}={v}' for k, v in sorted(test_conditions.items())])
        
        const_str = ', '.join(const_parts)
        subtitle = f'{variable}'
        if const_str:
            subtitle += f' | {const_str}'
        
        ax.set_title(subtitle, fontsize=10, style='italic')
        ax.grid(True, which='both', linestyle='--', alpha=0.3)
    
    # Overall figure title
    fig_title = f'{paper_title} - Figure {fig_num}'
    fig.suptitle(fig_title, fontsize=14, fontweight='bold', y=0.995)
    
    plt.tight_layout()
    
    # Save figure if output_dir is provided
    if output_dir:
        save_figure_plot(fig, paper_title, fig_num, output_dir)
        plt.close(fig)
    
    return fig


def save_figure_plot(fig: plt.Figure, paper_title: str, fig_num: int, output_dir: Path) -> None:
    """
    Save the figure to a file.
    
    Args:
        fig: The Matplotlib Figure to save
        paper_title: Title of the paper
        fig_num: Figure number
        output_dir: Directory to save PNG output
    """
    safe_title = "".join([c for c in paper_title if c.isalnum() or c in (' ', '_')]).rstrip()
    output_file = output_dir / f'{safe_title}_Fig{fig_num}.png'
    
    fig.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def process_research_data(excel_file_path: str, output_directory: str = None) -> None:
    """
    Main function to process research data and generate plots.
    
    Args:
        excel_file_path: Path to the input Excel file
        output_directory: Directory to save PNG outputs (defaults to ./plots/)
    """
    # Setup output directory
    if output_directory is None:
        output_directory = Path('./plots')
    else:
        output_directory = Path(output_directory)
    
    output_directory.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("RESEARCH DATA VISUALIZATION PIPELINE")
    print("=" * 70)
    
    # Load data
    print("\n[1] Loading data...")
    df = load_research_data(excel_file_path)
    
    # Create batches
    print("\n[2] Creating hierarchical batches...")
    batches = create_hierarchical_batches(df)
    
    # Process each batch
    print("\n[3] Generating plots...")
    for (paper_title, fig_num), batch_df in batches.items():
        print(f"\n  Processing: {paper_title[:50]}... Fig {fig_num}")
        fig = create_figure_plot(batch_df, paper_title, fig_num, output_directory)
        plt.close(fig)
    
    print("\n" + "=" * 70)
    print(f"COMPLETE! Generated {len(batches)} figure(s)")
    print(f"Outputs saved to: {output_directory.absolute()}")
    print("=" * 70)


if __name__ == '__main__':
    # Example usage
    # Modify this path to point to your actual Excel file
    excel_file = 'Rib Data.xlsx'
    output_dir = 'Outputs'
    
    process_research_data(excel_file, output_dir)
    
    # Optional: specify custom output directory
    output_dir = './plots'
    
    process_research_data(excel_file, output_dir)
