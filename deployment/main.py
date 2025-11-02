import sys
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime

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
    if (builder.build()):
        logger.info("Build succeeded, proceeding to SQL deployment...")
    else:
        logger.error("Build failed, aborting SQL deployment.")
        return

    # After building, run the SQL deployment pipeline
    update_schema_config = config.get('update_schema_config', {})
    sql_pipeline = SQLDeploymentPipeline(update_schema_config, log_directory=log_dir, custom_logger=logger)
    sql_pipeline.run()

    # Publish the built artifacts concurrently

    logger.info(f"Deployment process completed.")

if __name__ == '__main__':
    main()
