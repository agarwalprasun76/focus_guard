"""
TaskManager: Handles loading, saving, and managing task profiles.
"""
from typing import List, Dict, Any

class TaskManager:
    def __init__(self, config_path: str):
        """Initialize TaskManager with path to task_profiles.json."""
        pass

    def load_tasks(self) -> List[Dict[str, Any]]:
        """Load task profiles from config file."""
        pass

    def select_task(self, task_name: str) -> None:
        """Set the current task by name."""
        pass

    def get_current_task(self) -> Dict[str, Any]:
        """Return the current task profile."""
        pass
