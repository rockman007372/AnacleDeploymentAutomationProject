from datetime import datetime
import json
import logging
import sys
from typing import Dict
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.builder import Builder

def load_config(path: Path) -> Dict:
    with open(path, 'r') as f:
        return json.load(f)

def setup_logging(log_dir):
    """Sets up logging to both console and file."""
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f'build_{timestamp}.log'

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

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

if __name__ == "__main__":
    root_dir = Path(__file__).parent.parent
    config = load_config(root_dir / "configs" / "build_config.json")
    log_dir = Path(root_dir / "logs" / "build")
    setup_logging(log_dir)
    builder = Builder(config)

    available_projects = ""
    for i, project_name in enumerate(builder.get_projects()):
        available_projects += f"{i+1}. {project_name}\n"

    print("Available projects:")
    print(f"{available_projects}")
    while True:
        response = input("Indicate project to build by its id. If none provided, build all: ").strip()
        if not response:
            break
        if response.isnumeric() and int(response) > 0 and int(response) <= len(available_projects):
            break
        print("Please indicate a valid project id.")
    
    if not response:
        builder.build()
    else:
        builder.build(int(response))

    logger = logging.getLogger()
    logger.info("Publishing the build artifacts...")
    builder.publish()