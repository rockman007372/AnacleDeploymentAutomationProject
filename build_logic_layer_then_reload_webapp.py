from pathlib import Path
import subprocess
import webbrowser

dev_cmd_path = Path("C:/Program Files/Microsoft Visual Studio/2022/Community/Common7/Tools/VsDevCmd.bat")
solution_dir = Path("C:/Anacle/SP/simplicity/abell.root/abell/")
url = "http://localhost/SP/applogin.aspx"

if __name__ == '__main__':
    dev_cmd = f'"{dev_cmd_path}"'
    abell_sol = solution_dir / "abell.sln"

    print("Building Logic Layer...")
    build_cmd = f'{dev_cmd} && msbuild {abell_sol} /t:LogicLayer:Rebuild /v:diag'
    result = subprocess.run(build_cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("Build LogicLayer failed")
        exit(1)

    # reload browser
    print(f"Opening {url}...")
    webbrowser.get("windows-default").open(url)
    

