import os
import shutil
import sys
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
import zipfile

sys.path.append('../')

from build.build_manager import Builder
from update_schema.script_manager import SQLDeploymentPipeline

def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        return json.load(f)

def init_logger(log_dir: Path) -> logging.Logger:
    log_file = log_dir / f'deployment.log'

    logger = logging.getLogger(f"deployment-{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger

def init_log_dir(base_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = base_dir / f'deployment_{timestamp}'
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir 

def copy_folder(src: Path, dst: Path, logger: logging.Logger):
    try:
        if not src.exists():
            raise NotADirectoryError(f"Source directory {src} does not exist")
        shutil.copytree(src, dst, dirs_exist_ok=True) # Create dst directory automatically
        logger.debug(f"Copied {src} to {dst}.")

    except Exception as e:
        logger.error(f"Error occured while copying {src} to {dst}: {e}")
        raise 
        

def move_file(src: Path, dst: Path, logger: logging.Logger):
    if src.exists():
        try:
            dst.mkdir(parents=True, exist_ok=True) # must ensure dest dir exists
            shutil.move(src, dst)
            logger.debug(f"Moved {src} to {dst}.")
        except Exception as e:
            logger.error(f"Error occured while moving {src} to {dst}: {e}")
            raise
    else:
        logger.info(f"Skip {src} because the file cannot be found.")

def zip_with_7zip(folders, zip_path, sevenzip_path, logger: logging.Logger):
    """Attempt to compress using external 7z.exe."""
    try:
        args = [sevenzip_path, 'a', '-tzip', str(zip_path)] + [str(f) for f in folders] + ['-mx=9']
        
        result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            logger.info(f"Deployment package created successfully (7-Zip): {zip_path}")
        else:
            logger.error(f"7-Zip failed with code {result.returncode}")
            sys.exit(1)
    
    except FileNotFoundError:
        logger.warning("7-Zip not found, falling back to Python zipfile")
        zip_with_python(folders, zip_path, logger)
    
    except Exception as e:
        logger.warning("7-Zip not found, falling back to Python zipfile")
        zip_with_python(folders, zip_path, logger)

def zip_with_python(folders, zip_path, logger: logging.Logger):
    """Fallback ZIP implementation using Python's zipfile."""
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for folder in folders:
                for root, _, files in os.walk(folder):
                    for f in files:
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, os.path.dirname(folders[0]))
                        z.write(full_path, rel_path)
        logger.info(f"Deployment package created successfully: {zip_path}")
    
    except Exception as e:
        logger.error(f" Failed to create deployment package: {e}")
        sys.exit(1)

def main():
    config = load_config('deployment.cfg.json')
    
    # Initialize logging directory and logger
    root_log_dir = Path(config.get('log_dir', './logs/'))
    log_dir = init_log_dir(root_log_dir)
    logger = init_logger(log_dir)

    logger.info(f"Deployment process started.")

    # Build the solution 
    logger.info("Starting build process...")
    build_config = config.get('build_config', {})
    builder = Builder(build_config, custom_logger=logger)
    builder.build()

    # After building, run the SQL deployment pipeline
    logger.info("Starting SQL deployment process...")
    update_schema_config = config.get('update_schema_config', {})
    sql_pipeline = SQLDeploymentPipeline(update_schema_config, log_directory=log_dir, custom_logger=logger)
    sql_pipeline.run()

    # Publish the built artifacts concurrently
    solution_dir: Path = Path(config["build_config"]["solution_dir"])
    dest_dir: Path = Path(config["destination_dir"]) / f"UAT_{datetime.now().strftime("%Y%m%d")}"
    zip_output: bool = config.get("zip_output", True)
    seven_zip_path: Path = Path(config.get("7zip_path", "C:/Program Files/7-Zip/7z.exe"))
    remove_config_files = config.get("remove_config_files", True)

    folders_to_copy = ["webapp", "service", "TPAPI"] 
    src_map = {
        "webapp": solution_dir / "webapp",
        "service": solution_dir / "service" / "bin" / "debug",
        "TPAPI": solution_dir / "AnacleAPI.Interface" / "bin" / "app.publish",
    }

    logger.info("Copying deployment folders...")
    for folder in folders_to_copy:
        copy_folder(src_map[folder], dest_dir / folder, logger)

    if remove_config_files:
        logger.info("Removing config files...")
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
                move_file(source, dest, logger)
    
    if zip_output:
        logger.info("Zipping deployment package...")
        folders_to_zip = [str(dest_dir / f) for f in folders_to_copy]
        zip_file = dest_dir / dest_dir.name
        if seven_zip_path.exists():
            zip_with_7zip(folders_to_zip, zip_file, seven_zip_path, logger)
        else:
            zip_with_python(folders_to_zip, zip_file, logger)
    
    logger.info(f"Deployment process completed.")

if __name__ == '__main__':
    main()
