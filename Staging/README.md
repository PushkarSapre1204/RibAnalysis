# Staging Directory for Meta-Analysis Preprocessing

This directory is used to stage raw research paper data before preprocessing into the master dataset.

## Directory Structure

Each research paper has its own subdirectory with the following files:

```
Staging/
├── P0001/                        # Any folder name (P0001, P_author_year, etc.)
│   ├── raw_data.csv              # Raw extracted data (15 columns per DATA_SCHEMA.md)
│   ├── manifest.json             # Metadata about experimental setup
│   └── clean_data.csv            # Generated locally after preprocessing
├── P0002/
│   ├── raw_data.csv
│   ├── manifest.json
│   └── clean_data.csv
```

**Folder Naming**: Folder names can be flexible:
- Serial: `P0001`, `P0002`, etc.
- Custom: `author_year`, `Smith2024`, etc.
- The preprocessor automatically adds the folder name as `paper_number` in the manifest

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
    "Study Objective": "Study description",
    "paper_number": "P0001"
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

**Automatic paper_number field**: The preprocessor automatically adds the folder name as `paper_number` in the `Paper Identification` section. This creates a permanent link between the folder name and the metadata, making it easy to track which staging folder each processed dataset came from.

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
