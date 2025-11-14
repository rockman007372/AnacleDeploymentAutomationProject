import logging
from pathlib import Path
from typing import Dict, List, Optional

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
            "password", 
            "remote_scripts_dir",
        ]
        missing = [k for k in required_keys if k not in config]
        if missing:
            raise ValueError(f"Missing required config keys: {missing}")

    def connect_to_denis4(self):
        server = self.config.get("server", "")
        username = self.config.get("user", "")
        password = self.config.get("password", "")
        try:
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(server, username=username, password=password)
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
            
            if exit_code != 0:
                self.logger.error(f"Command {command} failed with exit code {exit_code}")
                self.logger.error(f"stderr: {stderr_text}")
                return stdout_text, stderr_text, exit_code
                
            # Log stderr even on success (might contain warnings)
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

    def backup(self, directories_to_backup: List[Path], base_backup_dir: Path) -> bool:
        '''
        Create backups at base backup directory for the given directories.
        Execute the "backup.bat" script on remote server, which backups 
        "webapp", "service", "TPAPI" in the given directory.
        '''
        remote_script_dir = Path(self.config["remote_scripts_dir"])
        backup_script = remote_script_dir / "backup.bat"

        # TODO: paralellize? Maybe no need since publishing solution takes a longer time
        for directory in directories_to_backup:
            self.logger.info(f"Backing up {directory}...")
            cmd = f'{backup_script} "{directory}" "{base_backup_dir}"'
            _, _, exit_code = self.execute_command(cmd)
            if exit_code != 0:
                self.logger.error(f"Failed to backup {directory}. Check remote execution log for details.")
                return False
            self.logger.info(f"Back up {directory} successfully.")

        self.logger.info("All backups completed.")
        return True
    
    def upload_file(self, local_path: Path, remote_path: Path) -> bool:
        """Upload a file to remote server"""
        self.ensure_connected()
        try:
            sftp = self.ssh_client.open_sftp()
            sftp.put(str(local_path), str(remote_path))
            sftp.close()
            self.logger.info(f"Uploaded {local_path} to {remote_path} successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Upload {local_path} to {remote_path} failed: {e}")
            return False
        
    def stop_services(self, services: List[str]):
        """Stop a list of services"""
        self.ensure_connected()
        remote_script_dir = Path(self.config["remote_scripts_dir"])
        stop_services_script = remote_script_dir / "stop_services.bat"

        arguments = ' '.join(map(lambda service: f'"{service}"', services))
        cmd = f'{stop_services_script} {arguments}'

        self.logger.info(f"Stopping services: {services}...")
        _, _, exit_code = self.execute_command(cmd)
        if exit_code != 0:
            self.logger.error(f"Failed to stop {services}. Check remote execution log for details.")
        else:
            self.logger.info("Services stopped successfully.")

        return exit_code == 0
        
    def start_services(self, services: List[str]):
        """Start a list of services"""
        self.ensure_connected()
        remote_script_dir = Path(self.config["remote_scripts_dir"])
        start_services_script = remote_script_dir / "start_services.bat"

        arguments = ' '.join(map(lambda service: f'"{service}"', services))
        cmd = f'{start_services_script} {arguments}'

        self.logger.info(f"Starting services: {services}...")
        _, _, exit_code = self.execute_command(cmd)
        if exit_code != 0:
            self.logger.error(f"Failed to start {services}. Check remote execution log for details.")
        else:
            self.logger.info("Services started successfully.")

        return exit_code == 0

    