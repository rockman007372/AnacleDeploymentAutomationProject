import os
import subprocess
import sys
import json

from script_manager import ScriptDownloader, ScriptParser, ScriptExecutor
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv 

def main():
    load_dotenv()  
    
    if not Path('config.json').exists():
        print("Config.json file not found. Exiting.")
        sys.exit(1)

    with open('config.json', 'r') as f:
        config = json.load(f)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(f"{config.get("log_dir", "./logs/")}/{timestamp}")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    print("[STEP 1/3]: Downloading SQL script...")
    url = config.get("url")
    downloader = ScriptDownloader(base_url=url, download_dir=log_dir)
    script_path = downloader.download_script()
    if not script_path: 
        print("  Failed to download the script. Exiting.")
        sys.exit(1)

    print("\n[STEP 2/3]: Parsing SQL script...")
    update_all_tables = config.get("update_all_tables", False)
    if update_all_tables:
        print("  Updating all tables.")
    else:    
        selected_tables = config.get("tables", [])
        print(f"  Updating selected tables: {selected_tables}")
        parser = ScriptParser(script_path)
        script_path = parser.parse_script(selected_tables)
        if not script_path:
            print("  Failed to parse the script. Exiting.")
            sys.exit(1)

    # Open the script in Notepad for review
    subprocess.Popen(['notepad.exe', script_path])
    response = input("  Proceed with executing the script (Y/N): ")
    if response.strip().upper() != 'Y':
        print("  Operation aborted by user.")
        sys.exit(0)
    
    print("\n[STEP 3/3]: Executing SQL script...")
    connection_string = os.getenv("DB_CONNECTION_STRING")
    executor = ScriptExecutor(script_path, connection_string=connection_string)
    executor.execute_with_logging(log_dir / f"sql_execution_log_{timestamp}.txt")

if __name__ == "__main__":
    main()