"""
Windows System Tray Module for Focus Guard MVP
Minimal system tray implementation for Windows
"""
import sys
import os
from pathlib import Path

# PyQt5 imports for Windows system tray
from PyQt5.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QAction, 
                             QMessageBox, QInputDialog)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QTimer, pyqtSignal, QObject

from focus_guard.core.coordinator import FocusGuardCoordinator
from focus_guard.core.platform_utils.windows.windows_config import WindowsConfig


class FocusGuardTrayApp(QObject):
    """Windows system tray application for Focus Guard MVP"""
    
    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        self.coordinator = None
        self.config = WindowsConfig()
        self.is_monitoring = False
        
        self.setup_tray()
        self.setup_timer()
        
    def setup_tray(self):
        """Setup system tray icon and menu"""
        # Create simple icon (green/red circle)
        self.create_tray_icon()
        
        # Create menu
        self.menu = QMenu()
        
        # Status action
        self.status_action = QAction("Status: Stopped")
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)
        
        self.menu.addSeparator()
        
        # Start/Stop actions
        self.start_action = QAction("Start Monitoring")
        self.start_action.triggered.connect(self.start_monitoring)
        self.menu.addAction(self.start_action)
        
        self.stop_action = QAction("Stop Monitoring")
        self.stop_action.triggered.connect(self.stop_monitoring)
        self.stop_action.setEnabled(False)
        self.menu.addAction(self.stop_action)
        
        self.menu.addSeparator()
        
        # Configuration
        self.config_action = QAction("Configuration")
        self.config_action.triggered.connect(self.open_config)
        self.menu.addAction(self.config_action)
        
        self.menu.addSeparator()
        
        # Exit
        self.exit_action = QAction("Exit")
        self.exit_action.triggered.connect(self.exit_app)
        self.menu.addAction(self.exit_action)
        
        # Setup tray icon
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.setToolTip("Focus Guard - Stopped")
        
        # Show tray icon
        self.tray_icon.show()
        
    def create_tray_icon(self):
        """Create simple tray icon"""
        # Create a simple 16x16 pixmap with red circle (stopped state)
        pixmap = QPixmap(16, 16)
        pixmap.fill()
        
        from PyQt5.QtGui import QPainter, QBrush, QColor
        painter = QPainter(pixmap)
        painter.setBrush(QBrush(QColor("red")))
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        
        self.stopped_icon = QIcon(pixmap)
        
        # Create green circle for running state
        pixmap = QPixmap(16, 16)
        pixmap.fill()
        painter = QPainter(pixmap)
        painter.setBrush(QBrush(QColor("green")))
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        
        self.running_icon = QIcon(pixmap)
        
        # Set initial icon
        self.tray_icon.setIcon(self.stopped_icon)
        
    def setup_timer(self):
        """Setup update timer"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(5000)  # Update every 5 seconds
        
    def start_monitoring(self):
        """Start Focus Guard monitoring"""
        try:
            if not self.coordinator:
                self.coordinator = FocusGuardCoordinator()
            
            self.coordinator.start()
            self.is_monitoring = True
            
            # Update UI
            self.status_action.setText("Status: Running")
            self.start_action.setEnabled(False)
            self.stop_action.setEnabled(True)
            self.tray_icon.setIcon(self.running_icon)
            self.tray_icon.setToolTip("Focus Guard - Running")
            
            # Show notification
            self.tray_icon.showMessage(
                "Focus Guard",
                "Monitoring started",
                QSystemTrayIcon.Information,
                2000
            )
            
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to start monitoring: {e}")
            
    def stop_monitoring(self):
        """Stop Focus Guard monitoring"""
        try:
            if self.coordinator:
                self.coordinator.stop()
            
            self.is_monitoring = False
            
            # Update UI
            self.status_action.setText("Status: Stopped")
            self.start_action.setEnabled(True)
            self.stop_action.setEnabled(False)
            self.tray_icon.setIcon(self.stopped_icon)
            self.tray_icon.setToolTip("Focus Guard - Stopped")
            
            # Show notification
            self.tray_icon.showMessage(
                "Focus Guard",
                "Monitoring stopped",
                QSystemTrayIcon.Information,
                2000
            )
            
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to stop monitoring: {e}")
            
    def open_config(self):
        """Open configuration file"""
        try:
            config_path = self.config.get_config_path()
            
            if not os.path.exists(config_path):
                # Create default config
                self.config.save_config(self.config.default_config)
                
            # Open config file with default editor
            if os.name == 'nt':  # Windows
                os.system(f'notepad "{config_path}"')
            else:
                os.system(f'xdg-open "{config_path}"')
                
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to open configuration: {e}")
            
    def update_status(self):
        """Update status periodically"""
        if self.is_monitoring:
            self.status_action.setText("Status: Running")
        else:
            self.status_action.setText("Status: Stopped")
            
    def exit_app(self):
        """Exit the application"""
        try:
            if self.coordinator:
                self.coordinator.stop()
                
            self.tray_icon.hide()
            self.app.quit()
            
        except Exception as e:
            print(f"Error during exit: {e}")
            self.app.quit()
            
    def run(self):
        """Run the system tray application"""
        return self.app.exec_()


def main():
    """Main entry point for Windows system tray"""
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("System tray is not available on this system")
        return 1
        
    app = FocusGuardTrayApp()
    return app.run()


if __name__ == '__main__':
    sys.exit(main())
