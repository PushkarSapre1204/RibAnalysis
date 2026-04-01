# Staging Directory for Meta-Analysis Preprocessing

This directory is used to stage raw research paper data before preprocessing into the master dataset.

## Directory Structure

Each research paper has its own subdirectory with the following files:

```
Staging/
├── [paper_name]/
│   ├── raw_data.csv          # Raw extracted data (15 columns per DATA_SCHEMA.md)
│   ├── manifest.json         # Metadata about experimental setup and constants
│   └── clean_data.csv        # Generated locally after preprocessing
```

## Files per Paper

### raw_data.csv
Expected 15-column schema:

**Core Data (5 columns)**:
- Paper Title
- Figure Number
- Point ID
- Variable
- Value

**Parameters (7 columns)**:
- Reynolds number (Re)
- Geometry
- P/e
- e/D
- Alpha
- Aspect ratio
- Number of ribbed walls

**Test Conditions (2 columns)**:
- Reading on
- Constant factor

**Additional (1 column)**:
- Dittus-Boelter Value

For detailed schema, see: `docs/DATA_SCHEMA.md`

### manifest.json
Metadata about the paper's experimental setup. Example structure:

```json
{
  "Paper Identification": {
    "Title": "Paper Title",
    "Authors/Year": "Author(s) Year",
    "Study Objective": "Study description"
  },
  "Experimental Apparatus & Dimensions": {
    "Channel Geometry": ["value"],
    "Channel Dimensions": {
      "Width": [20],
      "Height": [10],
      "Length": [100]
    },
    "Hydraulic Diameter (Dh)": [null],
    "Aspect Ratio (W/H)": [null],
    "Rib Dimensions": {
      "Width": [0.5],
      "Height": [0.5],
      "Pitch": [2.6]
    },
    "e/Dh": [null],
    "P/e": [null],
    "Angle of attack": [45]
  },
  "Boundary & Flow Conditions": {
    "Reynolds Number Range": [[1000, 10000]],
    "Fluid Properties": {"Pr": 0.71},
    "Thermal Boundary Condition": "Constant heat flux",
    "Heating Setup": "description",
    "Number of Ribbed Walls": [1],
    "Surface Curvature": "Flat"
  },
  "Data Reduction & Normalization": {
    "Smooth Baseline (Heat Transfer)": "Dittus-Boelert",
    "Smooth Baseline (Friction)": "Blasius",
    "Reported Dependent Variables": ["Nu", "f"],
    "Uncertainty": "±5%"
  },
  "Figures of Interest": [1, 2, 3]
}
```

**Note on varying parameters**: If a parameter (e.g., P/e, Alpha) was varied in the study, list it as the second array element indicator in the manifest. This triggers the "Safety Trigger" — the preprocessor will NOT auto-fill N/A values for varied parameters.

### clean_data.csv
Generated output after preprocessing. Includes:
- All raw data columns
- Source tracking columns ([Param]_Source)
- Normalized standard ratio columns
- Metadata tracking (Prandtl number, baseline method used)

## Workflow

1. **Extract data from paper**: Use charts, tables, or reported data to create raw_data.csv
2. **Document setup**: Fill in manifest.json with experimental constants
3. **Run preprocessor**: Execute `python -m ribs_core.preprocessor Staging/[paper_name]`
4. **Review clean_data.csv**: Verify derivations and processing decisions
5. **Check logs**: Review JSON logs in `preprocessing_logs/[paper_name]/` for detailed processing decisions

## Master Output

After processing all papers, the master file is generated:

```
data/clean_data_master.csv
```

This aggregates all clean_data.csv files from all papers, ready for analysis and visualization.
