import json
import logging
from pathlib import Path
from datetime import datetime

from script_manager import SQLDeploymentPipeline

def setup_logging(log_dir: Path):
    """Sets up logging to both console and file."""
    log_file = log_dir / "app.log"

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
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Attach handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        return json.load(f)
    
def main():
    config = load_config('config.json')

    # Create a unique log directory for this run
    root_log_dir = Path(config.get('log_dir', './logs/'))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = root_log_dir / f'run_{timestamp}'

    # Ensure the log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup logging
    logger = setup_logging(log_dir)

    # Run the SQL deployment pipeline
    pipeline = SQLDeploymentPipeline(config, log_directory=log_dir, custom_logger=logger)
    pipeline.run()

if __name__ == "__main__":
    main()
