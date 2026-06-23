# Implementation Plan: Project Browser and View Settings

**Date:** June 18, 2026  
**Feature:** Project Browser with Figure Tabs and View Configuration Dialog

---

## Overview

Add a project browser docked to the left of the plot area that displays saved figure definitions, allows double-clicking to open each figure in a new tab, and right-clicking to delete with confirmation. Add a View menu that opens a full configuration dialog for plot style properties (markers, lines, colors, sizes). Style configuration will be persisted in a project-local config file mirroring the shape of `ribs_core/config.py`, with defaults copied on project creation and overwritten on save.

---

## Locked Design Decisions

1. **Browser Row Representation:** One row = one saved figure definition (from `ProjectState.figures`)
2. **Double-Click Behavior:** Always opens a new tab for that figure
3. **Tab Close Behavior:** Show confirmation prompt if tab has unsaved changes
4. **View Menu:** Dialog-based full configuration editor
5. **View Editor Tabs:**
   - **Markers:** Symbol, color, and size dropdowns
   - **Lines:** Color order and thickness controls
6. **Style Persistence:** Project-local config file with same shape as `ribs_core/config.py`
7. **Config File Scope:** One per project, overwritten on save, not stored in `.prj` file
8. **Default Load:** Defaults from `ribs_core/config.py` copied on project creation

---

## Implementation Steps

### Step 1: Extend Project Manager to Handle Project Config Files

**Files to Modify:**
- `ribs_core/project_manager.py`

**Changes:**
- Add project config file path to `ProjectState` (e.g., `project_root / "config.py"`)
- Add method `ProjectState.get_config_file_path()` to return path
- Add helper functions:
  - `copy_default_config_to_project(project_root: Path)` — Copy defaults from `ribs_core/config.py` to project-local config
  - `load_project_config(config_file: Path)` — Load markers, colors, line styles from project config
  - `save_project_config(config_file: Path, markers, colors, lines)` — Persist config to project config file

**Outcome:** Project creation and loading can manage a local config file.

---

### Step 2: Extend Visualiser Layout to Split View with Browser

**Files to Modify:**
- `tools/visualiser_tool/visualiser_gui.py`

**Changes:**
1. Replace the current `content_area` layout with a `ttk.PanedWindow(orient='horizontal')` split:
   - **Left pane:** Project browser (Listbox with scrollbar showing figure names)
   - **Right pane:** Existing `PlotDisplayPanel` unchanged
2. Create new class `ProjectBrowser(ttk.Frame)`:
   - Listbox showing saved figures with labels like "Fig 1: X vs Y (2D Scatter)"
   - Bind `<Double-Button-1>` to open figure in new tab
   - Bind `<Button-3>` (right-click) to show context menu with Open/Delete
3. Populate browser from `self.project.figures` whenever project is loaded or figures are saved

**Outcome:** Left-side browser displays saved figures, right-side plot area unchanged.

---

### Step 3: Add Tab Management for Figures

**Files to Modify:**
- `tools/visualiser_tool/visualiser_gui.py`

**Changes:**
1. Create new class `PlotTab`:
   - Wraps a figure and its metadata (FigureSpec, unsaved changes flag)
   - Tracks whether the displayed plot has unsaved modifications
2. Replace single `PlotDisplayPanel` with `ttk.Notebook` for tab management
3. Add methods:
   - `_open_figure_in_tab(figure_spec: FigureSpec)` — Regenerate figure from spec and open in new tab
   - `_close_tab_with_confirmation(tab_index)` — Show confirmation if unsaved changes
   - `_on_figure_double_click(index)` — Call `_open_figure_in_tab()` for clicked figure

**Outcome:** Figures can be opened in multiple tabs with close-confirmation on unsaved changes.

---

### Step 4: Add Context Menu for Browser with Delete Action

**Files to Modify:**
- `tools/visualiser_tool/visualiser_gui.py`

**Changes:**
1. In `ProjectBrowser`:
   - On right-click, create `tk.Menu` with "Open" and "Delete" options
   - "Open" calls `_on_figure_double_click()` (redundant with double-click but expected behavior)
   - "Delete" calls `_delete_figure_with_confirmation(index)`
2. Add method `_delete_figure_with_confirmation(index)`:
   - Show `messagebox.askyesno()` confirmation
   - If yes: remove from `self.project.figures`, update browser, save project
   - If no: return without action

**Outcome:** Right-click context menu on browser entries with confirmed deletion.

---

### Step 5: Add View Menu and Configuration Dialog

**Files to Modify:**
- `tools/visualiser_tool/visualiser_gui.py`

**Changes:**
1. In `_create_menu_bar()`:
   - Add new menu: `view_menu = tk.Menu(menu_bar, tearoff=0)`
   - Add command: `view_menu.add_command(label="Plot Properties", command=self._open_view_config)`
   - Add to menu bar: `menu_bar.add_cascade(label="View", menu=view_menu)`

2. Create new class `PlotPropertiesDialog(tk.Toplevel)`:
   - Left-side `ttk.Notebook` with tabs: "Markers" and "Lines"
   - **Markers tab:**
     - Dropdown for marker symbol (load from project config or defaults)
     - Dropdown for marker color (predefined colors from config)
     - Spinbox or dropdown for marker size (e.g., 30-100)
   - **Lines tab:**
     - Dropdown for line color order/palette
     - Spinbox for line thickness (e.g., 0.5-3.0)
   - Buttons: "Reset to Defaults", "Apply", "Cancel"
   - Load current values from project config on open
   - On "Apply": Save values to project config file and update plots

3. Add method `_open_view_config()`:
   - Open `PlotPropertiesDialog(self)`
   - Pass current project config

**Outcome:** View menu opens a tabbed configuration dialog for style properties.

---

### Step 6: Update Project Creation and Loading Paths

**Files to Modify:**
- `tools/visualiser_tool/visualiser_gui.py`
- `ribs_core/project_manager.py`

**Changes:**
1. In `_new_project()`:
   - After creating project root and data dir, call `copy_default_config_to_project(project_root)`
   - Load project config into app state

2. In `_open_project()`:
   - Load project config from `project.get_config_file_path()`
   - Apply loaded config to current plot rendering

3. In `_save_project()` and `_save_project_as()`:
   - Save project config if any style changes were made

**Outcome:** New projects get a default config, existing projects load and can override styles.

---

### Step 7: Update Plot Generation to Use Project Config

**Files to Modify:**
- `tools/visualiser_tool/visualiser_gui.py`

**Changes:**
1. Modify `get_bin_colors_symbols(n_bins)` to accept optional project config:
   - If project config provided, use its markers/colors
   - If not, fall back to defaults from `ribs_core/config.py`

2. Update all calls to `get_bin_colors_symbols()` in plot generation functions:
   - Pass project config when available

3. Ensure `_generate_plot()` and `_regenerate_figure_from_spec()` apply project config

**Outcome:** Plots respect project-specific style configuration.

---

### Step 8: Implement Figure Regeneration from Spec

**Files to Modify:**
- `tools/visualiser_tool/visualiser_gui.py`

**Changes:**
1. Add method `_regenerate_figure_from_spec(figure_spec: FigureSpec)`:
   - Extract papers, x_axis, y_axis, z_axis, plot_representation, binning_data from spec
   - Call existing plot generation functions with extracted data
   - Return generated figure

2. Call this method from `_on_figure_double_click()` to populate new tabs

**Outcome:** Saved figures can be fully reconstructed from their specs.

---

### Step 9: Update Project File Schema (Optional Enhancement)

**Files to Modify:**
- `ribs_core/project_manager.py`

**Changes (if needed):**
- Add optional field `config_file_path: Optional[Path]` to `ProjectState` for reference
- Keep `.prj` file focused on project structure, figures, and metadata
- Do NOT duplicate style data in `.prj`; always load from project-local config file

**Outcome:** `.prj` and project config stay separate, reducing duplication.

---

## File Structure After Implementation

```
project_root/
├── project_name.prj          # Project metadata, figures, structure
├── config.py                 # Project-local style configuration
├── Data/
│   ├── P001/
│   │   ├── raw_data.csv
│   │   ├── manifest.json
│   │   └── clean_data.csv
│   └── P002/
│       └── ...
└── clean_data_master.csv     # Aggregated data
```

---

## Testing and Verification

1. **Create new project:** Verify project config file is created with defaults
2. **Import papers:** Verify browser remains empty until figures are generated
3. **Generate plot:** Verify figure appears in browser and can be double-clicked to open in new tab
4. **Double-click figure:** Verify new tab opens (not replacing existing tabs)
5. **Close tab with unsaved changes:** Verify confirmation prompt appears
6. **Right-click figure:** Verify context menu shows Open and Delete options
7. **Delete figure:** Verify confirmation prompt, then removal from browser and project file
8. **Open View menu:** Verify configuration dialog opens with current project settings
9. **Edit style properties:** Verify Apply saves to project config and plots regenerate with new styles
10. **Save and reopen project:** Verify browser list, tabs, and style overrides are restored

---

## Key Implementation Notes

- Reuse existing Tkinter patterns from `Selected Papers listbox` and `Point Details matches_listbox`
- Existing plot generation functions remain unchanged; pass config as optional parameter
- Project config file should be valid Python (mirrors `ribs_core/config.py`) or JSON for easier parsing
- Consider backward compatibility: projects without config file should load defaults
- Closing the app should prompt to save any unsaved tab changes
- The `dirty` flag in `ProjectState` should be set when figures are added/deleted or styles change

---

## Dependency Order

1. ✅ Step 1: Project config file management (project_manager.py)
2. ✅ Step 2: Layout split with browser (visualiser_gui.py)
3. ✅ Step 3: Tab management (visualiser_gui.py)
4. ✅ Step 4: Context menu (visualiser_gui.py)
5. ✅ Step 5: View menu and config dialog (visualiser_gui.py)
6. ✅ Step 6: Project creation/loading (visualiser_gui.py + project_manager.py)
7. ✅ Step 7: Plot generation integration (visualiser_gui.py)
8. ✅ Step 8: Figure regeneration (visualiser_gui.py)
9. ⚠️  Step 9: Project file schema updates (project_manager.py, optional)

---

## Success Criteria

- [ ] Project browser displays all saved figures with descriptive labels
- [ ] Double-clicking a figure opens it in a new tab
- [ ] Closing a tab with unsaved changes prompts for confirmation
- [ ] Right-clicking a figure shows context menu with Delete option
- [ ] Deleting a figure removes it from browser and project file
- [ ] View menu opens configuration dialog
- [ ] Configuration changes save to project-local config file
- [ ] Reopening a project restores browser, tabs, and style settings
- [ ] Plots render using project-specific style configuration
- [ ] No existing functionality is broken (plots still generate, projects still save/load)
