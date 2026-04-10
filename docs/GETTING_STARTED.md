
# GETTING STARTED - First Time Setup

Welcome! This guide will get you up and running in 5 minutes.

## Step 1: Verify Python Installation (1 min)

Open PowerShell and check Python is installed:

```powershell
python --version
```

**Expected output:** Python 3.7 or higher (e.g., `Python 3.9.7`)

If not installed, download from https://www.python.org/downloads/

---

## Step 2: Install Dependencies (2 min)

In the same PowerShell window, navigate to the script directory:

```powershell
cd "C:\Users\Pushkar\OneDrive - KTH\Thesis\Ribs"
```

Install all required packages:

```powershell
pip install -r requirements.txt
```

**What it installs:**
- pandas (data manipulation)
- matplotlib (plotting)
- seaborn (styling)
- numpy (numerical)
- openpyxl (Excel support)

Expected time: 30-60 seconds

---

## Step 3: Verify Installation (1 min)

Test the installation:

```powershell
python -c "import pandas, matplotlib, seaborn; print('✓ All imports successful!')"
```

**Expected output:**
```
✓ All imports successful!
```

If you see errors, run the pip install command again.

---

## Step 4: Try the Example (1 min)

Generate sample data and test the script:

```powershell
python example_usage.py
```

**What it does:**
1. Creates sample Excel data (`master_research_data.xlsx`)
2. Analyzes the data
3. Generates plots in `./plots/` directory
4. Shows completion message

**Expected output:**
```
======================================================================
RESEARCH DATA VISUALIZATION PIPELINE
======================================================================

[1] Loading data...
Loaded data: 14 rows, 11 columns
...
[3] Generating plots...
  Processing: Flow Dynamics in Ribbed Channels... Fig 1
Saved: ./plots/Flow_Dynamics_in_Ribbed_Channels_Fig1.png
...
======================================================================
COMPLETE! Generated 3 figure(s)
Outputs saved to: C:\...\Ribs\plots
======================================================================
```

---

## Step 5: Check Your Output

Navigate to the `plots` folder:

```powershell
explorer plots
```

You should see PNG files like:
- `Flow_Dynamics_in_Ribbed_Channels_Fig1.png`
- `Heat_Transfer_Enhancement_Study_Fig2.png`
- `Pressure_Drop_Analysis_Fig3.png`

Open them to verify the plots look correct!

---

## Step 6: Use With Your Own Data

### Prepare Your Excel File

Create an Excel file with these columns:
```
Paper Title | Figure Number | Point ID | Variable | Value | Reynolds number (Re) | Geometry | P/e | e/D | Alpha | Aspect ratio | Number of ribbed walls | Reading on | Constant factor | Dittus-Boelter Value
```

Example:
```
My Study   | 1             | P1       | Nu       | 15.2  | 1000                | Rectangular | 10  | 0.1 | 45    | 2            | 1                      | Wall 1     | 1.0             | 12.5
My Study   | 1             | P2       | Nu       | 18.5  | 5000                | Rectangular | 10  | 0.1 | 45    | 2            | 1                      | Wall 1     | 1.0             | 15.2
```

Use `N/A` for missing values.

### Run the Script

```powershell
python -c "from Verification import process_research_data; process_research_data('your_file.xlsx', 'my_plots')"
```

Replace:
- `your_file.xlsx` with your Excel filename
- `my_plots` with desired output folder

### Check Results

```powershell
explorer my_plots
```

Your plots are ready! 📊

---

## Meta-Analysis Preprocessing Pipeline

Before using the visualization pipeline, you may need to preprocess raw research data from multiple papers. The preprocessing pipeline:

1. **Processes geometric parameters** — Derives missing values (e.g., Aspect Ratio, e/D) from atomic components
2. **Normalizes baselines** — Converts author-reported ratios to standard baselines (Dittus-Boelert for Nu, Blasius for f)
3. **Aggregates papers** — Combines individual paper datasets into a master CSV

### Setup: Create Staging Directory Structure

Create a `Staging` folder with the following structure for each paper:

```
Staging/
├── paper_name_1/
│   ├── raw_data.csv      # 15-column CSV with experimental data (see DATA_SCHEMA.md)
│   └── manifest.json     # Metadata about experimental setup (see Staging/README.md)
├── paper_name_2/
│   ├── raw_data.csv
│   └── manifest.json
└── ...
```

For detailed template, see: `Staging/README.md`

### Running the Preprocessor

Once you have staged all paper directories, run:

```powershell
python -m ribs_core.preprocessor ./Staging --verbose
```

The preprocessor will:
1. Process each paper in `Staging/`
2. Generate `clean_data.csv` and `clean_data_log.csv` locally in each paper directory
3. Create `Staging/clean_data_master.csv` with all papers aggregated (schema only)
4. Save decision logs in `preprocessing_logs/`

**Output files:**
- `Staging/[paper_name]/clean_data.csv` — Processed data for each paper (schema columns only)
- `Staging/[paper_name]/clean_data_log.csv` — Source tracking and processing metadata
- `Staging/clean_data_master.csv` — Master file ready for visualization (schema columns only)

### Preprocessor Features

**Safety Trigger**: Protects against auto-filling when parameters were varied
- If a parameter is listed as "varied" in manifest, it won't be auto-filled with N/A values

**Geometric Derivations**: Automatically calculates missing parameters  
- Aspect Ratio: $W/H$
- Relative Roughness: $e/D_h$ (with fallback to $D_h = \frac{2WH}{W+H}$)
- Pitch-to-Height: $P/e$

**Source Tracking**: Every parameter gets a `[Param]_Source` column showing:
- `raw` — Value from raw_data.csv
- `metadata` — Value from manifest.json
- `derived` — Calculated from atomic components
- `unfilled` — Could not be filled (Missing atomic components or Safety Trigger blocked it)

**Baseline Normalization**: Converts to standard correlations
- If author used standard baseline (Dittus-Boelert, Blasius) → keeps as-is
- If author used non-standard method (Petukhov, Gnielinski, Experimental) → "Uncover & Reconvert":
  1. Back-calculates raw Nu/f using author's formula
  2. Recalculates using standard correlation
  3. Generates new standard ratio

### Example: Complete Workflow

```powershell
# 1. Stage your papers
mkdir Staging\Paper_Smith_2024
# Copy raw_data.csv and manifest.json into Paper_Smith_2024/

# 2. Run preprocessing
python -m ribs_core.preprocessor ./Staging

# 3. Check results
Get-Content Staging/clean_data_master.csv | Select-Object -First 5

# 4. Use with visualization
python -c "from ribs_core.data_loader import process_research_data; process_research_data('./data/clean_data_master.csv')"
```

---

## Troubleshooting

### Issue: "python: command not found"
**Solution**: Python not installed or not in PATH
- Install Python from https://www.python.org/downloads/
- **Important**: Check "Add Python to PATH" during installation

### Issue: "No module named pandas"
**Solution**: Dependencies not installed
- Run: `pip install -r requirements.txt`
- Wait for completion (1-2 minutes)

### Issue: "Excel file not found"
**Solution**: File path incorrect
- Use full path: `"C:\Users\...\Ribs\your_file.xlsx"`
- Or put file in same directory as script

### Issue: "No valid data points"
**Solution**: Data filtering issue
- Check that Value column is numeric
- Check that parameter columns have some non-N/A values
- Verify Figure Number is numeric

### Issue: Plots look wrong
**Solution**: Data values issue
- Make sure Value column contains numbers, not text
- Check for unexpected "N/A" values
- Verify Reynolds number is numeric

---

## Optional: Customize Behavior

Edit `Verification.py` to customize:

```python
# Change colors
COLORS = sns.color_palette("Set2", 12)

# Change parameter categorization
PARAMETER_COLUMNS = [
    'Reynolds number (Re)',
    'Geometry',
    'P/e',
    'e/D',
    'Alpha',
    'Aspect ratio',
    'Number of ribbed walls',
    'Your_Custom_Parameter',  # Add here to analyze for axes
]

TEST_CONDITION_COLUMNS = [
    'Reading on',
    'Constant factor',
    'Your_Test_Parameter',  # Add here to show in titles only
]

# Change output DPI
OUTPUT_DPI = 600  # Higher quality
```

Then run as normal - script uses new settings automatically!

---

## Tips for Best Results

### 1. Data Quality
- Ensure Value column is numeric (no text)
- Use "N/A" consistently for missing values
- Give meaningful Variable names (Nu, f, St, etc.)

### 2. File Organization
- Put Excel file in same folder as script
- Or use full file paths
- Use meaningful paper titles (used in filenames)

### 3. Understanding Output
- Subplots = multiple variables in same figure
- X-axis = parameter with most variation
- Legend = parameter with second-most variation
- Title = constant parameters (test conditions)

### 4. Publication Use
- Output is 300 DPI (suitable for print)
- PNG format (universal support)
- Size ~3-4 inches (adjustable in config)

---

## What Happens Behind the Scenes

When you run the script, it:

1. **Loads** your Excel data
2. **Groups** by Paper Title → Figure Number
3. **Analyzes** which parameters vary
4. **Selects** best axes automatically
5. **Detects** if log scaling is needed
6. **Generates** publication-quality plots
7. **Saves** as PNG files

No manual configuration of axes needed! The script is truly parameter-agnostic.

---

## Next Steps

### Quick Reference
- See: `QUICKSTART.md` (5 min read)

### Full Documentation
- See: `README.md` (15 min read)

### Understand Algorithm
- See: `ALGORITHM_GUIDE.md` (10 min read)

### Run Tests
- See: `test_visualizer.py` (unit tests)

### Customize Behavior
- Edit: `config.py` (well-documented)

---

## Success Checklist

- [ ] Python 3.7+ installed
- [ ] Ran `pip install -r requirements.txt`
- [ ] Ran `python example_usage.py` successfully
- [ ] Saw PNG files in `plots/` folder
- [ ] Opened PNG files and verified appearance
- [ ] Prepared your own Excel data
- [ ] Ran script with your data
- [ ] Got plots in output folder

**Completed all?** Congratulations! You're ready to use the tool. 🎉

---

## Quick Command Reference

```powershell
# Navigate to script directory
cd "C:\Users\Pushkar\OneDrive - KTH\Thesis\Ribs"

# Install dependencies
pip install -r requirements.txt

# Test with example data
python example_usage.py

# Run with your data
python -c "from Verification import process_research_data; process_research_data('your_file.xlsx')"

# Run unit tests
python test_visualizer.py

# View output
explorer plots
```

---

## Support

If you get stuck:

1. **Check**: QUICKSTART.md
2. **Check**: README.md
3. **Read**: ALGORITHM_GUIDE.md
4. **Run**: test_visualizer.py
5. **Review**: example_usage.py
6. **Edit**: config.py for customization

---

**Ready?** Go to Step 1 above or skip straight to Step 4 if Python is installed! 🚀

---

Version 1.0 | March 12, 2026
