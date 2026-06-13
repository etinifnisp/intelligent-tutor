import os
import shutil
import glob
from pathlib import Path

def main():
    project_root = Path(__file__).resolve().parent.parent
    papers_dir = project_root / "papers"
    
    advanced_dir = papers_dir / "advanced"
    mains_dir = papers_dir / "Mains"
    old_mains_dir = papers_dir / "main"
    backup_dir = papers_dir / "old_mock_backup"
    
    print(f"Project root: {project_root}")
    print(f"Papers dir: {papers_dir}")
    
    # 1. Create backup dir
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Identify root-level PDFs in advanced_dir and move to backup
    root_advanced_pdfs = list(advanced_dir.glob("*.pdf"))
    print(f"Found {len(root_advanced_pdfs)} root-level PDFs in advanced_dir to backup.")
    for pdf in root_advanced_pdfs:
        dest = backup_dir / pdf.name
        shutil.move(str(pdf), str(dest))
        print(f"Backed up: {pdf.name} -> old_mock_backup/")
        
    # 3. Identify root-level PDFs in old_mains_dir and move to backup
    if old_mains_dir.exists():
        root_mains_pdfs = list(old_mains_dir.glob("*.pdf"))
        print(f"Found {len(root_mains_pdfs)} root-level PDFs in old_mains_dir to backup.")
        for pdf in root_mains_pdfs:
            dest = backup_dir / pdf.name
            shutil.move(str(pdf), str(dest))
            print(f"Backed up: {pdf.name} -> old_mock_backup/")
            
    # 4. Flatten Advanced PDFs: move all PDFs in subfolders to advanced_dir root
    # We walk the advanced subfolders
    advanced_nested_pdfs = []
    for root, dirs, files in os.walk(str(advanced_dir)):
        # Skip advanced_dir itself
        if Path(root) == advanced_dir:
            continue
        # Skip backup_dir if it's somehow inside (it shouldn't be)
        if "old_mock_backup" in root:
            continue
        for file in files:
            if file.lower().endswith(".pdf"):
                advanced_nested_pdfs.append(Path(root) / file)
                
    print(f"Found {len(advanced_nested_pdfs)} nested PDFs in advanced_dir.")
    for pdf in advanced_nested_pdfs:
        dest = advanced_dir / pdf.name
        # If destination already exists (due to name clash, though shouldn't happen), warn
        if dest.exists():
            print(f"Warning: Destination {dest.name} already exists. Appending suffix.")
            dest = advanced_dir / f"{pdf.stem}_nested{pdf.suffix}"
        shutil.move(str(pdf), str(dest))
        print(f"Moved: {pdf.name} -> advanced/")
        
    # 5. Flatten Mains PDFs: move all PDFs in subfolders to mains_dir root
    mains_nested_pdfs = []
    for root, dirs, files in os.walk(str(mains_dir)):
        if Path(root) == mains_dir:
            continue
        for file in files:
            if file.lower().endswith(".pdf"):
                mains_nested_pdfs.append(Path(root) / file)
                
    print(f"Found {len(mains_nested_pdfs)} nested PDFs in mains_dir.")
    for pdf in mains_nested_pdfs:
        dest = mains_dir / pdf.name
        if dest.exists():
            print(f"Warning: Destination {dest.name} already exists. Appending suffix.")
            dest = mains_dir / f"{pdf.stem}_nested{pdf.suffix}"
        shutil.move(str(pdf), str(dest))
        print(f"Moved: {pdf.name} -> Mains/")
        
    # 6. Delete empty subfolders recursively
    def delete_empty_dirs(path: Path):
        for root, dirs, files in os.walk(str(path), topdown=False):
            for d in dirs:
                dir_path = Path(root) / d
                try:
                    # check if empty
                    if not any(dir_path.iterdir()):
                        dir_path.rmdir()
                        print(f"Removed empty dir: {dir_path.relative_to(project_root)}")
                except Exception as e:
                    print(f"Could not remove {dir_path}: {e}")
                    
    delete_empty_dirs(advanced_dir)
    delete_empty_dirs(mains_dir)
    
    # Remove old_mains_dir if empty
    if old_mains_dir.exists():
        try:
            if not any(old_mains_dir.iterdir()):
                old_mains_dir.rmdir()
                print(f"Removed empty old mains dir: {old_mains_dir.relative_to(project_root)}")
            else:
                print(f"Warning: old mains dir is not empty: {list(old_mains_dir.iterdir())}")
        except Exception as e:
            print(f"Could not remove old mains dir: {e}")
            
    # Verify final counts
    final_adv = list(advanced_dir.glob("*.pdf"))
    final_main = list(mains_dir.glob("*.pdf"))
    print(f"Final Advanced count: {len(final_adv)} (Expected: 44)")
    print(f"Final Mains count: {len(final_main)} (Expected: 118)")
    print("Consolidation finished.")

if __name__ == "__main__":
    main()
