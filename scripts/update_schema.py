import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.pipeline import SQLDeploymentPipeline

def setup_logging(log_dir: Path):
    """Sets up logging to both console and file."""
    log_file = log_dir / "update_schema.log"

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # File handler
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(threadName)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Attach handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

def load_config(path: Path) -> dict:
    with open(path, 'r') as f:
        return json.load(f)

def create_current_run_log_dir(config: dict) -> Path:
    root_log_dir = Path(config.get('log_dir', './logs/update_schema'))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return root_log_dir / f'update_schema_{timestamp}'

def get_db_connection():
    return {
        "server":   os.getenv("server", ""),
        "database": os.getenv("database", ""),
        "uid":      os.getenv("uid", ""),
        "pwd":      os.getenv("pwd", "")
    }

# If called as a script
if __name__ == "__main__":
    file_directory = Path(__file__)
    root_directory = file_directory.parent.parent
    env_path = root_directory / "configs" / ".env"
    config_path = root_directory / "configs" / "update_schema_config.json"

    load_dotenv(env_path)
    db_connection = get_db_connection()
    config = load_config(config_path)
    log_dir = create_current_run_log_dir(config)
    log_dir.mkdir(parents=True, exist_ok=True)    
    logger = setup_logging(log_dir)

    # Run the SQL deployment pipeline
    pipeline = SQLDeploymentPipeline(config, db_connection, log_directory=log_dir, custom_logger=logger)

    pipeline.run()
