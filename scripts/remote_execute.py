import logging
import os
import json
import sys
from datetime import datetime
from pathlib import Path
import time
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.remote import Denis4Client, Denis4ClientFactory

def load_config(path: Path) -> dict:
    with open(path, 'r') as f:
        return json.load(f)

def create_current_run_log_dir(root_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return root_dir / "logs" / "remote_execute" / f'remote_execute_{timestamp}'

def init_logger(log_dir: Path):
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
        "%(asctime)s - %(levelname)s - %(threadName)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Attach handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

if __name__ == "__main__":
    file_directory = Path(__file__)
    root_directory = file_directory.parent.parent
    config_path = root_directory / "configs" / "remote_execute_config.json"

    log_dir = create_current_run_log_dir(root_directory)
    log_dir.mkdir(parents=True, exist_ok=True)  
    logger = init_logger(log_dir)
    config = load_config(config_path)
    config["log_dir"] = log_dir

    client = Denis4ClientFactory(config).spawn_client()

    # test backup
    start = time.perf_counter()
    client.backup_no_script()
    end = time.perf_counter()

    # backup with no remote script, sequential: 85.297046 seconds
    # backup with remote script: 83.676199 seconds
    # doesnt matter, because build + publish + upload is the bottleneck
    logger.info(f"Elapsed: {end - start:.6f} seconds")

    # test transfer file
    # local_file = root_directory / "README.md"
    # remote_file = Path("./Desktop/TestFileTransfer/README.md")
    # client._upload_file(local_file, remote_file)

    # test stopping and starting services
    # client.stop_services()
    # client.start_services()
