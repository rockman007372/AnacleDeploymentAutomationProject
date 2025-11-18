from datetime import datetime
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import paramiko

# Module-level fallback logger
module_logger = logging.getLogger(__name__)

class Denis4Client():
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None) -> None:
        self.validate_config(config)
        self.config = config
        self.logger = logger or module_logger
        self.ssh_client = paramiko.SSHClient()
        self.execution_log = self.get_execution_log_file()

    def validate_config(self, config: Dict):
        required_keys = [
            "log_dir",
            "server", 
            "user", 
            "remote_scripts_dir",
            "directories_to_backup",
            "base_backup_dir"
        ]
        missing = [k for k in required_keys if k not in config]
        if missing:
            raise ValueError(f"Missing required config keys: {missing}")

    def connect_to_denis4(self):
        server = self.config.get("server", "")
        username = self.config.get("user", "")
        try:
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(server, username=username)
            self.logger.info(f"Connected to {username}@{server}")
        except Exception as e:
            self.logger.error(f"Failed to connect to {username}@{server}: {e}")
            raise

    def is_connected(self) -> bool:
        """Check if SSH connection is still alive"""
        if not self.ssh_client:
            return False

        transport = self.ssh_client.get_transport()
        if not transport:
            return False
        
        return transport.is_active()

    def ensure_connected(self):
        """Reconnect if connection is lost"""
        if not self.is_connected():
            self.logger.warning("SSH connection lost, reconnecting...")
            if self.ssh_client:
                try:
                    self.ssh_client.close()
                except:
                    pass
            self.ssh_client = paramiko.SSHClient()
            self.connect_to_denis4()

    def get_execution_log_file(self) -> Path:
        '''
        Return the path of the execution log file, 
        which stores all stdout/stderr info from the remote server.
        This is separated from the app.log file.
        '''
        log_dir = Path(self.config["log_dir"])
        log_file = log_dir / "denis4.log"

        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)

        return log_file

    def execute_command(self, command: str) -> tuple[str, str, int]:
        self.ensure_connected()
        try:
            _, stdout, stderr = self.ssh_client.exec_command(command)
            
            # Wait for command to complete and get exit code
            exit_code = stdout.channel.recv_exit_status()
            
            stdout_text = stdout.read().decode()
            stderr_text = stderr.read().decode()

            # Normalize Windows CRLF → LF
            stdout_text = stdout_text.replace("\r\n", "\n")
            stderr_text = stderr_text.replace("\r\n", "\n")
            
            # if exit_code != 0:
            #     self.logger.error(f"Command {command} failed with exit code {exit_code}")
                
            if stderr_text:
                self.logger.warning(f"stderr: {stderr_text}")

            # Write stdout to execution logs 
            with open(self.execution_log, "a") as f:
                f.write(stdout_text)
            
            return stdout_text, stderr_text, exit_code
            
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            raise

    def __del__(self):
        """Cleanup on deletion"""
        try:
            if self.ssh_client:
                self.ssh_client.close()
        except:
            pass

    def backup(
            self, 
            directories_to_backup: Optional[List[Path]] = None, 
            base_backup_dir: Optional[Path] = None
        ):
        '''
        Create backups at base backup directory for the given directories.
        Execute the "backup.bat" script on remote server, which backups 
        "webapp", "service", "TPAPI" in the given directory.
        '''
        remote_script_dir = Path(self.config["remote_scripts_dir"])
        backup_script = remote_script_dir / "backup.bat"

        if not directories_to_backup:
            directories_to_backup = list(map(lambda dir: Path(dir), self.config["directories_to_backup"]))

        if not base_backup_dir:
            base_backup_dir = Path(self.config["base_backup_dir"])
        
        has_error = False
        for directory in directories_to_backup:
            self.logger.info(f"Backing up {directory}...")
            cmd = f'{backup_script} "{directory}" "{base_backup_dir}"'
            _, _, exit_code = self.execute_command(cmd)
            if exit_code != 0:
                self.logger.error(f"❌ Failed to backup {directory}. Check remote execution log for details.")
                has_error = True
            else:
                self.logger.info(f"✅ Backup {directory} successfully.")
        
        if has_error:
            raise RuntimeError("Some backups failed.")
    
    def _make_directory_recursive(self, sftp: paramiko.SFTPClient, remote_dir: str):
        """Create remote directory if it doesn't exist"""

        def is_existing_dir(dir: str):
            try:
                sftp.stat(dir)
                return True
            except FileNotFoundError:
                return False
            
        # Normalize path
        remote_dir = remote_dir.replace('\\', '/')
        remote_dir = remote_dir.rstrip("/")    # Avoid creating trailing empty dirs
         
        # base cases
        if not remote_dir or remote_dir in ('/', '.', 'C:/', 'D:/', 'E:/'):
            return
        
        if is_existing_dir(remote_dir):
            return

        parent = str(Path(remote_dir).parent)

        # Safety: prevent infinite recursion if parent == current
        if parent != remote_dir:
            self._make_directory_recursive(sftp, parent)

        # Create directory with error handling
        try:
            sftp.mkdir(remote_dir)
            self.logger.info(f"Created directory: {remote_dir}")
        except IOError as e:
            self.logger.error(f"Failed to create {remote_dir}: {e}")
            raise

    def _upload_file(self, local_file: Path, remote_file: Path):
        sftp = self.ssh_client.open_sftp()
        try:
            self._make_directory_recursive(sftp, str(remote_file.parent))
            sftp.put(str(local_file), str(remote_file))
        except Exception:
            raise
        finally:
            sftp.close()

    def upload_deployment_package(self, deployment_package: Path) -> Path:
        """Upload a file to remote server. Returns the remote file path."""
        try:
            self.ensure_connected()
            if not deployment_package.exists():
                raise FileNotFoundError("No deployment package found.")
            base_deployment_dir = Path(self.config["base_deployment_dir"])
            remote_file_path = base_deployment_dir / f"{datetime.now().strftime("%Y%m%d")}_mybill_v10" / deployment_package.name
            
            self.logger.info(f"Uploading deployment package {deployment_package}...")
            self._upload_file(deployment_package, remote_file_path)
            self.logger.info(f"✅ Deployment package uploaded to {remote_file_path}.")
            
            return remote_file_path
        
        except Exception:
            self.logger.exception(f"❌ Upload deployment package failed.")
            raise
    
    def stop_services(self):
        """Stop a list of services"""
        self.ensure_connected()
        services: List[str] = self.config["services"] 

        is_success = True
        for service in services:
            self.logger.info(f'Stopping service: "{service}"...')
            cmd = f'net stop "{service}"'
            _, _, exit_code = self.execute_command(cmd)
            if exit_code != 0:
                self.logger.error(f'❌ Failed to stop "{service}". Check remote execution log for details.')
                is_success = False
            else:
                self.logger.info(f'✅ Service "{service}" stopped successfully.')

        if not is_success:
            raise Exception("Some services failed to stop.")

    def start_services(self):
        """Start a list of services"""
        self.ensure_connected()
        services: List[str] = self.config["services"] 

        is_success = True
        for service in services:
            self.logger.info(f'Starting service: "{service}"...')
            cmd = f'net start "{service}"'
            _, _, exit_code = self.execute_command(cmd)
            if exit_code != 0:
                self.logger.error(f'❌ Failed to start "{service}". Check remote execution log for details.')
                is_success = False
            else:
                self.logger.info(f'✅ Service "{service}" started successfully.')

        if not is_success:
            raise Exception("Some services failed to start.")
       
    
    def extract_deployment_package(self, remote_file: Path):
        self.ensure_connected()
        remote_script_dir = Path(self.config["remote_scripts_dir"])
        extract_script = remote_script_dir / "extract.bat"
        destinations = self.config.get("directories_to_backup", [])
        destinations_args = ' '.join(map(lambda dir: f'"{dir}"', destinations))
        
        cmd = f'{extract_script} "{remote_file}" {destinations_args}'
        _, _, exit_code = self.execute_command(cmd)
        if exit_code != 1:
            self.logger.error(f'❌ Failed to extract deployment package {remote_file} to {destinations}.')
            raise RuntimeError("Extract deployment package failed.")
            
        self.logger.info(f'✅ Extract deloyment package successfully.')
        

    def extract_deployment_package_no_script(self, remote_file: Path):
        self.ensure_connected()
        destinations: Iterable[Path] = map(lambda dest: Path(dest), self.config.get("directories_to_backup", []))

        # Extract the zip package
        sevenzip_path: Path = Path(self.config.get("7zip_path", "C:/Program Files/7-Zip/7z.exe"))
        extracted_package: Path = remote_file.parent / remote_file.stem
        cmd = f'"{sevenzip_path}" x "{remote_file}" -o"{extracted_package}" -y'
        
        self.logger.info(f"Extracting {remote_file}...")
        _, _, exit_code = self.execute_command(cmd)
        if exit_code != 0:
            raise Exception(f"{remote_file} extraction failed.")
        self.logger.info(f"{remote_file} extracted successfully.")

        # Copy the package to destinations
        for destination in destinations:
            '''
            /IS: Include Same => copy non-modified files
            /IT: Include Tweaked => copy modifed files
            /E: Recursively copy subdirectories, including Empty dirs
            /NFL: No File List
            /NDL: No Directory List
            '''
            cmd = f'robocopy "{extracted_package}" "{destination}" /IT /E /NFL /NDL' 

            self.logger.info(f"Copying package {extracted_package} to {destination}...")
            _, _, exit_code = self.execute_command(cmd)
            self.logger.debug(f'robocopy exits with code: {exit_code}')
            if exit_code >= 8: # robocopy-specific exit code behaviour
                raise Exception(f"Copying package to {destination} failed.")
            self.logger.info(f"Copied {extracted_package} to {destination} successfully.")
            



    