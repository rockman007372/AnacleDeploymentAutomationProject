import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, List, Optional
import zipfile

class Builder:
    def __init__(self, config: Dict, custom_logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = custom_logger or logging.getLogger(__name__)
        self.validate_config()

    def validate_config(self):
        required_fields = [
            "dev_cmd_path",
            "7zip_path",
            "solution_dir",
            "publish_dir",
            "remove_config_files",
            "zip_output"
        ]
        missing_fields = [k for k in required_fields if k not in self.config]
        if missing_fields:
            raise Exception(f"Missing required field: {missing_fields}")

    def get_projects(self):
        '''
        Returns a list of available projects to be built.
        '''
        return ["LogicLayer", "Service", "AnacleAPI.Interface"]

    def run_command(self, command: str, step_name: str):
        self.logger.info(f"{step_name}...")
        self.logger.debug(f"Command: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        # self.logger.debug(result.stdout)
        if result.returncode != 0:
            self.logger.error(result.stderr)
            raise RuntimeError(f"{step_name} failed: {result.stderr}")
        self.logger.info(f"{step_name} completed successfully.")

    def build(self, project_id: Optional[int]=None):
        """Build LogicLayer, Service and publish TPAPI."""
        try:
            solution_dir = Path(self.config["solution_dir"])
            dev_cmd_path = Path(self.config["dev_cmd_path"])
            if not solution_dir.exists():
                raise FileNotFoundError(f"Solution directory not found: {solution_dir}")
            if not dev_cmd_path.exists():
                raise FileNotFoundError(f"Development command prompt not found: {dev_cmd_path}")

            dev_cmd = f'"{dev_cmd_path}"'
            abell_sol = solution_dir / "abell.sln"
            interface = solution_dir / "AnacleAPI.Interface" / "AnacleAPI.Interface.csproj"

            projects = {
                1: {
                    "name": "LogicLayer",
                    "cmd": f'{dev_cmd} && msbuild {abell_sol} /t:LogicLayer:Rebuild /v:diag',
                },
                2: {
                    "name": "Service",
                    "cmd": f'{dev_cmd} && msbuild {abell_sol} /t:Service:Rebuild /v:diag',
                },
                3: {
                    "name": "AnacleAPI.Interface",
                    "cmd": f'{dev_cmd} && msbuild "{interface}" /p:DeployOnBuild=true /p:PublishProfile=DevOpsDebug /p:Configuration=Debug /v:m'
                },
            }

            # Build all if no specific project is passed
            if project_id is None:
                targets = projects.values()
            elif project_id in projects:
                targets = [projects[project_id]]
            else:
                raise ValueError(f"Unknown project ID: {project_id}")

            for target in targets:
                self.run_command(target["cmd"], f"Building/Publishing {target['name']}")

            self.logger.info("✅ All build tasks completed successfully.")

        except Exception as e:
            self.logger.exception(f"❌ Build process failed.")
            exit(1)

    def copy_folder(self, src: Path, dst: Path):
        try:
            if not src.exists():
                raise NotADirectoryError(f"Source directory {src} does not exist")
            shutil.copytree(src, dst, dirs_exist_ok=True) # Create dst directory automatically
            self.logger.info(f"Copied {src} to {dst}.")
        except Exception as e:
            self.logger.error(f"Error occured while copying {src} to {dst}: {e}")
            raise 

    def move_file(self, src: Path, dst: Path):
        if src.exists():
            try:
                dst.parent.mkdir(parents=True, exist_ok=True) # must ensure dest dir exists
                shutil.copy(src, dst)
                os.remove(src)
                self.logger.info(f"Moved {src} to {dst}.")
            except Exception as e:
                self.logger.error(f"Error occured while moving {src} to {dst}: {e}")
                raise
        else:
            self.logger.warning(f"Skip {src} because the file cannot be found.")

    def zip_with_7zip(self, folders, zip_path):
        """Attempt to compress using external 7z.exe."""
        try:
            sevenzip_path: Path = Path(self.config.get("7zip_path", "C:/Program Files/7-Zip/7z.exe"))
            args = [sevenzip_path, 'a', '-tzip', str(zip_path)] + [str(f) for f in folders] + ['-mx=9']
            result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"Deployment package created successfully (7-Zip): {zip_path}")
            else:
                self.logger.error(f"7-Zip failed with code {result.returncode}")
                sys.exit(1)
        
        except FileNotFoundError:
            self.logger.warning("7-Zip not found, falling back to Python zipfile")
            self.zip_with_python(folders, zip_path)
        
        except Exception as e:
            self.logger.warning("7-Zip not found, falling back to Python zipfile")
            self.zip_with_python(folders, zip_path)

    def zip_with_python(self, folders, zip_path):
        """Fallback ZIP implementation using Python's zipfile."""
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
                for folder in folders:
                    for root, _, files in os.walk(folder):
                        for f in files:
                            full_path = os.path.join(root, f)
                            rel_path = os.path.relpath(full_path, os.path.dirname(folders[0]))
                            z.write(full_path, rel_path)
            self.logger.info(f"Deployment package created successfully: {zip_path}")
        
        except Exception as e:
            self.logger.error(f" Failed to create deployment package: {e}")
            sys.exit(1)

    def publish(self) -> Optional[Path]:
        """
        Publish webapp, service, TPAPI directories to a deployment directory 
        and create an optional deployment zip package. Returns the path of the deployment package if created. 
        """
        solution_dir: Path = Path(self.config["solution_dir"])
        publish_dir: Path = Path(self.config["publish_dir"]) / f"UAT_{datetime.now().strftime("%Y%m%d")}"
        zip_output: bool = self.config.get("zip_output", True)
        remove_config_files = self.config.get("remove_config_files", True)

        folders_to_copy = ["webapp", "service", "TPAPI"] 
        folders_to_paths = {
            "webapp": solution_dir / "webapp",
            "service": solution_dir / "service" / "bin" / "debug",
            "TPAPI": solution_dir / "AnacleAPI.Interface" / "bin" / "app.publish",
        }

        self.logger.info("Copying deployment folders...")
        for folder in folders_to_copy:
            self.copy_folder(folders_to_paths[folder], publish_dir / folder)

        if remove_config_files:
            self.logger.info("Removing config files...")
            config_dir = publish_dir / "configs"
            config_files = {
                "webapp": ["web.config", "website.publishproj"],
                "service": ["Service.exe.config", "LogicLayer.dll.config"],
                "TPAPI": ["Web.config"],
            }

            for folder in folders_to_copy:
                for cfg_file in config_files.get(folder, []):
                    source = publish_dir / folder / cfg_file
                    dest = config_dir / folder / cfg_file
                    self.move_file(source, dest)

        zip_file = None
        if zip_output:
            self.logger.info("Zipping deployment package...")
            folders_to_zip = [str(publish_dir / f) for f in folders_to_copy]
            zip_file = publish_dir / publish_dir.name
            self.zip_with_7zip(folders_to_zip, zip_file)

        self.logger.info("✅ Actifact published successfully.")
        return zip_file