import os
import pyodbc                   # python -m pip install pyodbc
from dotenv import load_dotenv  # python -m pip install python-dotenv

load_dotenv()  # Load environment variables into the current Python process

connection_string = os.getenv('DB_CONNECTION_STRING')

try:
    with pyodbc.connect(connection_string) as conn:
        with conn.cursor() as cursor:
            print("Database connection successful!")

except pyodbc.Error as e:
    print("Database error occurred:")
    print(e)

except Exception as ex:
    print("Unexpected error:")
    print(ex)
