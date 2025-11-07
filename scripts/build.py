import json
from typing import Dict

from builder import Builder

def load_and_validate_config(path: str) -> Dict:
    with open(path, 'r') as f:
        config = json.load(f)

    required_fields = ["solution_dir", "dev_cmd_path"]
    for field in required_fields:
        if field not in config:
            exit(1)

    return config


if __name__ == "__main__":
    config = load_and_validate_config('build.cfg.json')
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
            
    builder.build(int(response))