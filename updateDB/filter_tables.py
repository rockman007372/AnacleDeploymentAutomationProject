from pathlib import Path
import subprocess
import sys

# Where the sql scripts are located
script_dir = Path("C:/Users/rockm/Downloads")

if len(sys.argv) < 2:
    print("Usage: python filter_tables.py \"database.sql\"")
    sys.exit(1)

script = script_dir / sys.argv[1]

# Load SQL script
with open(script, "r") as f:
    lines = f.readlines()

table_blocks = {}
current_table = None
current_block = []

for line in lines:
    line_strip = line.strip()
    
    # Detect the start of a table block
    if line_strip.startswith("print ('Syncing"):
        current_table = line_strip.split()[2].strip("('")  # Extract table name
        current_block = [line]
    
    # Accumulate lines in the current block
    elif current_table:
        current_block.append(line)
        # Detect the end of the table block
        if line_strip.startswith("print ('") and "synchronized" in line_strip:
            table_blocks[current_table] = "".join(current_block)
            current_table = None
            current_block = []

# Ask user for tables to include
selected_tables = input("Enter tables to modify, separated by commas: ").split(",")
selected_tables = [t.strip() for t in selected_tables]

# Generate new SQL script
new_script = "set nocount on\n"
new_script += "declare @xmls nvarchar(max)\n\n"

for table in selected_tables:
    if table in table_blocks:
        print(f"[INFO] Including table '{table}' in the new script.")
        new_script += table_blocks[table] + "\n"
    else:
        print(f"[WARNING] Table '{table}' not found in the script.")

new_script += "set nocount off\n"

# Save new script and open it in Notepad
with open("output.sql", "w") as f:
    f.write(new_script)
    subprocess.Popen(['notepad.exe', 'output.sql'])

print("New SQL script saved as output.sql")

