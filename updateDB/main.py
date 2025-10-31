import os
import subprocess
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from script_manager import ScriptDownloader, ScriptParser, ScriptExecutor

def setup_logging(log_dir: Path):
    """Sets up logging to both console and file."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

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
    load_dotenv()

    if not Path("config.json").exists():
        print("Config.json file not found. Exiting.")
        sys.exit(1)

    with open("config.json", "r") as f:
        config = json.load(f)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(f"{config.get('log_dir', './logs/')}/{timestamp}")
    logger = setup_logging(log_dir)

    logger.info("[STEP 1/3] Downloading SQL script...")
    url = config.get("url")
    logger.info(f"Download URL: {url}")

    downloader = ScriptDownloader(base_url=url, download_dir=log_dir)
    script_path = downloader.download_script()
    if not script_path:
        logger.error("Failed to download the script. Exiting.")
        sys.exit(1)

    logger.info("[STEP 2/3] Parsing SQL script...")
    update_all_tables = config.get("update_all_tables", False)

    if update_all_tables:
        logger.info("Updating all tables.")
    else:
        selected_tables = config.get("tables", [])
        logger.info(f"Updating selected tables: {selected_tables}")
        parser = ScriptParser(script_path)
        script_path = parser.parse_script(selected_tables)
        if not script_path:
            logger.error("Failed to parse the script. Exiting.")
            sys.exit(1)

    # Optional validation
    validate_script = config.get("validate_script_before_execution", True)
    if validate_script:
        logger.info("Opening script in Notepad for review...")
        subprocess.Popen(["notepad.exe", script_path])
        response = input("Proceed with executing the script (Y/N): ")
        if response.strip().upper() != "Y":
            logger.info("Operation aborted by user.")
            sys.exit(0)

    logger.info("[STEP 3/3] Executing SQL script...")
    logger.info(f"Script to be executed: {script_path}")
    connection_string = os.getenv("DB_CONNECTION_STRING")
    executor = ScriptExecutor(script_path, connection_string=connection_string)
    executor.execute()

if __name__ == "__main__":
    main()
