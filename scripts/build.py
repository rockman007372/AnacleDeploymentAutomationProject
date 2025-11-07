import json
import sys
from typing import Dict
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.builder import Builder

def load_and_validate_config(path: Path) -> Dict:
    with open(path, 'r') as f:
        config = json.load(f)

    required_fields = ["solution_dir", "dev_cmd_path"]
    missing_fields = [k for k in required_fields if k not in config]
    if missing_fields:
        print(f"Missing required field: {missing_fields}")
        exit(1)

    return config


if __name__ == "__main__":
    root_dir = Path(__file__).parent.parent
    config = load_and_validate_config(root_dir / "configs" / "build_config.json")
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