import json
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
import subprocess
import sys

def log(msg, file=None):
    print(msg)
    if file:
        with open(file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

def create_dir(path, log_file):
    try:
        os.makedirs(path, exist_ok=True)
        log(f"  [CREATED] {path}", log_file)
    except Exception as e:
        log(f"  [ERROR] Unable to create {path}: {e}", log_file)
        sys.exit(1)

def copy_folder(name, src, dst, log_file):
    log(f"  Copying {name} files...", log_file)
    if not os.path.exists(src):
        log(f"  [ERROR] Source folder missing: {src}", log_file)
        return
    try:
        shutil.copytree(src, dst, dirs_exist_ok=True)
        log(f"  [OK] {name} files copied", log_file)
    except Exception as e:
        log(f"  [ERROR] Failed to copy {name} files: {e}", log_file)
    log("", log_file)

def move_config(path, config_dir, log_file):
    if os.path.exists(path):
        try:
            os.makedirs(config_dir, exist_ok=True)
            shutil.move(path, config_dir)
            log(f"  [MOVED] {path}", log_file)
        except Exception as e:
            log(f"  [ERROR] Failed to move {path}: {e}", log_file)
            sys.exit(1)
    else:
        log(f"  [SKIPPED] Not found: {path}", log_file)

def zip_with_python(folders, zip_path, log_file):
    """Fallback ZIP implementation using Python's zipfile."""
    log(f"  Compressing with Python zipfile: {zip_path}", log_file)
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for folder in folders:
                for root, _, files in os.walk(folder):
                    for f in files:
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, os.path.dirname(folders[0]))
                        z.write(full_path, rel_path)
        log("  [OK] Deployment package created successfully", log_file)
    
    except Exception as e:
        log(f"  [ERROR] Failed to create deployment package: {e}", log_file)
        sys.exit(1)

def zip_with_7zip(folders, zip_path, sevenzip_path, log_file):
    """Attempt to compress using external 7z.exe."""
    try:
        args = [sevenzip_path, 'a', '-tzip', str(zip_path)] + [str(f) for f in folders] + ['-mx=9']
        
        log(f"  Running: {' '.join(args)}", log_file)
        result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            log("  [OK] Deployment package created successfully (7-Zip)", log_file)
        else:
            log(f"  [ERROR] 7-Zip failed with code {result.returncode}", log_file)
            log(result.stderr, log_file)
            sys.exit(1)
    
    except FileNotFoundError:
        log("  [WARN] 7-Zip not found, falling back to Python zipfile", log_file)
        zip_with_python(folders, zip_path, log_file)
    
    except Exception as e:
        log(f"  [ERROR] Failed to run 7-Zip: {e}", log_file)
        zip_with_python(folders, zip_path, log_file)

def load_and_validate_config(config_path: str) -> dict:
    """Load and validate the deployment config JSON."""
    required_fields = {
        "solutionDir": str,
        "destinationDir": str,
        "foldersToCopy": list,
        "removeConfigFiles": bool,
        "zipOutput": bool,
        "use7Zip": bool,
        "sevenZipPath": str
    }

    # Load JSON
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read config file: {e}")
        sys.exit(1)

    # Validate required fields
    missing = [key for key in required_fields if key not in config]
    if missing:
        print(f"[ERROR] Missing required config keys: {', '.join(missing)}")
        sys.exit(1)

    # Validate types
    for key, expected_type in required_fields.items():
        if not isinstance(config[key], expected_type):
            print(f"[ERROR] Invalid type for '{key}': expected {expected_type.__name__}, got {type(config[key]).__name__}")
            sys.exit(1)

    # Extra validation: check folder existence
    if not Path(config["solutionDir"]).exists():
        print(f"[ERROR] Solution directory not found: {config['solutionDir']}")
        sys.exit(1)

    if config["use7Zip"] and not Path(config["sevenZipPath"]).exists():
        print(f"[ERROR] 7-Zip executable not found: {config['sevenZipPath']}")
        # falls back to Python zipfile if path not existing

    # Everything valid
    return config

def main():
    if len(sys.argv) < 2:
        print("Usage: python deploy.py config.json")
        sys.exit(1)

    cfg = load_and_validate_config(sys.argv[1])

    # Config
    solution_dir: Path = Path(cfg["solutionDir"])
    dest_root: Path = Path(cfg["destinationDir"])
    sevenzip_path: Path = Path(cfg.get("sevenZipPath", r"C:\Program Files\7-Zip\7z.exe"))
    folders_to_copy = cfg.get("foldersToCopy", [])
    remove_config: bool = cfg.get("removeConfigFiles", False)
    zip_output: bool = cfg.get("zipOutput", False)
    use_7zip: bool = cfg.get("use7Zip", False)

    # Date-based destination
    date_tag: str = datetime.now().strftime("%Y%m%d")
    dest_dir: Path = dest_root / f"UAT_{date_tag}"
    log_file: Path = dest_dir / f"UAT_{date_tag}.log"
    zip_file: Path = dest_dir / f"UAT_{date_tag}.zip"

    # Create destination directory
    try:
        os.makedirs(dest_dir, exist_ok=True)
        print(f"Created destination directory {dest_dir}\n")
    except Exception as e:
        print(f"Unable to create destination directory {dest_dir}: {e}")
        sys.exit(1)

    # Clear any existing log file
    if log_file:
        open(log_file, "w", encoding="utf-8").close()

    # Header
    log("="*75, log_file)
    log("                  UAT DEPLOYMENT BUILD LOG", log_file)
    log("="*75, log_file)
    log(f"Start Time: {datetime.now().strftime('%Y%m%d_%H%M%S')}", log_file)
    log("", log_file)

    # Configuration
    log("[CONFIGURATION]", log_file)
    log(f"  Solution Directory   : {cfg['solutionDir']}", log_file)
    log(f"  Destination Directory: {cfg['destinationDir']}", log_file)
    log(f"  Folders To Copy      : {', '.join(cfg['foldersToCopy'])}", log_file)
    log(f"  Remove Config Files  : {cfg['removeConfigFiles']}", log_file)
    log(f"  Zip Output           : {cfg['zipOutput']}", log_file)
    log(f"  Using 7-Zip          : {cfg['use7Zip']}", log_file)
    log("", log_file)

    # Step 1: Create directories
    log("[STEP 1/5] Creating Directory Structure", log_file)
    for sub in ["webapp", "service", "TPAPI", "configs"]:
        create_dir(dest_dir / sub, log_file)
    log("", log_file)

    # Step 2: Copy folders
    log("[STEP 2/5] Copying Files", log_file)
    src_map = {
        "webapp": solution_dir / "webapp",
        "service": solution_dir / "service" / "bin" / "debug",
        "TPAPI": solution_dir / "AnacleAPI.Interface" / "bin" / "app.publish",
    }
    for folder in folders_to_copy:
        copy_folder(folder, src_map.get(folder, ""), dest_dir / folder, log_file)
    log("", log_file)

    # Step 3: Config file management
    if remove_config:
        log("[STEP 3/5] Managing Configuration Files", log_file)
        config_dir = dest_dir / "configs"

        config_files = {
            "webapp": ["web.config", "web.config.bak", "website.publishproj"],
            "service": ["Service.exe.config", "LogicLayer.dll.config"],
            "TPAPI": ["Web.config"],
        }

        for folder in folders_to_copy:
            for cfg_file in config_files.get(folder, []):
                source = dest_dir / folder / cfg_file
                dest = config_dir / folder
                move_config(source, dest, log_file)

        log("", log_file)

    # Step 4: Zip
    if zip_output:
        log("[STEP 4/5] Creating Deployment Package", log_file)
        folders = [str(dest_dir / f) for f in folders_to_copy]
        if use_7zip and sevenzip_path.exists():
            zip_with_7zip(folders, zip_file, str(sevenzip_path), log_file)
        else:
            log("  [INFO] Falling back to Python zipfile", log_file)
            zip_with_python(folders, zip_file, log_file)
        log("", log_file)

    # Step 5: Complete
    log("[STEP 5/5] Build Complete", log_file)
    log("", log_file)
    
    log("="*75, log_file)
    log("                     BUILD SUCCESSFUL", log_file)
    log("="*75, log_file)
    log(f"End Time: {datetime.now().strftime('%Y%m%d_%H%M%S')}", log_file)
    log("", log_file)
    log(f"Deployment package is ready at: {dest_dir}", log_file)

    # Open log and destination folder on Windows
    if os.name == 'nt':
        subprocess.Popen(['notepad.exe', str(log_file)], shell=True)
        os.startfile(dest_dir)

if __name__ == "__main__":
    main()
