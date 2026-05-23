# -*- coding: utf-8 -*-
"""
engine/logging.py

Manages the localized, offline transaction logs for patronymic inferences.
Stores execution profiles inside independent, database-specific JSON files
to isolate data and prevent database pollution.
"""

import os
import json
import platform
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any


def get_default_log_dir() -> str:
    """
    Locates the default user application directory for reversibility logs.
    First checks if running inside Gramps to use USER_DIR, otherwise falls back
    to standard OS-specific configurations.
    """
    try:
        from gramps.gen.const import USER_DIR
        return os.path.join(USER_DIR, "reversibility_logs")
    except ImportError:
        # Fallback for offline testing outside active Gramps runtime
        if platform.system() == "Windows":
            appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
            return os.path.join(appdata, "gramps", "reversibility_logs")
        else:
            return os.path.join(os.path.expanduser("~"), ".gramps", "reversibility_logs")


def generate_execution_id() -> str:
    """
    Generates a human-readable, sorting-friendly execution transaction ID.
    Format: exec_YYYYMMDD_HHMMSS
    """
    return datetime.now().strftime("exec_%Y%m%d_%H%M%S")


class InferenceLogManager:
    """
    Manages loading, updating, and writing database-isolated inference transaction logs.
    """
    def __init__(self, db_id: str, log_dir: Optional[str] = None):
        """
        Args:
            db_id (str): The unique database identifier (e.g. leaf name of Gramps DB dir).
            log_dir (str, optional): Custom path to log directory. Defaults to standard user dir.
        """
        # Ensure db_id is safe for file names
        self.db_id = "".join(c for c in db_id if c.isalnum() or c in ("-", "_")).strip()
        self.log_dir = log_dir if log_dir else get_default_log_dir()
        
        # Ensure target logging directory exists
        os.makedirs(self.log_dir, exist_ok=True)

    @property
    def log_filepath(self) -> str:
        """Returns the full path to the database-specific JSON log file."""
        return os.path.join(self.log_dir, f"{self.db_id}.json")

    def load_log(self) -> Dict[str, Any]:
        """
        Loads transaction log data. Returns a blank template if the file
        does not yet exist or is unreadable.
        """
        if not os.path.exists(self.log_filepath):
            return {"database_id": self.db_id, "executions": []}

        try:
            with open(self.log_filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict) or "executions" not in data:
                    return {"database_id": self.db_id, "executions": []}
                return data
        except (json.JSONDecodeError, OSError):
            # Gracefully fall back to an empty structure on corruption or read issues
            return {"database_id": self.db_id, "executions": []}

    def save_log(self, data: Dict[str, Any]) -> None:
        """
        Pretty-prints and writes execution log data to disk.
        """
        with open(self.log_filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def log_execution(
        self,
        execution_id: str,
        plugin_id: str,
        changes: List[Dict[str, Any]]
    ) -> None:
        """
        Appends an execution transaction run record to the log.

        Args:
            execution_id (str): Unique transaction identifier.
            plugin_id (str): Naming plugin responsible for calculations.
            changes (list): List of change dicts, each containing:
                {
                    "person_handle": str,
                    "name_handle": str,
                    "original_value": str,
                    "inferred_value": str,
                    "father_handle": str,
                    "reference_year": int|None,
                    "pre_reform": bool,
                    "confidence_score": float,
                    "applied_heuristics": List[str]
                }
        """
        log_data = self.load_log()
        
        execution_record = {
            "execution_id": execution_id,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "plugin_id": plugin_id,
            "changes": changes
        }

        # Keep latest runs at the head of the list
        log_data["executions"].insert(0, execution_record)
        self.save_log(log_data)

    def get_executions(self) -> List[Dict[str, Any]]:
        """Returns list of completed execution runs sorted latest first."""
        log_data = self.load_log()
        return log_data.get("executions", [])

    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves details of a specific execution run."""
        for run in self.get_executions():
            if run.get("execution_id") == execution_id:
                return run
        return None

    def remove_execution(self, execution_id: str) -> bool:
        """
        Removes a specific execution transaction entry from the log.
        Returns True if found and removed, False otherwise.
        """
        log_data = self.load_log()
        executions = log_data.get("executions", [])
        
        initial_len = len(executions)
        executions = [run for run in executions if run.get("execution_id") != execution_id]
        
        if len(executions) < initial_len:
            log_data["executions"] = executions
            self.save_log(log_data)
            return True
        return False