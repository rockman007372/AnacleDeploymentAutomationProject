import json
import sys

from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.deployment import DeploymentManager

if __name__ == '__main__':
    file_directory = Path(__file__)
    root_directory = file_directory.parent.parent
    config_path = root_directory / "configs" / "deploy_config.json"
    
    with open(config_path, "r") as f:
        config = json.load(f)

    deploy_manager = DeploymentManager(config)
    deploy_manager.deploy()
