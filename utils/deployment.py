import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List
from typing import Callable, Dict, List, Optional
from dotenv import load_dotenv

from .builder import Builder
from .pipeline import SQLDeploymentPipeline
from .remote import Denis4Client

class DeploymentManager:
    def __init__(self, config: Dict) -> None:
        self.config = config

        # Initiate environment and logging
        self.init_env()
        self.log_dir = self.init_log_dir()
        self.logger = self.init_logger()

        # Initiate helper classes
        self.builder = self.init_builder()
        self.schema_updater = self.init_schema_updater()
        self.remote_client = self.init_remote_client()

    def init_env(self):
        file_directory = Path(__file__)
        root_directory = file_directory.parent.parent
        env_path = root_directory / "configs" / ".env"
        load_dotenv(env_path)

    def init_log_dir(self):
        base_log_dir = Path(self.config["log_dir"]) # absolute path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = base_log_dir / f'deployment_{timestamp}'
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir 

    def init_logger(self):
        log_file = self.log_dir / f'deployment.log'

        logger = logging.getLogger(f"deployment-{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        logger.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        logger.propagate = False # Prevent log messages being propagated to root logger when a new process is spawned
        return logger

    def init_builder(self):
        build_config = self.config.get("build_config", {})
        return Builder(build_config, self.logger)

    def init_schema_updater(self):
        update_schema_config = self.config.get("update_schema_config", {})
        db_connection = {
            "server":   os.getenv("server", ""),
            "database": os.getenv("database", ""),
            "uid":      os.getenv("uid", ""),
            "pwd":      os.getenv("pwd", "")
        }
        return SQLDeploymentPipeline(update_schema_config, db_connection, self.log_dir, self.logger)

    def init_remote_client(self):
        remote_config = self.config.get("remote_config", {})
        remote_config["log_dir"] = self.log_dir
        remote_config["server"] = os.getenv("denis4_server")
        remote_config["user"] = os.getenv("denis4_user")
        remote_config["password"] = os.getenv("denis4_password")
        client = Denis4Client(remote_config, self.logger)
        client.connect_to_denis4()
        return client
    
    def build_projects(self):
        self.builder.build()

    def update_schema(self):
        self.schema_updater.run()

    def publish_artifacts(self) -> Optional[Path]:
        return self.builder.publish()

    def backup_remote(self):
        self.remote_client.backup()
    
    def upload_package_to_remote(self, deployment_package: Path) -> Path:
        if not deployment_package:
            raise Exception("No deployment package created")
        remote_file_path = self.remote_client.upload_deployment_package(deployment_package)
        return remote_file_path
    
    def stop_services(self):
        self.remote_client.stop_services()

    def start_services(self):
        self.remote_client.start_services()

    def extract_deployment_package(self, remote_file: Path):
        self.remote_client.extract_deployment_package(remote_file)

    def parallelize(self, tasks: List[Callable]) -> List:
        num_workers = min(len(tasks), 8)  # Capped at logical core numbers?
        task_to_id = {task : id for id, task in enumerate(tasks)}
        results = [None] * len(tasks)

        with ThreadPoolExecutor(max_workers=num_workers, thread_name_prefix="Worker") as executor:
            # Submit all tasks
            futures = {executor.submit(task): task for task in tasks}
            
            # Wait for completion and handle errors
            for future in as_completed(futures):
                task = futures[future]
                try:
                    result = future.result()
                    results[task_to_id[task]] = result
                    self.logger.info(f"Task {task.__name__} completed successfully")
                except Exception as e:
                    self.logger.error(f"Task {task.__name__} failed: {e}")
                    sys.exit(1)
        
        return results

    def deploy(self):
        self.logger.info(f"Deployment process started.")

        backup_future = None
        try:    
            with ThreadPoolExecutor(max_workers=1) as executor:
                # Backup remote directories while doing local work
                backup_future = executor.submit(self.backup_remote)
                
                # Perform local deployment tasks
                self.build_projects()
                results = self.parallelize([self.publish_artifacts, self.update_schema])
                deployment_package = results[0]
                remote_package = self.upload_package_to_remote(deployment_package)

                # Wait for backup status - exception raises here if failed
                backup_future.result()

                # Performs remote deployment tasks
                self.stop_services()
                self.extract_deployment_package(remote_package)
                self.start_services()

        except Exception:
            self.logger.exception("❌ Deployment failed.")

            if backup_future and not backup_future.done():
                self.logger.warning("Remote backup is not completed.")
                try:
                    self.logger.info("Waiting for remote backup to complete...")
                    backup_future.result(timeout=300)  # Wait up to 5 min
                    self.logger.info("Backup completed.")
                except Exception as e:
                    self.logger.warning(f"Backup failed or timed out: {e}")

            sys.exit(1)
            
        self.logger.info(f"✅ Deployment process completed successfully.")

        
