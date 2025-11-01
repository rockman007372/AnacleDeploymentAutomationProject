import requests
import pyodbc
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class ScriptDownloader:
    def __init__(self, base_url: str, download_dir: Path):
        self.base_url = base_url
        self.download_dir = download_dir
        self.session = requests.Session()

    def _get_hidden_fields(self):
        response = self.session.get(self.base_url, timeout=60)
        soup = BeautifulSoup(response.content, 'html.parser')
        return {
            '__VIEWSTATE': soup.find('input', {'name': '__VIEWSTATE'})['value'], # type: ignore
            '__VIEWSTATEGENERATOR': soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value'], # type: ignore
        }

    def download_script(self) -> Optional[Path]:
        try:
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
                    
                logger.info(f"Script downloaded successfully: {filename}")
                return filename
            else:
                logger.error("No attachment found in response")
                return None
            
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
        
class ScriptParser:
    def __init__(self, script_path: Path):
        self.script_path = script_path

    def parse_script(self, selected_tables: list[str]) -> Optional[Path]:
        table_blocks = self.generate_table_blocks()
        filtered_script = self.generate_filtered_script(table_blocks, selected_tables)
        return filtered_script

    def generate_table_blocks(self)-> dict[str, str]:
        '''
        Parse the SQL script and return a dictionary of 
        table names mapping to its corresponding SQL blocks.
        '''
        with open(self.script_path, 'r') as f:
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

    def generate_filtered_script(self, table_blocks, selected_tables: list[str]) -> Optional[Path]:
        '''
        Generate a new SQL script containing only the selected tables.
        '''
        try:
            new_script = "set nocount on\n"
            new_script += "declare @xmls nvarchar(max)\n\n"

            for table in selected_tables:
                if table in table_blocks:
                    logger.info(f"Including table '{table}' in the new script.")
                    new_script += table_blocks[table] + "\n"
                else:
                    logger.error(f"Table '{table}' not found in the script.")
                    return None

            new_script += "set nocount off\n"

            # Write the new script to a file in the same directory
            filtered_script_path = self.script_path.parent / "filtered_script.sql"
            with open(filtered_script_path, 'w') as f:
                f.write(new_script)

            return filtered_script_path
        
        except Exception as e:
            logger.error(f"An error occurred while generating filtered script: {e}")
            return None
        
class ScriptExecutor:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def execute(self, script_path: Path, log_dir: Path):
        try:
            if not script_path.exists():
                logger.error(f"Script file not found: {script_path}")
                return
            sql_script = script_path.read_text()
            log_dir.mkdir(parents=True, exist_ok=True)        

            with pyodbc.connect(self.connection_string, autocommit=False) as conn:
                with conn.cursor() as cursor:     
                    logger.info("Executing script...")     
                    cursor.execute(sql_script)

                    # Capture PRINT statements from SQL Server messages
                    execution_log = log_dir / "execution_log.txt"
                    with open(execution_log, "w") as log_file:
                        if cursor.messages:
                            for message in cursor.messages:
                                msg_text = message[1]
                                log_file.write(f"{msg_text}\n")
                        
                        # Process any additional result sets
                        while cursor.nextset():
                            if cursor.messages:
                                for message in cursor.messages:
                                    msg_text = message[1]
                                    log_file.write(f"{msg_text}\n")

                    # Commit the transaction
                    conn.commit()
                    logger.info(f"SQL script executed successfully. Check {execution_log} for details.")
                        
        except Exception as e:
            logger.error(f"An error occurred during SQL execution: {e}")