"""
Configuration file for research_data_visualizer.py

Users can modify this file to customize the visualization behavior
without editing the main script.
"""

# ============================================================================
# DATA SCHEMA CONFIGURATION
# ============================================================================

# Define all parameter columns that might exist in your data
# Parameters not in this list will be ignored
PARAMETER_COLUMNS = [
    'Reynolds number (Re)',
    'P/e',
    'e/D',
    'Alpha',
    'Aspect ratio',
    'Rib Gap',
    # Add custom parameters here:
    # 'Custom_Parameter_1',
    # 'Custom_Parameter_2',
]

# Core columns (should not change unless your data structure is different)
CORE_COLUMNS = ['Paper Title', 'Figure Number', 'Variable', 'Value']

# ============================================================================
# PLOTTING STYLE CONFIGURATION
# ============================================================================

# Marker styles - used for legend differentiation
MARKERS = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h', '+', 'x']

# Color palette options:
# - "husl" (default): Perceptually uniform
# - "Set1", "Set2", "Set3": Categorical
# - "viridis", "plasma", "inferno": Perceptually uniform
# - "coolwarm", "RdYlBu": Diverging
# - "Pastel1", "Pastel2": Soft colors
SEABORN_PALETTE = "husl"
N_COLORS = 12  # Number of colors to generate

# ============================================================================
# FIGURE STYLE CONFIGURATION
# ============================================================================

# Figure size (width, height) in inches
FIGURE_WIDTH = 10
SUBPLOT_HEIGHT_PER_VAR = 4  # Height per subplot

# DPI for output PNG
OUTPUT_DPI = 300

# Font sizes
TITLE_FONTSIZE = 14
SUBTITLE_FONTSIZE = 10
LABEL_FONTSIZE = 11

# Grid configuration
GRID_STYLE = '--'  # '--' for dashed, ':' for dotted, '-' for solid
GRID_ALPHA = 0.3

# Scatter plot configuration
SCATTER_SIZE = 80
SCATTER_ALPHA = 0.7

# Legend configuration
LEGEND_LOCATION = 'best'  # 'best', 'upper left', 'upper right', 'lower left', etc.
LEGEND_FRAMEALPHA = 0.9

# ============================================================================
# SCALING CONFIGURATION
# ============================================================================

# Threshold for log scaling (data range in orders of magnitude)
# If max/min > this value, log scale will be applied
LOG_SCALE_THRESHOLD = 10

# Always use log scale for Reynolds number
ALWAYS_LOG_RE = True

# ============================================================================
# OUTPUT CONFIGURATION
# ============================================================================

# Default output directory for PNG files
DEFAULT_OUTPUT_DIR = './plots'

# File naming convention
# Options: 'full', 'abbreviated', 'custom'
# 'full': [Full Paper Title]_Fig[Number].png
# 'abbreviated': [First 30 chars of title]_Fig[Number].png
FILE_NAMING = 'abbreviated'

# ============================================================================
# DATA HANDLING CONFIGURATION
# ============================================================================

# String(s) representing missing values in Excel
MISSING_VALUE_STRINGS = ['N/A', 'NA', 'n/a', 'na', 'None', '']

# Drop rows with missing values in these columns
REQUIRED_COLUMNS_NOT_NA = ['Value']

# ============================================================================
# LOGGING & DEBUG CONFIGURATION
# ============================================================================

# Verbosity level: 'quiet', 'normal', 'verbose'
VERBOSITY = 'normal'

# Save debug information
SAVE_DEBUG_INFO = False  # Creates a CSV with analysis details
DEBUG_INFO_DIR = './debug'

# ============================================================================
# ADVANCED CONFIGURATION
# ============================================================================

# Priority for X-axis selection when there's a tie
X_AXIS_PRIORITY = [
    'Reynolds number (Re)',
    'P/e',
    'e/D',
    'Alpha',
    'Aspect ratio',
    'Rib Gap',
]

# Priority for Legend axis selection when there's a tie
LEGEND_PRIORITY = [
    'Alpha',
    'Aspect ratio',
    'P/e',
    'e/D',
    'Reynolds number (Re)',
    'Rib Gap',
]

# Minimum number of data points per plot
MIN_DATA_POINTS = 1  # Set to >1 to skip sparse plots

# ============================================================================
# CUSTOM FORMATTING
# ============================================================================

# Format string for constant parameters in title
# Available placeholders: {param_name}, {param_value}
CONSTANT_FORMAT = '{param_name}={param_value}'
CONSTANT_SEPARATOR = ', '

# Format string for legend labels
# Available placeholders: {axis_name}, {axis_value}
LEGEND_FORMAT = '{axis_name}={axis_value}'

# ============================================================================
# DATA FILTERING RULES (Advanced)
# ============================================================================

# Filter out data points where Value (dependent variable) is
# outside this range. Use None for no limit.
VALUE_MIN = None  # e.g., 0 to exclude zero/negative
VALUE_MAX = None

# Filter out data points where X-axis parameter is
# outside this range. Use None for no limit.
X_AXIS_MIN = None
X_AXIS_MAX = None
