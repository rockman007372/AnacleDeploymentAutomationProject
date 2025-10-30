import os
import pyodbc
from datetime import datetime
from dotenv import load_dotenv 
from pathlib import Path

# Load environment variables into the current Python process
load_dotenv()  

def execute_sql_with_logging(sql_file, log_file):
    connection_string = os.getenv('DB_CONNECTION_STRING')
    try:
        with pyodbc.connect(connection_string, autocommit=False) as conn:
            with conn.cursor() as cursor:
                with open(sql_file, 'r') as f:
                    sql_script = f.read()
                
                with open(log_file, 'w') as log_f:
                    log_f.write(f"Script execution started at {datetime.now()}\n")
                    log_f.write("=" * 80 + "\n\n")

                    cursor.execute(sql_script)

                    # Capture PRINT statements from SQL Server messages
                    # These are stored in cursor.messages
                    if cursor.messages:
                        for message in cursor.messages:
                            # message is a tuple: (type of message, text)
                            msg_text = message[1]
                            log_f.write(f"{msg_text}\n")
                            print(msg_text)  # Also print to console
                    
                    # Process any additional result sets
                    while cursor.nextset():
                        if cursor.messages:
                            for message in cursor.messages:
                                msg_text = message[1]
                                log_f.write(f"{msg_text}\n")
                                print(msg_text)
                    
                    # Commit the transaction
                    conn.commit()
                    
                    log_f.write("\n" + "=" * 80 + "\n")
                    log_f.write(f"Script execution completed at {datetime.now()}\n")
                        
        print(f"Schemas updated successfully. Check '{log_file}' for details.")
    
    except pyodbc.Error as e:
        print("Database error occurred:")
        print(e)

if __name__ == "__main__":
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    sql_file = "output.sql"
    log_file = f"./log/execution_log_{timestamp}.txt"

    # Ensure the log directory exists
    Path("./log").mkdir(parents=True, exist_ok=True)

    execute_sql_with_logging(sql_file, log_file)