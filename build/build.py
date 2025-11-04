import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

class Builder:
    def __init__(self, config: Dict, custom_logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = custom_logger or self._setup_logging(Path(config.get('log_dir', './logs/')))

    def _setup_logging(self, log_dir: Path):
        """Sets up logging to both console and file."""
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f'build_{timestamp}.log'

        logger = logging.getLogger(f"Builder-{timestamp}")
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

    def get_projects(self):
        return ["LogicLayer", "Service", "AnacleAPI.Interface"]

    def run_command(self, command: str, step_name: str):
        self.logger.info(f"{step_name}...")
        self.logger.debug(f"Command: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        self.logger.debug(result.stdout)
        if result.returncode != 0:
            self.logger.error(result.stderr)
            raise RuntimeError(f"{step_name} failed: {result.stderr}")
        self.logger.info(f"{step_name} completed successfully.")

    def build(self, project_id: Optional[int]=None):
        try:
            solution_dir = Path(self.config["solution_dir"])
            dev_cmd_path = Path(self.config["dev_cmd_path"])
            if not solution_dir.exists():
                raise FileNotFoundError(f"Solution directory not found: {solution_dir}")
            if not dev_cmd_path.exists():
                raise FileNotFoundError(f"Development command prompt not found: {dev_cmd_path}")

            dev_cmd = f'"{dev_cmd_path}"'
            abell_sol = solution_dir / "abell.sln"
            interface = solution_dir / "AnacleAPI.Interface" / "AnacleAPI.Interface.csproj"

            projects = {
                1: {
                    "name": "LogicLayer",
                    "cmd": f'{dev_cmd} && msbuild {abell_sol} /t:LogicLayer:Rebuild /v:diag',
                },
                2: {
                    "name": "Service",
                    "cmd": f'{dev_cmd} && msbuild {abell_sol} /t:Service:Rebuild /v:diag',
                },
                3: {
                    "name": "AnacleAPI.Interface",
                    "cmd": f'{dev_cmd} && msbuild "{interface}" /p:DeployOnBuild=true /p:PublishProfile=DevOpsDebug /p:Configuration=Debug /v:m'
                },
            }

            # Build all if no specific project is passed
            if project_id is None:
                targets = projects.values()
            else:
                if project_id not in projects:
                    raise ValueError(f"Unknown project ID: {project_id}")
                targets = [projects[project_id]]

            for target in targets:
                self.run_command(target["cmd"], f"Building/Publishing {target['name']}")

            self.logger.info("✅ All build tasks completed successfully.")

        except Exception as e:
            self.logger.exception(f"❌ Build process failed.")
            exit(1)


def load_and_validate_config(path: str) -> Dict:
    with open(path, 'r') as f:
        config = json.load(f)

    required_fields = ["solution_dir", "dev_cmd_path"]
    for field in required_fields:
        if field not in config:
            exit(1)

    return config


def main():
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


if __name__ == "__main__":
    main()