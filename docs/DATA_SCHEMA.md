# Quick Reference: Data Schema

## Required Excel Column Headers (Correct Format)

Your Excel file must have these **15 columns** in any order:

### Core Data Columns (5 columns)
| # | Column Name | Type | Example | Notes |
|---|---|---|---|---|
| 1 | **Paper Title** | Text | "Heat Transfer in Ribbed Channels" | Identifier for the research paper |
| 2 | **Figure Number** | Integer | 1, 2, 3 | Plot number within the paper |
| 3 | **Point ID** | Text | "P1", "P2" | Unique identifier for each data point |
| 4 | **Variable** | Text | "Nu", "f", "St" | Dependent variable (y-axis variable) |
| 5 | **Value** | Numeric | 15.2, 0.035 | Numerical measurement for the variable |

### Parameter Columns (7 columns) - Used for Axis Selection
| # | Column Name | Type | Example | Notes |
|---|---|---|---|---|
| 6 | **Reynolds number (Re)** | Numeric or N/A | 1000, 5000, 10000 | Flow rate parameter |
| 7 | **Geometry** | Text or N/A | "Rectangular", "Trapezoidal" | **RIB geometry type** (not channel geometry) |
| 8 | **P/e** | Numeric or N/A | 8, 10, 12 | Pitch to rib height ratio |
| 9 | **e/D** | Numeric or N/A | 0.1, 0.15, 0.2 | Rib height to hydraulic diameter |
| 10 | **Alpha** | Numeric or N/A | 45, 60, 90 | Rib angle in degrees |
| 11 | **Aspect ratio** | Numeric or N/A | 2, 4, 6 | Channel aspect ratio (width/height) |
| 12 | **Number of ribbed walls** | Integer or N/A | 1, 2, 4 | Count of ribbed walls |

### Test Condition Columns (2 columns) - Shown in Title Only
| # | Column Name | Type | Example | Notes |
|---|---|---|---|---|
| 13 | **Reading on** | Text or N/A | "Wall 1", "Wall 2" | Which wall measurement was taken (test parameter) |
| 14 | **Constant factor** | Numeric or N/A | 1.0, 1.1, 1.2 | Correction or scaling factor (test parameter) |

### Additional Data Columns (1 column) - Not Used in Analysis
| # | Column Name | Type | Example | Notes |
|---|---|---|---|---|
| 15 | **Dittus-Boelter Value** | Numeric or N/A | 12.5, 15.2 | Reference correlation value (informational only) |

## Data Entry Guidelines

### For Varying Parameters (plot will use these)
- Use actual numeric or text values
- Can have different values across rows within the same Figure
- These 7 columns are analyzed to select X-axis and Legend axes

### For Test Conditions (shown in plot title)
- Use same value across all rows within the same Figure
- Appear in the subplot title
- Not used for axis selection
- Examples: "Reading on", "Constant factor"

### For Additional Data (informational only)
- Not used in plot generation
- Can be any value
- Example: "Dittus-Boelter Value" (reference comparison data)

### For Non-Applicable Values
- Use **"N/A"** exactly (case-insensitive)
- Or leave the cell empty
- These columns will be completely ignored

## Example Data Structure

```
Paper Title | Figure Number | Point ID | Variable | Value | Reynolds number (Re) | Geometry | P/e | e/D | Alpha | Aspect ratio | Number of ribbed walls | Reading on | Constant factor | Dittus-Boelter Value
---|---|---|---|---|---|---|---|---|---|---|---|---|---|---
Heat Transfer Study | 1 | P1 | Nu | 15.2 | 1000 | Rectangular | 10 | 0.1 | 45 | 2 | 1 | Wall 1 | 1.0 | 12.5
Heat Transfer Study | 1 | P2 | Nu | 18.5 | 5000 | Rectangular | 10 | 0.1 | 45 | 2 | 1 | Wall 1 | 1.0 | 15.2
Heat Transfer Study | 1 | P3 | Nu | 22.3 | 10000 | Rectangular | 10 | 0.1 | 45 | 2 | 1 | Wall 1 | 1.0 | 18.8
Friction Factor Study | 2 | P1 | f | 0.032 | 1000 | Trapezoidal | 8 | 0.15 | N/A | 4 | 2 | Wall 2 | 1.1 | N/A
Friction Factor Study | 2 | P2 | f | 0.028 | 5000 | Trapezoidal | 8 | 0.15 | N/A | 4 | 2 | Wall 2 | 1.1 | N/A
```

## Algorithm Behavior with This Schema

For each **Paper Title + Figure Number + Variable** combination, the script:

1. **Identifies Available Data**
   - Reads all 15 columns
   - Filters out columns with all "N/A" values
   
2. **Classifies Parameters** (from 7 PARAMETER_COLUMNS only)
   - **Constants**: Parameters with only 1 unique value → shown in subplot title
   - **Variables**: Parameters with 2+ unique values → candidates for X-axis and Legend
   - **Ignored**: Columns that are entirely "N/A"

3. **Collects Test Conditions** (from 2 TEST_CONDITION_COLUMNS)
   - Extracts values from "Reading on" and "Constant factor"
   - Always shown in subplot title (regardless of variation)

4. **Selects Axes** (from variable parameters only)
   - **X-Axis**: Parameter with most unique values
   - **Legend**: Parameter with second-most unique values
   - **Tie-breaker**: Reynolds number gets priority if there's a tie

5. **Creates Plot**
   - Multi-variable subplots if multiple Variables exist
   - Automatic log-log scaling if data spans multiple orders of magnitude
   - Unique colors and markers for legend items
   - Subplot title includes both constants AND test conditions
   - Overall title: `Paper Title - Figure Number`

## Common Scenarios

### Scenario 1: Reynolds Number Variation Study
```
Variable=Nu, Re varies [1000, 5000, 10000], P/e=10, Alpha=45
Reading on=Wall 1, Constant factor=1.0
→ X-axis: Reynolds number (Re) [only variable parameter]
→ Legend: None
→ Subplot title: "Nu | P/e=10, Alpha=45, Reading on=Wall 1, Constant factor=1.0"
```

### Scenario 2: Multi-Parameter Study
```
Variable=Nu, Re varies [1000, 5000], P/e varies [8, 10, 12], Alpha=45
Reading on=Wall 1, Constant factor=1.0
→ X-axis: P/e (3 values > 2 Re values)
→ Legend: Reynolds number (Re) (2 values)
→ Subplot title: "Nu | Alpha=45, Reading on=Wall 1, Constant factor=1.0"
```

### Scenario 3: Multi-Variable in Same Figure
```
Variables: Nu and f, both with Re variation
→ Creates 2 subplots (one for Nu, one for f)
→ Each subplot independently selects best axes
```

## Column Name Sensitivity

⚠️ **Important**: Column names are **case-sensitive** and must match exactly:
- ✓ Correct: `Reynolds number (Re)`
- ✗ Wrong: `reynolds number (re)`
- ✗ Wrong: `Reynolds Number (RE)`

If the script says "column not found," check spelling and capitalization.
