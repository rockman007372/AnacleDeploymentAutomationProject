import logging
from pathlib import Path
from typing import Dict

import paramiko

config = {
    "log_dir": "",
    "server": "",
    "user": "",
    "password": "",
    "remote_scripts_dir": "",
    "base_backup_dir": "",
    "directories_to_backup": [],
}

class Denis4Client():
    def __init__(self, config: Dict, logger: logging.Logger) -> None:
        self.validate_config(config)
        self.config = config
        self.logger = logger or logging.getLogger()
        self.ssh_client = paramiko.SSHClient()
        self.connect_to_denis4()
        self.execution_log = self.create_execution_log_file()

    def validate_config(self, config: Dict):
        required_keys = [
            "log_dir",
            "server", 
            "user", 
            "password", 
            "remote_scripts_dir",
            "base_backup_dir", 
            "directories_to_backup",
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
            self.logger.info(f"Connected to {server}")
        except Exception as e:
            self.logger.error(f"Failed to connect to {server}: {e}")
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

    def execute_command(self, command: str) -> tuple[str, str, int]:
        self.ensure_connected()
        try:
            _, stdout, stderr = self.ssh_client.exec_command(command)
            
            # Wait for command to complete and get exit code
            exit_code = stdout.channel.recv_exit_status()
            
            stdout_text = stdout.read().decode()
            stderr_text = stderr.read().decode()
            
            if exit_code != 0:
                self.logger.error(f"Command {command} failed with exit code {exit_code}")
                self.logger.error(f"stderr: {stderr_text}")
                return stdout_text, stderr_text, exit_code
                
            # Log stderr even on success (might contain warnings)
            if stderr_text:
                self.logger.warning(f"stderr: {stderr_text}")
            
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

    def create_execution_log_file(self) -> Path:
        '''
        Return the path of the execution log file, 
        which stores all stdout/stderr info from the remote server.
        '''
        log_dir = Path(self.config["log_dir"])
        log_file = log_dir / "denis4.log"

        if not log_file.exists():
            log_file.mkdir(parents=True, exist_ok=True)

        return log_file

    def backup(self):
        remote_script_dir = Path(self.config["remote_script_dir"])
        backup_script = remote_script_dir / "backup.bat"
        base_backup_dir = Path(self.config["base_backup_dir"])
        directories_to_backup = map(lambda dir: Path(dir), self.config.get("directories_to_backup", []))

        # TODO: paralellize
        for directory in directories_to_backup:
            cmd = f'{backup_script} {directory} {base_backup_dir}'
            stdout, stderr, exit_code = self.execute_command(cmd)


        self.logger.info("Backup completed.")
    
    def upload_file(self, local_path: str, remote_path: str):
        """Upload a file to remote server"""
        self.ensure_connected()
        try:
            sftp = self.ssh_client.open_sftp()
            sftp.put(local_path, remote_path)
            sftp.close()
            self.logger.info(f"Uploaded {local_path} to {remote_path}")
        except Exception as e:
            self.logger.error(f"Upload failed: {e}")
            raise
