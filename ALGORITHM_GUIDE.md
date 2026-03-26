
# ALGORITHM VISUAL GUIDE

## Overview Flowchart

```
┌─────────────────────────────────────────────────────────────────┐
│ INPUT: Excel file with research data (15 columns)               │
│ • Core: Paper Title, Figure #, Point ID, Variable, Value        │
│ • Parameters (7): Re, Geometry, P/e, e/D, Alpha, Aspect, Walls  │
│ • Test Conditions (2): Reading on, Constant factor              │
│ • Additional (1): Dittus-Boelert Value                           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: LOAD & PREPROCESS                                       │
│ • Convert 'N/A' strings to NaN                                  │
│ • Parse numeric values                                           │
│ • Categorize columns by type                                    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: HIERARCHICAL BATCHING                                   │
│ Group by: Paper Title → Figure Number → Variable                │
│ For each combination:                                            │
│   - Create separate subplot                                     │
│   - Analyze variability independently                           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: ANALYZE PARAMETER COLUMNS (7 parameters only)           │
│                                                                 │
│ For each parameter:                                             │
│   IF all values are NaN:                                        │
│     → Ignore this parameter                                     │
│   ELSE:                                                          │
│     Count unique non-NaN values:                                │
│       1 unique value  → CONSTANT parameter                      │
│       >1 unique value → VARIABLE parameter                      │
│                                                                 │
│ KEEP SEPARATE: Test Condition columns (always in title)         │
│ IGNORE: Additional Data column (Dittus-Boelert)                 │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: EXTRACT TEST CONDITIONS                                 │
│ Extract values from Test Condition columns:                     │
│   • Reading on                                                  │
│   • Constant factor                                             │
│ These are NOT analyzed, just extracted for title display        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: AXIS SELECTION (from VARIABLE parameters only)          │
│                                                                 │
│ X-AXIS: Parameter with HIGHEST number of unique values         │
│   • On tie: Prioritize Reynolds number (Re)                    │
│                                                                 │
│ LEGEND: Parameter with SECOND-HIGHEST unique count             │
│   • On tie: Use priority list from config                      │
│                                                                 │
│ TITLE: Constants + Test Conditions                              │
│   Format: "Variable | const=val, test=val"                     │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: SCALING DETECTION                                       │
│                                                                 │
│ LOG-X: Use log scale if:                                        │
│   • X-axis is Reynolds number (Re), OR                          │
│   • Data range (max/min) > 10                                   │
│                                                                 │
│ LOG-Y: Use log scale if:                                        │
│   • Data range (max/min) > 10                                   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 7: PLOT GENERATION                                         │
│                                                                 │
│ For each data point:                                            │
│   • Plot X vs Value (scatter)                                   │
│   • Color by Legend category                                    │
│   • Shape by Legend category (different markers)               │
│                                                                 │
│ Apply:                                                          │
│   • Log scaling (X and/or Y if needed)                          │
│   • Grid lines                                                  │
│   • Clear labels and legend                                     │
│   • Professional styling (seaborn)                              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ OUTPUT: PNG files (300 DPI)                                     │
│ Filename: [Paper_Title]_Fig[Number].png                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Variability Analysis: Step-by-Step Example

### Input Data
```
Reynolds (Re) | P/e | e/D | Alpha | Aspect | Value
1000          | 10  | N/A | 45    | 2      | 15.2
5000          | 10  | N/A | 45    | 4      | 18.5
10000         | 10  | N/A | 60    | 2      | 22.3
20000         | 10  | N/A | 60    | 4      | 25.8
```

### Analysis Process

```
Parameter Analysis:
─────────────────

Reynolds (Re):
  Values (non-NaN): [1000, 5000, 10000, 20000]
  Unique count: 4
  → VARIABLE (4 unique values)

P/e:
  Values (non-NaN): [10, 10, 10, 10]
  Unique count: 1
  → CONSTANT (only 1 unique value)

e/D:
  Values (non-NaN): [N/A, N/A, N/A, N/A]
  Unique count: 0
  → IGNORED (entirely N/A)

Alpha:
  Values (non-NaN): [45, 45, 60, 60]
  Unique count: 2
  → VARIABLE (2 unique values)

Aspect:
  Values (non-NaN): [2, 4, 2, 4]
  Unique count: 2
  → VARIABLE (2 unique values)
```

### Axis Selection

```
Variables by Unique Count (descending):
1. Reynolds (Re): 4 unique values  ← HIGHEST
2. Alpha: 2 unique values          ← SECOND
3. Aspect: 2 unique values         ← SECOND (tie with Alpha)

Selection:
──────────
X-AXIS: Reynolds (Re)  [highest variability]
LEGEND: Alpha          [second highest, selected first in priority list]
CONSTANTS: P/e=10, e/D=N/A (ignored)

Final Title:
────────────
"Variable | Conditions: P/e=10"
(e/D omitted because entirely N/A)
```

---

## Axis Assignment Rules (Priority)

### X-Axis Selection Algorithm

```python
def select_x_axis(variables_dict):
    """
    variables_dict: {param_name: unique_count, ...}
    """
    sorted_vars = sort by unique count (descending)
    
    highest_count = sorted_vars[0].count
    tied_params = [p for p in sorted_vars if p.count == highest_count]
    
    if 'Reynolds number (Re)' in tied_params:
        return 'Reynolds number (Re)'  # Priority!
    else:
        return tied_params[0]  # First in order
```

### Example Tie-Breaking

**Scenario 1: Re vs P/e both have 4 unique values**
```
Reynolds (Re): 4 unique → Tied
P/e: 4 unique           → Tied

Decision: Choose Reynolds number (Re) [PRIORITY]
```

**Scenario 2: Alpha vs Aspect both have 2 unique values**
```
Alpha: 2 unique         → Tied
Aspect: 2 unique        → Tied

Decision: Choose Alpha [appears first in parameter list]
```

---

## Log Scale Detection

### Algorithm

```python
def check_need_log_scale(values):
    # Filter: keep only positive, non-NaN values
    valid = [v for v in values if v > 0 and not NaN]
    
    if len(valid) < 2:
        return False
    
    range = max(valid) / min(valid)
    return range > 10  # More than 1 order of magnitude
```

### Examples

**Example 1: Data [10, 50, 100]**
```
Range: 100/10 = 10 (exactly 1 order of magnitude)
Result: NO log scale (range must be > 10)
```

**Example 2: Data [1, 10, 100, 1000]**
```
Range: 1000/1 = 1000 (3 orders of magnitude)
Result: YES log scale (range > 10)
```

**Example 3: Data with Reynolds number as X-axis**
```
X-axis is 'Reynolds number (Re)'
Result: YES log scale [ALWAYS, regardless of data range]
```

**Example 4: Data with N/A and negative**
```
Raw: [-100, 0, 1, 10, 100, 1000, N/A]
Valid: [1, 10, 100, 1000]  (filtered)
Range: 1000/1 = 1000
Result: YES log scale
```

---

## Data Flow Example: Complete Paper

### Input Excel
```
Paper Title: "Flow Dynamics in Ribbed Channels"
3 figures with 14 total data points
```

### Processing

```
PAPER: Flow Dynamics in Ribbed Channels
│
├─ FIGURE 1 (4 data points)
│  │
│  └─ VARIABLE: Nu
│     ├─ X-axis: Reynolds (Re) [4 unique: 1k, 5k, 10k, 20k]
│     ├─ Legend: None [P/e constant: 10]
│     └─ Constants: P/e=10, e/D=0.1, Alpha=45, Aspect=2
│        → Plot 1: Scatter (Re vs Nu) with log-log scaling
│           Title: "Nu | Conditions: P/e=10, e/D=0.1, Alpha=45, Aspect=2"
│
├─ FIGURE 2 (6 data points)
│  │
│  ├─ VARIABLE: Nu
│  │  ├─ X-axis: Reynolds (Re) [2 unique: 1k, 5k]
│  │  ├─ Legend: Aspect ratio [2 unique: 2, 4]
│  │  └─ Constants: P/e=8, e/D=0.15
│  │     → Subplot 1: 2 series (Aspect=2, Aspect=4)
│  │        Title: "Nu | Conditions: P/e=8, e/D=0.15"
│  │
│  └─ VARIABLE: f
│     ├─ X-axis: Reynolds (Re) [4 unique: 1k, 5k, 10k, 20k]
│     ├─ Legend: Aspect ratio [2 unique: 2, 4]
│     └─ Constants: P/e=8, e/D=0.15
│        → Subplot 2: 2 series (Aspect=2, Aspect=4)
│           Title: "f | Conditions: P/e=8, e/D=0.15"
│
│        → OUTPUT: One figure with 2 subplots (Nu and f)
│           File: "Flow_Dynamics_in_Ribbed_Channels_Fig2.png"
│
└─ FIGURE 3 (4 data points)
   │
   ├─ VARIABLE: f
   ├─ VARIABLE: St
   │
   └─ → OUTPUT: One figure with 2 subplots
      File: "Flow_Dynamics_in_Ribbed_Channels_Fig3.png"

FINAL OUTPUT:
─────────────
Flow_Dynamics_in_Ribbed_Channels_Fig1.png  ← 1 subplot
Flow_Dynamics_in_Ribbed_Channels_Fig2.png  ← 2 subplots
Flow_Dynamics_in_Ribbed_Channels_Fig3.png  ← 2 subplots
```

---

## Decision Tree: Axis & Scale Selection

```
For each Variable in each Figure:
│
├─ Analyze variability
│  └─ For each parameter:
│     ├─ Count unique (non-NaN) values
│     ├─ If 1: Add to CONSTANTS
│     └─ If >1: Add to VARIABLES
│
├─ SELECT X-AXIS
│  ├─ If no variables:
│  │  └─ Use index (no x-axis parameter)
│  └─ Else:
│     ├─ Find parameter with MAX unique count
│     └─ If tie: Choose Reynolds (Re)
│
├─ SELECT LEGEND
│  ├─ If only 1 variable parameter:
│  │  └─ No legend
│  └─ Else:
│     ├─ Find parameter with 2ND highest unique count
│     └─ If tie: Choose first in priority list
│
└─ SELECT SCALING
   ├─ LOG-X?
   │  ├─ If X-axis = "Reynolds (Re)": YES
   │  └─ Else if range(X) > 10: YES
   │  └─ Else: NO
   │
   └─ LOG-Y?
      ├─ If range(Value) > 10: YES
      └─ Else: NO
```

---

## N/A Handling: Detailed Rules

```
WHEN LOADING:
├─ Convert all "N/A", "NA", "n/a" strings → NaN
├─ Keep numeric values as-is
└─ Keep empty cells as NaN

WHEN ANALYZING VARIABILITY:
├─ For each parameter:
│  ├─ Extract non-NaN values
│  ├─ If zero non-NaN values:
│  │  └─ Ignore parameter (skip)
│  ├─ Else if one unique non-NaN value:
│  │  └─ CONSTANT
│  └─ Else if >1 unique value:
│     └─ VARIABLE
│
└─ Don't include ignored parameters in axes or title

WHEN PLOTTING:
├─ Remove rows where X-axis is NaN
├─ Remove rows where Legend-axis is NaN
├─ Remove rows where Value is NaN
└─ Plot remaining points
```

---

## Color & Marker Assignment

```
Legend Series #1: Color #1, Marker 'o'  ← circle
Legend Series #2: Color #2, Marker 's'  ← square
Legend Series #3: Color #3, Marker '^'  ← triangle up
Legend Series #4: Color #4, Marker 'D'  ← diamond
...
Legend Series #12: Color #12, Marker 'x' ← x

(Cycles back if more than 12 series)

Colors from: seaborn.color_palette("husl", 12)
Markers: ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h', '+', 'x']
```

---

## Summary Checklist

- [x] Data loaded and cleaned (N/A → NaN)
- [x] Data grouped hierarchically
- [x] Each variable analyzed independently
- [x] Constants identified and stored
- [x] X-axis selected (highest variability)
- [x] Legend selected (2nd highest variability)
- [x] Log scaling auto-detected
- [x] Points plotted with unique colors & markers
- [x] Title includes paper, figure, and constants
- [x] PNG saved at 300 DPI
- [x] Repeat for all papers & figures

**Result**: Professional, publication-quality plots with no manual parameter specification needed! 📊
