import os
import subprocess
import sys
import pyodbc
from datetime import datetime
from dotenv import load_dotenv 
from pathlib import Path

# Load environment variables into the current Python process
load_dotenv()  

# Where the sql database scripts are located
script_dir = Path("C:/Users/rockm/Downloads")

def parse_script(sql_file):
    '''
    Parse the SQL script and return a dictionary of 
    table names mapping to its conresponding SQL blocks.
    '''
    with open(sql_file, 'r') as f:
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

def generate_filtered_script(table_blocks, selected_tables):
    '''
    Generate a new SQL script containing only the selected tables.
    '''
    new_script = "set nocount on\n"
    new_script += "declare @xmls nvarchar(max)\n\n"

    for table in selected_tables:
        if table in table_blocks:
            print(f"[INFO] Including table '{table}' in the new script.")
            new_script += table_blocks[table] + "\n"
        else:
            print(f"[WARNING] Table '{table}' not found in the script.")

    new_script += "set nocount off\n"
    return new_script

def execute_sql_with_logging(sql_script: str, log_path: Path):
    try:
        # Ensure the log directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        connection_string = os.getenv('DB_CONNECTION_STRING')
        
        with pyodbc.connect(connection_string, autocommit=False) as conn:
            with conn.cursor() as cursor:          
                with open(log_path, 'w') as log_file:
                    # Header
                    log_file.write("=" * 80 + "\n")
                    log_file.write("SQL SCRIPT\n")
                    log_file.write("=" * 80 + "\n\n")
                    
                    # SQL Script content
                    log_file.write(sql_script)
                    
                    # Separator between script and execution
                    log_file.write("\n\n" + "=" * 80 + "\n")
                    log_file.write("EXECUTION LOG\n")
                    log_file.write("=" * 80 + "\n")
                    log_file.write(f"Started:  {datetime.now()}\n")
                    log_file.write("-" * 80 + "\n\n")

                    cursor.execute(sql_script)

                    # Capture PRINT statements from SQL Server messages
                    if cursor.messages:
                        for message in cursor.messages:
                            msg_text = message[1]
                            log_file.write(f"{msg_text}\n")
                            print(msg_text)
                    
                    # Process any additional result sets
                    while cursor.nextset():
                        if cursor.messages:
                            for message in cursor.messages:
                                msg_text = message[1]
                                log_file.write(f"{msg_text}\n")
                                print(msg_text)
                    
                    # Commit the transaction
                    conn.commit()
                    
                    # Footer
                    log_file.write("\n" + "-" * 80 + "\n")
                    log_file.write(f"Completed: {datetime.now()}\n")
                    log_file.write("=" * 80 + "\n")
                        
        print(f"Schemas updated successfully. Check '{log_path}' for details.")
    
    except pyodbc.Error as e:
        print("Database error occurred:")
        print(e)
    
    except Exception as ex:
        print("An error occurred:")
        print(ex)

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python update_schema.py \"database.sql\"")
        sys.exit(1)

    script: Path = script_dir / sys.argv[1]
    if not script.exists():
        print(f"SQL script file '{script}' does not exist.")
        sys.exit(1)

    table_blocks = parse_script(script)

    print("Enter tables to update, separated by commas.\nTo update all tables, input '.':")
    selected_tables = input().strip()
    
    if selected_tables == '.':
        selected_tables = list(table_blocks.keys())
    else:
        selected_tables = [t.strip() for t in selected_tables.split(",")]

    new_script = generate_filtered_script(table_blocks, selected_tables)

    # Save new script and open it in Notepad for review
    with open("output.sql", "w") as f:
        f.write(new_script)
        subprocess.Popen(['notepad.exe', 'output.sql'])

    response = input("Proceed with executing the script (Y/N): ")
    if response.strip().upper() != 'Y':
        print("Operation aborted by user.")
        sys.exit(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = Path(f"./log/execution_log_{timestamp}.txt")

    execute_sql_with_logging(new_script, log_path)