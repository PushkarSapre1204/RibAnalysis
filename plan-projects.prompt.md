## Plan: Projects Feature

The feature should live in the visualiser app only and replace the current Staging-centric workflow with a project-centric one. I’m planning it so a project can hold multiple papers, persist raw inputs plus processed data, store figure definitions for regeneration, and support import, save, save as, and export from a toolbar-driven UI.

**Steps**
1. Define the project storage contract first: the project root, the `Data/P001`, `Data/P002`, ... layout, and the JSON `.prj` schema for figure definitions and project metadata. This is the foundation for everything else.
2. Add explicit project state to the visualiser app so it can represent a blank project, a loaded project, and a dirty/unsaved state without auto-loading `Staging/clean_data_master.csv` on startup.
3. Replace the current top-level controls with a toolbar that has File and Edit menus. File should contain New Project, Save, and Save As. Edit should contain Import Papers and Export.
4. Implement the import flow as a two-step dialog sequence: first choose a raw `.xlsx` or `.csv` file, then choose one or more `.json` metadata files, then run preprocessing and merge the result into the active project dataframe.
5. Refactor preprocessing entry so it can operate from project-owned inputs instead of only the existing staging directory. Reuse the current preprocessing engines rather than duplicating logic.
6. Implement save and save as behavior so existing project files are overwritten on Save, and Save As creates a full copy of the project directory in a new location.
7. Persist figure definitions in the `.prj` file so plots can be regenerated later from data plus config. Each figure needs to store the included papers, x/y/z variables, plot representation, and binning settings.
8. Add export support for generated figures as images, with PNG and JPG/JPEG at minimum.
9. Add the Mermaid algorithm flowchart as `algorithm.md`, covering blank project creation, import, preprocessing, save, reload, and export.
10. Validate the workflow with focused checks for blank startup, import, save, reload, figure regeneration, and export, then confirm the existing preprocessing path still behaves as expected outside the new project flow.

**Relevant files**
- `tools/visualiser_tool/visualiser_gui.py` — current app entry point, toolbar/ribbon controls, data loading, save behavior, and figure state.
- `ribs_core/preprocessor.py` — preprocessing orchestrator that currently expects staging-style paper directories.
- `ribs_core/data_loader.py` — likely needs extension or reuse for project-backed loading.
- `ribs_core/config.py` — schema and constants that may need project-related additions.
- `ribs_core/geometric_engine.py` — geometric derivation logic to reuse during import preprocessing.
- `ribs_core/baseline_engine.py` — baseline normalization logic to reuse during import preprocessing.
- `ribs_core/stitching_engine.py` — output assembly and logging logic to reuse for persistence.
- `Staging/README.md` — current storage model that the new project model will replace.
- `docs/GETTING_STARTED.md` — likely needs user-facing workflow updates.
- `algorithm.md` — Mermaid flowchart document to create for the project algorithm.

**Verification**
1. Start the visualiser with a new blank project and confirm no data is auto-loaded.
2. Import a raw file and metadata, then confirm preprocessing runs and the processed dataframe is attached to the project.
3. Save a project and verify the expected directory layout plus `.prj` file are created.
4. Reopen the saved project and confirm figures regenerate from stored definitions.
5. Export a figure to PNG and JPG/JPEG and confirm the files are usable.
6. Run the narrowest relevant tests or manual checks for data loading, preprocessing, and visualiser behavior after implementation.

**Decisions captured**
- Visualiser only, not the verification tool.
- Multiple papers can be added to a single project.
- Persist raw imported files, processed data, figure definitions, and exported images.
- `.prj` should be JSON.
- Paper folders should be auto-numbered `P001`, `P002`, and so on.
- The new project folder should replace Staging as the canonical data root.
- Save As should create a full copy of the project directory.
- `algorithm.md` should contain the Mermaid flowchart.
- Export should support PNG and JPG/JPEG at minimum.

**Next Considerations**
1. Confirm whether the import flow should support importing multiple raw files in one operation, or whether repeated imports are the intended way to add more papers.
2. Decide whether a figure definition should store only plot settings and data references, or also cache a rendered thumbnail for faster project browsing.
3. Clarify whether the existing Staging directory should remain readable for backward compatibility after the project system becomes canonical.