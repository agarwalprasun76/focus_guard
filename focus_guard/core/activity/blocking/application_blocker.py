"""
Application blocker for process termination and blocking enforcement.

This module provides the ApplicationBlocker class that handles the actual
blocking of applications based on policy decisions.
"""

import os
import sys
import time
import threading
import subprocess
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
import logging

from focus_guard.core.activity.blocking.models import BlockingDecision, BlockingEvent, BlockingAction
from focus_guard.core.activity.blocking.policy_engine import PolicyEngine
from focus_guard.core.activity.models import WindowInfo

logger = logging.getLogger(__name__)


class ProcessManager:
    """Cross-platform process management utilities."""
    
    @staticmethod
    def get_process_by_name(process_name: str) -> List[Dict[str, Any]]:
        """
        Get processes by name.
        
        Args:
            process_name: Name of the process to find
            
        Returns:
            List[Dict[str, Any]]: List of process information dictionaries
        """
        processes = []
        
        if sys.platform == "win32":
            try:
                import psutil
                for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
                    try:
                        if process_name.lower() in proc.info['name'].lower():
                            processes.append({
                                'pid': proc.info['pid'],
                                'name': proc.info['name'],
                                'exe': proc.info['exe'],
                                'cmdline': proc.info['cmdline']
                            })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except ImportError:
                # Fallback to tasklist on Windows
                try:
                    result = subprocess.run(
                        ['tasklist', '/fo', 'csv', '/nh'],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        for line in result.stdout.strip().split('\n'):
                            parts = line.split('","')
                            if len(parts) >= 2:
                                name = parts[0].strip('"')
                                pid = parts[1].strip('"')
                                if process_name.lower() in name.lower():
                                    processes.append({
                                        'pid': int(pid),
                                        'name': name,
                                        'exe': name,
                                        'cmdline': []
                                    })
                except Exception as e:
                    logger.error(f"Error getting processes with tasklist: {e}")
        
        return processes
    
    @staticmethod
    def terminate_process(pid: int, force: bool = False) -> bool:
        """
        Terminate a process by PID.
        
        Args:
            pid: Process ID to terminate
            force: If True, force kill the process
            
        Returns:
            bool: True if process was terminated successfully
        """
        try:
            if sys.platform == "win32":
                try:
                    import psutil
                    proc = psutil.Process(pid)
                    if force:
                        proc.kill()
                    else:
                        proc.terminate()
                    return True
                except ImportError:
                    # Fallback to taskkill on Windows
                    cmd = ['taskkill', '/PID', str(pid)]
                    if force:
                        cmd.append('/F')
                    result = subprocess.run(cmd, capture_output=True, timeout=10)
                    return result.returncode == 0
            else:
                # Unix-like systems
                import signal
                os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
                return True
        except Exception as e:
            logger.error(f"Error terminating process {pid}: {e}")
            return False
    
    @staticmethod
    def is_process_running(pid: int) -> bool:
        """
        Check if a process is still running.
        
        Args:
            pid: Process ID to check
            
        Returns:
            bool: True if process is running
        """
        try:
            if sys.platform == "win32":
                try:
                    import psutil
                    return psutil.pid_exists(pid)
                except ImportError:
                    # Fallback method for Windows
                    result = subprocess.run(
                        ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV'],
                        capture_output=True, text=True, timeout=5
                    )
                    return str(pid) in result.stdout
            else:
                # Unix-like systems
                os.kill(pid, 0)  # Signal 0 checks if process exists
                return True
        except (OSError, subprocess.TimeoutExpired):
            return False


class ApplicationBlocker:
    """
    Application blocker that enforces blocking decisions.
    
    This class handles the actual blocking of applications based on policy
    decisions, including graceful shutdown, warnings, and process termination.
    """
    
    def __init__(self, policy_engine: PolicyEngine):
        """
        Initialize the application blocker.
        
        Args:
            policy_engine: PolicyEngine instance for making blocking decisions
        """
        self.policy_engine = policy_engine
        self.process_manager = ProcessManager()
        
        # Tracking
        self.blocked_processes: Dict[int, Dict[str, Any]] = {}  # pid -> block_info
        self.warning_processes: Dict[int, Dict[str, Any]] = {}  # pid -> warning_info
        self.grace_period_processes: Dict[int, Dict[str, Any]] = {}  # pid -> grace_info
        
        # Callbacks
        self.block_callbacks: List[Callable[[BlockingEvent], None]] = []
        self.warning_callbacks: List[Callable[[BlockingEvent], None]] = []
        
        # Threading
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Statistics
        self.total_blocks = 0
        self.total_warnings = 0
        self.total_grace_periods = 0
    
    def start_monitoring(self):
        """Start monitoring and blocking enforcement."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Application blocking monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring and blocking enforcement."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        logger.info("Application blocking monitoring stopped")
    
    def evaluate_and_block(self, window_info: WindowInfo) -> BlockingDecision:
        """
        Evaluate an application and apply blocking if necessary.
        
        Args:
            window_info: Information about the application window
            
        Returns:
            BlockingDecision: The decision made by the policy engine
        """
        decision = self.policy_engine.evaluate_application(window_info)
        
        if decision.should_block():
            self._handle_blocking_decision(decision, window_info)
        elif decision.should_warn():
            self._handle_warning_decision(decision, window_info)
        
        return decision
    
    def _handle_blocking_decision(self, decision: BlockingDecision, window_info: WindowInfo):
        """
        Handle a blocking decision by terminating or warning about the process.
        
        Args:
            decision: The blocking decision
            window_info: Information about the application window
        """
        pid = int(window_info.pid) if window_info.pid else None
        
        if not pid:
            logger.warning(f"Cannot block {window_info.app_name}: No PID available")
            return
        
        with self._lock:
            # Check if we're already handling this process
            if pid in self.blocked_processes or pid in self.grace_period_processes:
                return
            
            # Start grace period if configured
            if decision.grace_period_seconds > 0:
                self._start_grace_period(decision, window_info, pid)
            else:
                self._block_process_immediately(decision, window_info, pid)
    
    def _handle_warning_decision(self, decision: BlockingDecision, window_info: WindowInfo):
        """
        Handle a warning decision by showing a warning notification.
        
        Args:
            decision: The warning decision
            window_info: Information about the application window
        """
        pid = int(window_info.pid) if window_info.pid else None
        
        if not pid:
            return
        
        with self._lock:
            if pid not in self.warning_processes:
                self.warning_processes[pid] = {
                    'decision': decision,
                    'window_info': window_info,
                    'warning_time': datetime.now(),
                    'warning_count': 0
                }
                self.total_warnings += 1
        
        # Notify warning callbacks
        event = BlockingEvent(
            event_type="warned",
            app_name=window_info.app_name,
            domain=str(window_info.domain) if window_info.domain else None,
            window_title=window_info.window_title,
            policy_name=decision.policy_name,
            reason=decision.reason
        )
        
        for callback in self.warning_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in warning callback: {e}")
        
        logger.info(f"Warning issued for {window_info.app_name}: {decision.reason}")
    
    def _start_grace_period(self, decision: BlockingDecision, window_info: WindowInfo, pid: int):
        """
        Start a grace period before blocking a process.
        
        Args:
            decision: The blocking decision
            window_info: Information about the application window
            pid: Process ID
        """
        grace_end = datetime.now() + timedelta(seconds=decision.grace_period_seconds)
        
        self.grace_period_processes[pid] = {
            'decision': decision,
            'window_info': window_info,
            'grace_end': grace_end,
            'notified': False
        }
        self.total_grace_periods += 1
        
        logger.info(f"Grace period started for {window_info.app_name}: {decision.grace_period_seconds}s")
    
    def _block_process_immediately(self, decision: BlockingDecision, window_info: WindowInfo, pid: int):
        """
        Block a process immediately.
        
        Args:
            decision: The blocking decision
            window_info: Information about the application window
            pid: Process ID
        """
        # Attempt to terminate the process
        success = self.process_manager.terminate_process(pid, force=False)
        
        if success:
            self.blocked_processes[pid] = {
                'decision': decision,
                'window_info': window_info,
                'block_time': datetime.now(),
                'termination_success': True
            }
            self.total_blocks += 1
            
            # Create blocking event
            event = BlockingEvent(
                event_type="blocked",
                app_name=window_info.app_name,
                domain=str(window_info.domain) if window_info.domain else None,
                window_title=window_info.window_title,
                policy_name=decision.policy_name,
                reason=decision.reason
            )
            
            # Notify callbacks
            for callback in self.block_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Error in block callback: {e}")
            
            logger.info(f"Blocked application: {window_info.app_name} (PID: {pid})")
        else:
            logger.error(f"Failed to terminate process: {window_info.app_name} (PID: {pid})")
    
    def _monitoring_loop(self):
        """Main monitoring loop for handling grace periods and cleanup."""
        while self._monitoring:
            try:
                with self._lock:
                    self._process_grace_periods()
                    self._cleanup_finished_processes()
                
                time.sleep(1.0)  # Check every second
            except Exception as e:
                logger.error(f"Error in blocking monitoring loop: {e}")
                time.sleep(1.0)
    
    def _process_grace_periods(self):
        """Process active grace periods and block when they expire."""
        now = datetime.now()
        expired_pids = []
        
        for pid, grace_info in self.grace_period_processes.items():
            if now >= grace_info['grace_end']:
                # Grace period expired, block the process
                decision = grace_info['decision']
                window_info = grace_info['window_info']
                
                self._block_process_immediately(decision, window_info, pid)
                expired_pids.append(pid)
            elif not grace_info['notified']:
                # Send grace period notification (first time only)
                remaining_seconds = (grace_info['grace_end'] - now).total_seconds()
                
                event = BlockingEvent(
                    event_type="grace_period",
                    app_name=grace_info['window_info'].app_name,
                    domain=str(grace_info['window_info'].domain) if grace_info['window_info'].domain else None,
                    window_title=grace_info['window_info'].window_title,
                    policy_name=grace_info['decision'].policy_name,
                    reason=f"Grace period: {remaining_seconds:.0f}s remaining"
                )
                
                for callback in self.warning_callbacks:
                    try:
                        callback(event)
                    except Exception as e:
                        logger.error(f"Error in grace period callback: {e}")
                
                grace_info['notified'] = True
        
        # Remove expired grace periods
        for pid in expired_pids:
            del self.grace_period_processes[pid]
    
    def _cleanup_finished_processes(self):
        """Clean up tracking for processes that are no longer running."""
        finished_pids = []
        
        # Check blocked processes
        for pid in list(self.blocked_processes.keys()):
            if not self.process_manager.is_process_running(pid):
                finished_pids.append(pid)
        
        # Check warning processes
        for pid in list(self.warning_processes.keys()):
            if not self.process_manager.is_process_running(pid):
                finished_pids.append(pid)
        
        # Check grace period processes
        for pid in list(self.grace_period_processes.keys()):
            if not self.process_manager.is_process_running(pid):
                finished_pids.append(pid)
        
        # Remove finished processes
        for pid in finished_pids:
            self.blocked_processes.pop(pid, None)
            self.warning_processes.pop(pid, None)
            self.grace_period_processes.pop(pid, None)
    
    def force_terminate_process(self, app_name: str) -> bool:
        """
        Force terminate all processes matching the application name.
        
        Args:
            app_name: Name of the application to terminate
            
        Returns:
            bool: True if at least one process was terminated
        """
        processes = self.process_manager.get_process_by_name(app_name)
        terminated_count = 0
        
        for proc_info in processes:
            if self.process_manager.terminate_process(proc_info['pid'], force=True):
                terminated_count += 1
                logger.info(f"Force terminated {app_name} (PID: {proc_info['pid']})")
        
        return terminated_count > 0
    
    def add_block_callback(self, callback: Callable[[BlockingEvent], None]):
        """Add a callback for blocking events."""
        self.block_callbacks.append(callback)
    
    def remove_block_callback(self, callback: Callable[[BlockingEvent], None]):
        """Remove a blocking event callback."""
        if callback in self.block_callbacks:
            self.block_callbacks.remove(callback)
    
    def add_warning_callback(self, callback: Callable[[BlockingEvent], None]):
        """Add a callback for warning events."""
        self.warning_callbacks.append(callback)
    
    def remove_warning_callback(self, callback: Callable[[BlockingEvent], None]):
        """Remove a warning event callback."""
        if callback in self.warning_callbacks:
            self.warning_callbacks.remove(callback)
    
    def get_blocking_statistics(self) -> Dict[str, Any]:
        """
        Get blocking statistics.
        
        Returns:
            Dict[str, Any]: Blocking statistics
        """
        with self._lock:
            return {
                'total_blocks': self.total_blocks,
                'total_warnings': self.total_warnings,
                'total_grace_periods': self.total_grace_periods,
                'active_blocked_processes': len(self.blocked_processes),
                'active_warning_processes': len(self.warning_processes),
                'active_grace_periods': len(self.grace_period_processes),
                'monitoring_active': self._monitoring
            }
    
    def get_active_processes(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get information about currently tracked processes.
        
        Returns:
            Dict[str, List[Dict[str, Any]]]: Dictionary of process lists by category
        """
        with self._lock:
            return {
                'blocked': [
                    {
                        'pid': pid,
                        'app_name': info['window_info'].app_name,
                        'block_time': info['block_time'].isoformat(),
                        'policy_name': info['decision'].policy_name,
                        'reason': info['decision'].reason
                    }
                    for pid, info in self.blocked_processes.items()
                ],
                'warned': [
                    {
                        'pid': pid,
                        'app_name': info['window_info'].app_name,
                        'warning_time': info['warning_time'].isoformat(),
                        'warning_count': info['warning_count'],
                        'policy_name': info['decision'].policy_name
                    }
                    for pid, info in self.warning_processes.items()
                ],
                'grace_period': [
                    {
                        'pid': pid,
                        'app_name': info['window_info'].app_name,
                        'grace_end': info['grace_end'].isoformat(),
                        'remaining_seconds': (info['grace_end'] - datetime.now()).total_seconds(),
                        'policy_name': info['decision'].policy_name
                    }
                    for pid, info in self.grace_period_processes.items()
                ]
            }
