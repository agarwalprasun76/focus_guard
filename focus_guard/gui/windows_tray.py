"""
Focus Guard Windows System Tray Application
"""
import sys
import os
import subprocess
import winreg
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QAction, 
                            QMessageBox, QWidget)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QTimer, QThread, pyqtSignal

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class FocusGuardWorker(QThread):
    """Worker thread for running Focus Guard coordinator."""
    status_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.running = False
        
    def run(self):
        """Run the Focus Guard coordinator in background."""
        try:
            self.status_changed.emit("starting")
            self.running = True
            
            # Import and run coordinator
            from focus_guard.core.mvp_main import main as coordinator_main
            import asyncio
            
            # Run the coordinator
            asyncio.run(coordinator_main())
            
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.running = False
            self.status_changed.emit("stopped")
    
    def stop_monitoring(self):
        """Stop the monitoring process."""
        self.running = False
        self.terminate()


class WindowsTrayApp(QWidget):
    """Windows System Tray Application for Focus Guard."""
    
    def __init__(self):
        super().__init__()
        self.worker = None
        self.monitoring_active = False
        
        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Set up the tray icon
        self.setup_tray_icon()
        self.create_tray_menu()
        
        # Set up status checking timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(5000)  # Check every 5 seconds
        
        # Show the tray icon
        self.tray_icon.show()
        
        # Setup autostart
        self.setup_autostart()
        
        # Show initial notification
        self.show_notification("Focus Guard Started", 
                             "Focus Guard is now running in the system tray.")
    
    def setup_tray_icon(self):
        """Set up the system tray icon."""
        # Create a simple icon (in a real app, you'd use a proper icon file)
        pixmap = QPixmap(16, 16)
        pixmap.fill()  # Fill with default color
        icon = QIcon(pixmap)
        
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Focus Guard - AI-powered productivity management")
        
        # Handle tray icon activation
        self.tray_icon.activated.connect(self.on_tray_activated)
    
    def create_tray_menu(self):
        """Create the right-click context menu."""
        menu = QMenu()
        
        # Status section
        self.status_action = QAction("Status: Ready", self)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)
        menu.addSeparator()
        
        # Control actions
        self.start_action = QAction("🚀 Start Monitoring", self)
        self.start_action.triggered.connect(self.start_monitoring)
        menu.addAction(self.start_action)
        
        self.stop_action = QAction("🛑 Stop Monitoring", self)
        self.stop_action.triggered.connect(self.stop_monitoring)
        self.stop_action.setEnabled(False)
        menu.addAction(self.stop_action)
        
        menu.addSeparator()
        
        # Configuration and tools
        config_action = QAction("⚙️ Configuration", self)
        config_action.triggered.connect(self.open_configuration)
        menu.addAction(config_action)
        
        test_action = QAction("🧪 Run Test", self)
        test_action.triggered.connect(self.run_test)
        menu.addAction(test_action)
        
        demo_action = QAction("🎬 Run Demo", self)
        demo_action.triggered.connect(self.run_demo)
        menu.addAction(demo_action)
        
        menu.addSeparator()
        
        # Exit
        exit_action = QAction("❌ Exit", self)
        exit_action.triggered.connect(self.exit_application)
        menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(menu)
    
    def on_tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_status_dialog()
    
    def start_monitoring(self):
        """Start Focus Guard monitoring."""
        if self.worker and self.worker.isRunning():
            self.show_notification("Already Running", 
                                 "Focus Guard monitoring is already active.")
            return
        
        try:
            self.worker = FocusGuardWorker()
            self.worker.status_changed.connect(self.on_status_changed)
            self.worker.error_occurred.connect(self.on_error_occurred)
            self.worker.start()
            
            self.monitoring_active = True
            self.start_action.setEnabled(False)
            self.stop_action.setEnabled(True)
            self.status_action.setText("Status: Starting...")
            
            self.show_notification("Monitoring Started", 
                                 "Focus Guard is now actively monitoring your activity.")
            
        except Exception as e:
            self.show_error("Failed to start monitoring", str(e))
    
    def stop_monitoring(self):
        """Stop Focus Guard monitoring."""
        if self.worker and self.worker.isRunning():
            self.worker.stop_monitoring()
            self.worker.wait(3000)  # Wait up to 3 seconds
        
        self.monitoring_active = False
        self.start_action.setEnabled(True)
        self.stop_action.setEnabled(False)
        self.status_action.setText("Status: Stopped")
        
        self.show_notification("Monitoring Stopped", 
                             "Focus Guard monitoring has been stopped.")
    
    def on_status_changed(self, status):
        """Handle status changes from worker thread."""
        if status == "starting":
            self.status_action.setText("Status: Starting...")
        elif status == "running":
            self.status_action.setText("Status: ✅ Running")
        elif status == "stopped":
            self.status_action.setText("Status: Stopped")
            self.monitoring_active = False
            self.start_action.setEnabled(True)
            self.stop_action.setEnabled(False)
    
    def on_error_occurred(self, error_msg):
        """Handle errors from worker thread."""
        self.show_error("Monitoring Error", error_msg)
        self.stop_monitoring()
    
    def update_status(self):
        """Update the status periodically."""
        if self.worker and self.worker.isRunning():
            self.status_action.setText("Status: ✅ Running")
        elif self.monitoring_active:
            self.status_action.setText("Status: Starting...")
        else:
            self.status_action.setText("Status: Ready")
    
    def open_configuration(self):
        """Open configuration file."""
        try:
            config_path = project_root / 'config' / 'app_config.json'
            if config_path.exists():
                os.startfile(str(config_path))
            else:
                self.show_error("Configuration Not Found", 
                              f"Configuration file not found at: {config_path}")
        except Exception as e:
            self.show_error("Failed to open configuration", str(e))
    
    def run_test(self):
        """Run Focus Guard functionality test."""
        try:
            # Run the CLI test command
            result = subprocess.run([
                sys.executable, "-m", "focus_guard.cli.windows_cli", "test"
            ], capture_output=True, text=True, cwd=str(project_root))
            
            if result.returncode == 0:
                self.show_notification("Test Passed", 
                                     "All Focus Guard tests completed successfully!")
            else:
                self.show_error("Test Failed", result.stderr or result.stdout)
                
        except Exception as e:
            self.show_error("Test Error", str(e))
    
    def run_demo(self):
        """Run the Focus Guard demo."""
        try:
            # Run the demo in a new process
            subprocess.Popen([
                sys.executable, "-m", "focus_guard.cli.windows_cli", "demo"
            ], cwd=str(project_root))
            
            self.show_notification("Demo Started", 
                                 "Focus Guard demo is running in a new window.")
                                 
        except Exception as e:
            self.show_error("Demo Error", str(e))
    
    def show_status_dialog(self):
        """Show detailed status dialog."""
        try:
            from focus_guard.core.api.api import ClassifierBlockerAPI
            api = ClassifierBlockerAPI()
            
            status_text = f"""Focus Guard Status
            
Status: {'✅ Running' if self.monitoring_active else '⏹️ Stopped'}
Classifiers: {len(api._classifier_registry.get_all())}
Blocking Strategies: {len(api._blocking_registry.get_all())}
Cache: Active
Configuration: Loaded

Double-click tray icon to show this dialog.
Right-click for menu options."""
            
            QMessageBox.information(self, "Focus Guard Status", status_text)
            
        except Exception as e:
            QMessageBox.warning(self, "Status Error", f"Error getting status: {e}")
    
    def setup_autostart(self):
        """Set up Windows autostart registry entry."""
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, 
                               winreg.KEY_SET_VALUE)
            
            # Set the registry value to start the tray app
            app_path = f'"{sys.executable}" -m focus_guard.gui.windows_tray'
            winreg.SetValueEx(key, "FocusGuard", 0, winreg.REG_SZ, app_path)
            winreg.CloseKey(key)
            
        except Exception as e:
            print(f"Warning: Could not set up autostart: {e}")
    
    def show_notification(self, title, message):
        """Show system tray notification."""
        if self.tray_icon.supportsMessages():
            self.tray_icon.showMessage(title, message, 
                                     QSystemTrayIcon.Information, 3000)
    
    def show_error(self, title, message):
        """Show error notification."""
        if self.tray_icon.supportsMessages():
            self.tray_icon.showMessage(title, message, 
                                     QSystemTrayIcon.Critical, 5000)
        QMessageBox.critical(self, title, message)
    
    def exit_application(self):
        """Exit the application."""
        if self.worker and self.worker.isRunning():
            self.stop_monitoring()
        
        QApplication.quit()


def main():
    """Main entry point for the tray application."""
    app = QApplication(sys.argv)
    
    # Check if system tray is available
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "System Tray", 
                           "System tray is not available on this system.")
        sys.exit(1)
    
    # Prevent application from quitting when last window is closed
    app.setQuitOnLastWindowClosed(False)
    
    # Create and show the tray application
    tray_app = WindowsTrayApp()
    
    # Run the application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
