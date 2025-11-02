from datetime import datetime
import os
import subprocess
import sys
from dotenv import load_dotenv
import requests
import pyodbc
import logging
from pathlib import Path
from typing import Dict, Optional
from bs4 import BeautifulSoup

# Module-level fallback logger
module_logger = logging.getLogger(__name__)

class ScriptDownloader:
    def __init__(self, base_url: str, download_dir: Path, logger: Optional[logging.Logger]=None):
        self.base_url = base_url
        self.download_dir = download_dir
        self.session = requests.Session()
        self.logger = logger or module_logger

    def _get_hidden_fields(self):
        response = self.session.get(self.base_url, timeout=60)
        soup = BeautifulSoup(response.content, 'html.parser')
        return {
            '__VIEWSTATE': soup.find('input', {'name': '__VIEWSTATE'})['value'], # type: ignore
            '__VIEWSTATEGENERATOR': soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value'], # type: ignore
        }

    def download_script(self) -> Optional[Path]:
        try:
            if not self.base_url or self.base_url.strip() == "":
                raise ValueError("Base URL is required to download the script.")

            hidden_fields = self._get_hidden_fields()
            post_data = {
                '__VIEWSTATE': hidden_fields['__VIEWSTATE'],
                '__VIEWSTATEGENERATOR': hidden_fields['__VIEWSTATEGENERATOR'],
                '__EVENTTARGET': 'buttonGenerateScript',
                '__EVENTARGUMENT': '',
            }
            
            response = self.session.post(self.base_url, data=post_data)
            
            if 'attachment' in response.headers.get('Content-Disposition', ''):
                content_disposition = response.headers.get('Content-Disposition', '')
                filename = 'script.sql'
                if 'filename=' in content_disposition:
                    filename = content_disposition.split('filename=')[1].strip('"')
                    
                if not self.download_dir.exists():
                    self.download_dir.mkdir(parents=True)

                filename = self.download_dir / filename  
                with open(filename, 'wb') as f:
                    f.write(response.content)
                    
                self.logger.info(f"Script downloaded successfully: {filename}")
                return filename
            else:
                raise RuntimeError("No attachment found in response.")
            
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            return None
        
class ScriptParser:
    def __init__(self, logger: Optional[logging.Logger]=None):
        self.logger = logger or module_logger

    def parse_script(self, script_path: Path, selected_tables: list[str]) -> Optional[Path]:
        table_blocks = self.generate_table_blocks(script_path)
        filtered_script = self.generate_filtered_script(table_blocks, selected_tables)

        if filtered_script:
            filtered_script_path = script_path.parent / f"filtered_{script_path.name}"
            with open(filtered_script_path, 'w') as f:
                f.write(filtered_script)
            self.logger.info(f"Filtered script created: {filtered_script_path}")
            return filtered_script_path

    def generate_table_blocks(self, script_path: Path)-> dict[str, str]:
        '''
        Parse the SQL script and return a dictionary of 
        table names mapping to its corresponding SQL blocks.
        '''
        with open(script_path, 'r') as f:
            lines = f.readlines()

        table_blocks = {}
        current_table = None
        current_block = []

        for line in lines:
            line_strip = line.strip()
            
            # Detect the start of a table block
            if line_strip.startswith("print ('Syncing"):
                current_table = line_strip.split()[2]  # Extract table name: [print, ('Syncing, [TableName],...]
                current_block = [line]
            
            # Accumulate lines in the current block
            elif current_table:
                current_block.append(line)
                # Detect the end of the table block
                if line_strip.startswith("print ('") and "synchronized" in line_strip:
                    table_blocks[current_table] = "".join(current_block)
                    current_table = None
                    current_block = []
        
        return table_blocks

    def generate_filtered_script(self, table_blocks, selected_tables: list[str]) -> Optional[str]:
        '''
        Generate a new SQL script containing only the selected tables.
        '''
        try:
            new_script = "set nocount on\n"
            new_script += "declare @xmls nvarchar(max)\n\n"

            for table in selected_tables:
                if table in table_blocks:
                    self.logger.debug(f"Including table '{table}' in the new script.")
                    new_script += table_blocks[table] + "\n"
                else:
                    raise RuntimeError(f"Table '{table}' not found in the script.")

            new_script += "set nocount off\n"

            return new_script
        
        except Exception as e:
            self.logger.error(f"An error occurred while generating filtered script: {e}")
            return None
        
class ScriptExecutor:
    def __init__(self, connection_string: str, logger: Optional[logging.Logger]=None):
        self.connection_string = connection_string
        self.logger = logger or module_logger

    def write_execution_log(self, log_dir: Path, messages: list[str]):
        log_dir.mkdir(parents=True, exist_ok=True)
        execution_log = log_dir / "sql_server_execution.log"
        with open(execution_log, "w") as log_file:
            log_file.write("\n".join(messages))
        self.logger.info(f"Execution log written to: {execution_log}")

    def execute(self, script_path: Path) -> bool:
        try:
            if not script_path.exists():
                raise FileNotFoundError(f"Script file not found: {script_path}")

            sql_script = script_path.read_text()

            with pyodbc.connect(self.connection_string, autocommit=False) as conn:
                with conn.cursor() as cursor:     
                    self.logger.info(f"Executing script: {script_path}")     
                    cursor.execute(sql_script)

                    # Capture PRINT statements from SQL Server messages
                    messages = []
                    if cursor.messages:
                        for message in cursor.messages:
                            messages.append(message[1])
                    while cursor.nextset():
                        if cursor.messages:
                            for message in cursor.messages:
                                messages.append(message[1])

                    self.write_execution_log(script_path.parent, messages)

                    # Commit the transaction
                    conn.commit()
                    self.logger.info(f"SQL script executed successfully.")
                    return True
                        
        except Exception as e:
            self.logger.error(f"An error occurred during SQL execution: {e}")
            return False

class SQLDeploymentPipeline:
    def __init__(self, config: Dict, log_directory: Optional[Path]=None, custom_logger: Optional[logging.Logger]=None):
        '''
        config: Configuration dictionary.
        log_directory: Directory to store downloaded and processed scripts, and SQL server execution log.
        custom_logger: Optional custom logger for logging. The log file may or may not be in log_directory.
        '''
        self.config = config
        self.log_directory = log_directory or Path(config.get("log_dir", "./logs/"))
        self.logger = custom_logger or module_logger

    def setup(self):
        """Initializes environment."""
        load_dotenv()

    def download_script(self) -> Path:
        """Downloads the SQL script using ScriptDownloader."""
        url = self.config.get("url", "")
        download_dir = self.log_directory
        downloader = ScriptDownloader(url, download_dir, self.logger)
        
        script_path = downloader.download_script()
        if not script_path:
            self.logger.error("Failed to download the script.") 
            raise Exception("Script download failed.")
        
        return script_path

    def parse_script(self, script_path: Path) -> Path:
        """Parses the SQL script using ScriptParser."""
        update_all_tables = self.config.get("update_all_tables", False)
        if update_all_tables:
            self.logger.info("Updating all tables as per configuration. No parsing needed.")
            return script_path

        selected_tables = self.config.get("tables", [])
        self.logger.info(f"Parsing selected tables: {selected_tables}")
        parser = ScriptParser(logger=self.logger)
        
        filtered_script_path = parser.parse_script(script_path, selected_tables)
        if not filtered_script_path:
            self.logger.error("Failed to parse the script.")
            raise Exception("Script parsing failed.")
        
        return filtered_script_path

    def validate_script(self, script_path: Path) -> bool:
        validate_script = self.config.get("validate_script_before_execution", True)

        if validate_script:
            self.logger.info("Opening script in Notepad for review...")
            subprocess.Popen(["notepad.exe", script_path])
            response = input("Proceed with executing the script (Y/N): ")
            if response.strip().upper() != "Y":
                self.logger.info("Operation aborted by user.")
                return False
            
        return True

    def execute_script(self, script_path: Path):
        """Executes the SQL script using ScriptExecutor."""
        connection_string = os.getenv("DB_CONNECTION_STRING", "")
        
        executor = ScriptExecutor(connection_string)
        is_success = executor.execute(script_path)
        if not is_success:
            raise Exception("Script execution failed.")

    def run(self):
        """Runs the full deployment pipeline."""
        try:
            self.setup()

            self.logger.info("[STEP 1/3] Downloading SQL script...")
            script_path = self.download_script()

            self.logger.info("[STEP 2/3] Parsing SQL script...")
            script_path = self.parse_script(script_path)

            if not self.validate_script(script_path):
                sys.exit(0)

            self.logger.info("[STEP 3/3] Executing SQL script...")
            self.execute_script(script_path)

            self.logger.info("✅ Deployment pipeline completed successfully.")

        except Exception as e:
            self.logger.exception(f"❌ Pipeline failed: {e}")
            sys.exit(1)

        