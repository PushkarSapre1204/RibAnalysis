"""
Cleanup script to remove all clean data CSV files from the Staging directory.

Removes:
- clean_data.csv (from each paper subdirectory)
- clean_data_log.csv (from each paper subdirectory)
- clean_data_master.csv (from Staging root)
"""

from pathlib import Path
import sys
import os

def cleanup_staging():
    """Remove all clean data CSV files from Staging directory."""
    staging_dir = Path('./Staging').resolve()
    
    if not staging_dir.exists():
        print(f"ERROR: Staging directory not found at {staging_dir}")
        return False
    
    removed_count = 0
    skipped_count = 0
    errors = []
    
    # Remove master files from Staging root
    master_files = ['clean_data_master.csv']
    
    for filename in master_files:
        filepath = staging_dir / filename
        if filepath.exists():
            try:
                os.remove(str(filepath))
                print(f"✓ Removed: {filepath}")
                removed_count += 1
            except PermissionError:
                print(f"⚠ Skipped (file in use): {filepath}")
                print(f"  Close the file in Excel/other programs and try again")
                skipped_count += 1
            except Exception as e:
                error_msg = f"✗ Failed to remove {filepath}: {e}"
                print(error_msg)
                errors.append(error_msg)
        else:
            print(f"  Skipped (not found): {filepath}")
            skipped_count += 1
    
    # Remove paper-level files from each paper subdirectory
    paper_files = ['clean_data.csv', 'clean_data_log.csv']
    
    if staging_dir.is_dir():
        for paper_dir in sorted(staging_dir.iterdir()):
            if paper_dir.is_dir():
                for filename in paper_files:
                    filepath = paper_dir / filename
                    if filepath.exists():
                        try:
                            os.remove(str(filepath))
                            print(f"✓ Removed: {filepath}")
                            removed_count += 1
                        except PermissionError:
                            print(f"⚠ Skipped (file in use): {filepath}")
                            skipped_count += 1
                        except Exception as e:
                            error_msg = f"✗ Failed to remove {filepath}: {e}"
                            print(error_msg)
                            errors.append(error_msg)
    
    print(f"\n{'='*60}")
    print(f"Cleanup complete!")
    print(f"Files removed: {removed_count}")
    if skipped_count > 0:
        print(f"Files skipped (in use): {skipped_count}")
    if errors:
        print(f"Errors encountered: {len(errors)}")
        for error in errors:
            print(f"  {error}")
        return removed_count > 0
    else:
        if removed_count > 0:
            print(f"Successfully cleaned staging directory!")
        return True

if __name__ == '__main__':
    success = cleanup_staging()
    sys.exit(0 if success else 1)
