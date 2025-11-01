from datetime import datetime
import logging
import subprocess
import json
from pathlib import Path

def setup_logging(log_dir: Path):
    """Sets up logging to both console and file."""
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f'build_{timestamp}.log'

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

def main():
    # Import deployment config
    with open('deployment.cfg.json', 'r') as cfg_file:
        config = json.load(cfg_file)

    solution_dir: str = config['solution_dir']
    if not Path(solution_dir).exists():
        raise FileNotFoundError(f"Solution directory not found: {solution_dir}")

    logic_layer_path: str = f"{solution_dir}/LogicLayer/LogicLayer.csproj"
    service_path: str = f"{solution_dir}/Service/Service.csproj"
    interface_path: str = f"{solution_dir}/AnacleAPI.Interface/AnacleAPI.Interface.csproj"

    dev_cmd_path: str = config['dev_cmd_path']
    if not Path(dev_cmd_path).exists():
        raise FileNotFoundError(f"Development command prompt not found: {dev_cmd_path}")
    dev_cmd: str = f'"{dev_cmd_path}"'

    log_dir = Path(config.get('log_dir', './logs/'))
    logger = setup_logging(log_dir)

    # Build LogicLayer
    logger.info("Building LogicLayer...")
    build_command = f'{dev_cmd} && msbuild "{logic_layer_path}" /t:Rebuild /p:Platform=AnyCPU /p:Configuration=Debug'
    logger.debug(f'Command: {build_command}')
    result = subprocess.run(build_command, shell=True, capture_output=True, text=True)
    logger.debug(result.stdout)
    if result.returncode != 0:
        logger.error(result.stderr)
        raise RuntimeError(f"Failed to build LogicLayer: {result.stderr}")
    logger.info("LogicLayer built successfully.")

    # Build Service
    logger.info("Building Service...")
    build_command = f'{dev_cmd} && msbuild "{service_path}" /t:Rebuild /p:Platform=AnyCPU /p:Configuration=Debug'
    logger.debug(f'Command: {build_command}')
    result = subprocess.run(build_command, shell=True, capture_output=True, text=True)
    logger.debug(result.stdout)
    if result.returncode != 0:
        logger.error(result.stderr)
        raise RuntimeError(f"Failed to build Service: {result.stderr}")
    logger.info("Service built successfully.")

    # Publish AnacleAPI.Interface
    logger.info("Publishing AnacleAPI.Interface...")
    publish_command = f'{dev_cmd} && msbuild "{interface_path}" /p:DeployOnBuild=true /p:PublishProfile=DevOpsDebug /p:Configuration=Debug /v:m'
    logger.debug(f'Command: {publish_command}')
    result = subprocess.run(publish_command, shell=True, capture_output=True, text=True)
    logger.debug(result.stdout)
    if result.returncode != 0:
        logger.error(result.stderr)
        raise RuntimeError(f"Failed to publish AnacleAPI.Interface: {result.stderr}")
    logger.info("AnacleAPI.Interface published successfully.")

    logger.info("All tasks completed successfully.")

if __name__ == "__main__":
    main()