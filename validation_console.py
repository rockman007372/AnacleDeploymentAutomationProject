import socket
import sys
from pathlib import Path

if len(sys.argv) != 3:
    print("Usage: python validation_console.py <port> <script>")
    sys.exit(1)

port = int(sys.argv[1])
script_path = Path(sys.argv[2])

# Print script to console for preview
print(f"Script path: {script_path}\n")
with script_path.open("r", encoding="utf-8") as f:
    for line in f:
        # Write directly to stdout immediately
        sys.stdout.write(line)

        # Ensures it appears in console immediately
        sys.stdout.flush()  

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("127.0.0.1", port))

resp = input("\nProceed with executing the script (Y/N): ")
s.send(resp.encode())
s.close()