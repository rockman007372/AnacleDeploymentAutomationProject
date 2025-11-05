from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import shutil
import sys
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
import zipfile

from build.builder import Builder
from update_schema.pipeline import SQLDeploymentPipeline


def load_config(path: str) -> dict:
    script_dir = Path(__file__).parent  # directory where main.py is located
    config_path = script_dir / path
    with open(config_path, 'r') as f:
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
        "%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logger.propagate = False # Prevent log messages being propagated to root logger when a new process is spawned
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
            dst.parent.mkdir(parents=True, exist_ok=True) # must ensure dest dir exists
            shutil.copy(src, dst)
            os.remove(src)
            logger.debug(f"Moved {src} to {dst}.")
        except Exception as e:
            logger.error(f"Error occured while moving {src} to {dst}: {e}")
            raise
    else:
        logger.warning(f"Skip {src} because the file cannot be found.")


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


def build_solution(config, logger):
    logger.info("Starting Build...")
    
    builder = Builder(config.get('build_config', {}), custom_logger=logger)
    builder.build()


def deploy_sql(config, log_dir, logger):
    logger.info("Starting SQL Deployment...")

    sql_pipeline = SQLDeploymentPipeline(
        config.get('update_schema_config', {}),
        log_directory=log_dir,
        custom_logger=logger
    )
    sql_pipeline.run()


def publish_artifacts(config, logger):
    logger.info("Publishing artifacts...")

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
            "webapp": ["web.config", "website.publishproj"],
            "service": ["Service.exe.config", "LogicLayer.dll.config"],
            "TPAPI": ["Web.config"],
        }

        for folder in folders_to_copy:
            for cfg_file in config_files.get(folder, []):
                source = dest_dir / folder / cfg_file
                dest = config_dir / folder / cfg_file
                move_file(source, dest, logger)
    
    if zip_output:
        logger.info("Zipping deployment package...")
        folders_to_zip = [str(dest_dir / f) for f in folders_to_copy]
        zip_file = dest_dir / dest_dir.name
        if seven_zip_path.exists():
            zip_with_7zip(folders_to_zip, zip_file, seven_zip_path, logger)
        else:
            zip_with_python(folders_to_zip, zip_file, logger)


def main():
    config = load_config('deployment.cfg.json')
    
    # Initialize logging directory and logger
    root_log_dir = Path(config.get('log_dir', './logs/'))
    log_dir = init_log_dir(root_log_dir)
    logger = init_logger(log_dir)

    logger.info(f"Deployment process started.")

    # Pipeline   
    build_solution(config, logger)

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="Worker") as executor:
        futures = {
            executor.submit(deploy_sql, config, log_dir, logger): "SQL Deployment",
            executor.submit(publish_artifacts, config, logger): "Artifact Publish"
        }

        for future in as_completed(futures):
            step = futures[future]
            try:
                future.result()
                logger.info(f"{step} completed.")
            except Exception:
                logger.exception(f"{step} failed.")
                sys.exit(1)
    
    logger.info(f"Deployment process completed.")

if __name__ == '__main__':
    main()
