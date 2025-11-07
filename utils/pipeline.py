from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import os
import socket
import subprocess
import sys
import threading
from dotenv import load_dotenv
import requests
import pyodbc
import logging
from pathlib import Path
from typing import Dict, List, Optional
from bs4 import BeautifulSoup

# Module-level fallback logger
module_logger = logging.getLogger(__name__)

class ScriptDownloader:
    def __init__(self, logger: Optional[logging.Logger]=None):
        self.session = requests.Session()
        self.logger = logger or module_logger

    def _get_hidden_fields(self, base_url):
        response = self.session.get(base_url) # IIS refresh takes some time. No need timeout
        soup = BeautifulSoup(response.content, 'html.parser')
        return {
            '__VIEWSTATE': soup.find('input', {'name': '__VIEWSTATE'})['value'], # type: ignore
            '__VIEWSTATEGENERATOR': soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value'], # type: ignore
        }

    def download_script(self, base_url: str, download_dir: Path) -> Optional[Path]:
        try:
            if not base_url or base_url.strip() == "":
                raise ValueError("Base URL is required to download the script.")

            hidden_fields = self._get_hidden_fields(base_url)
            post_data = {
                '__VIEWSTATE': hidden_fields['__VIEWSTATE'],
                '__VIEWSTATEGENERATOR': hidden_fields['__VIEWSTATEGENERATOR'],
                '__EVENTTARGET': 'buttonGenerateScript',
                '__EVENTARGUMENT': '',
            }
            
            response = self.session.post(base_url, data=post_data)
            
            if 'attachment' in response.headers.get('Content-Disposition', ''):
                content_disposition = response.headers.get('Content-Disposition', '')
                filename = 'script.sql'
                if 'filename=' in content_disposition:
                    filename = content_disposition.split('filename=')[1].strip('"')
                    
                if not download_dir.exists():
                    download_dir.mkdir(parents=True)

                filename = download_dir / filename  
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
    def __init__(self, connection_config: Dict, logger: Optional[logging.Logger]=None):
        self.db_connection = connection_config
        self.logger = logger or module_logger
    
    def create_connection_string(self, config) -> str:
        parts = []
        for key, value in config.items():
            parts.append(f"{key}={value}")
        return 'driver={SQL Server};' + ';'.join(parts) + ';'

    def write_execution_log(self, log_dir: Path, messages: list[str]):
        log_dir.mkdir(parents=True, exist_ok=True)
        execution_log = log_dir / "sql_server_execution.log"
        with open(execution_log, "a") as log_file:
            log_file.write("\n".join(messages) + "\n")
        self.logger.info(f"Execution log written to: {execution_log}")

    def execute_on_database(self, sql_script: str, connection_config: Dict, log_dir: Path):
        database = connection_config["database"]
        connection_string = self.create_connection_string(connection_config)

        try:
            with pyodbc.connect(connection_string, autocommit=False) as conn:
                with conn.cursor() as cursor:    
                    self.logger.info(f"Executing SQL script on {database}.")
                    cursor.execute(sql_script)

                    messages = []
                    messages.append(f"Database: {database}")
                    if cursor.messages:
                        for message in cursor.messages:
                            messages.append(message[1])
                    while cursor.nextset():
                        if cursor.messages:
                            for message in cursor.messages:
                                messages.append(message[1])

                    conn.commit()
                    self.write_execution_log(log_dir, messages)
                    self.logger.info(f"Completed execution on {database}.")
        
        except pyodbc.Error as e:
            self.logger.error(f"Database error on {database}: {e}")
            raise  # Re-raise so execute() can catch it
        except Exception as e:
            self.logger.error(f"Unexpected error on {database}: {e}")
            raise

    def execute(self, script_path: Path, databases: Optional[List[str]]=None) -> bool:
        try:
            if not script_path.exists():
                raise FileNotFoundError(f"Script file not found: {script_path}")
            self.logger.info(f"SQL script to be executed: {script_path}")

            sql_script = script_path.read_text()
            log_dir = script_path.parent

            if databases:
                parent_thread_name = threading.current_thread().name
                with ThreadPoolExecutor(max_workers=len(databases), thread_name_prefix=f"{parent_thread_name}-dbworker") as executor:
                    futures = {}
                    for database in databases:
                        cloned_config = self.db_connection.copy()
                        cloned_config["database"] = database
                        future = executor.submit(self.execute_on_database, sql_script, cloned_config, log_dir)
                        futures[future] = database

                    errors = []
                    for future in as_completed(futures):
                        database = futures[future]
                        try:
                            future.result() # raise exceptions if any
                        except Exception as e:
                            self.logger.error(f"Failed on {database}: {e}")
                            errors.append((database, e))

                    if errors:
                        error_summary = ", ".join([f"{db}: {str(e)}" for db, e in errors])
                        raise Exception(f"Failed on {len(errors)} database(s): {error_summary}")
            else:
                self.execute_on_database(sql_script, self.db_connection, log_dir)
            
            return True
                        
        except Exception as e:
            self.logger.error(f"An error occurred during SQL execution: {e}")
            return False

class SQLDeploymentPipeline:
    def __init__(
        self, 
        config: Dict, 
        db_connection: Dict,
        log_directory: Optional[Path] = None, 
        custom_logger: Optional[logging.Logger] = None
    ):
        '''
        config: Configuration dictionary.\n
        log_directory: Directory to store downloaded script, processed scripts, and SQL server execution log.\n
        custom_logger: Optional custom logger for logging. The log file may or may not be in log_directory.
        '''
        self.validate_config(config)
        self.config = config

        self.validate_db_connection(db_connection)
        self.db_connection = db_connection

        self.log_directory = log_directory or Path(config.get("log_dir", "./logs/update_schema"))
        self.logger = custom_logger or module_logger

        self.downloader = ScriptDownloader(self.logger)
        self.parser = ScriptParser(self.logger)
        self.executor = ScriptExecutor(db_connection, self.logger)

    def validate_config(self, config: Dict):
        required_keys = ["url", "update_all_tables", "tables", "validate_script_before_execution"]
        missing = [k for k in required_keys if k not in config]
        if missing:
            raise ValueError(f"Missing required config keys: {missing}")
        
    def validate_db_connection(self, db_connection: Dict):
        required_keys = ["server", "database", "uid", "pwd"]
        missing = [k for k in required_keys if k not in db_connection]
        if missing:
            raise ValueError(f"Missing required config keys: {missing}")

    def download_script(self) -> Path:
        """Downloads the SQL script using ScriptDownloader."""
        url = self.config.get("url", "")
        download_dir = self.log_directory

        script_path = self.downloader.download_script(url, download_dir)
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
        
        filtered_script_path = self.parser.parse_script(script_path, selected_tables)
        if not filtered_script_path:
            self.logger.error("Failed to parse the script.")
            raise Exception("Script parsing failed.")
        
        return filtered_script_path

    def open_validation_panel(self, port, sql_script_path):
         # Resolve path of validation_console.py relative to this module
        module_dir = Path(__file__).parent
        console_script = module_dir / "validation_console.py"

        if not console_script.exists():
            raise Exception(f"Cannot find {console_script}")

        subprocess.Popen(
            ["python", str(console_script), str(port), str(sql_script_path)],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )

    def validate_script(self, script_path: Path) -> bool:
        validate_script = self.config.get("validate_script_before_execution", True)

        if validate_script:
            host, port = "127.0.0.1", 50505

            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind((host, port))
            server.listen(1)

            logging.info("Waiting for user response after script validation...")
            self.open_validation_panel(port, script_path)

            conn, _ = server.accept()
            response = conn.recv(1024).decode()
            conn.close()
            server.close()

            if response.strip().upper() != "Y":
                self.logger.warning("Operation aborted by user.")
                return False

            self.logger.info("Script acknowledged by user. Proceed with execution.")                
            
        return True

    def execute_script(self, script_path: Path):
        """Executes the SQL script using ScriptExecutor."""
        databases = self.config.get("databases", [])
        is_success = self.executor.execute(script_path, databases)
        if not is_success:
            raise Exception("Script execution failed.")

    def run(self):
        """Runs the full deployment pipeline."""
        try:
            self.logger.info("Downloading SQL script...")
            script_path = self.download_script()

            self.logger.info("Parsing SQL script...")
            script_path = self.parse_script(script_path)

            if not self.validate_script(script_path):
                sys.exit(0)

            self.logger.info("Executing SQL script...")
            self.execute_script(script_path)

            self.logger.info("✅ SQL Deployment completed successfully.")

        except Exception as e:
            self.logger.exception(f"❌ SQL Deployment failed.")
            sys.exit(1)

        