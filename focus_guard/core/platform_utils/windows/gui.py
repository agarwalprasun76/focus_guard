"""
Windows-specific GUI implementation using PyQt5
System tray application for Windows Focus Guard
"""
import sys
import os
from pathlib import Path

from PyQt5.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QAction, 
                             QMessageBox, QInputDialog)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QTimer

from focus_guard.windows_config import WindowsConfig
from focus_guard.core.coordinator import FocusGuardCoordinator


class WindowsGUI:
    """Windows-specific system tray GUI"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        self.coordinator = None
        self.config = WindowsConfig()
        self.is_monitoring = False
        
    def run(self):
        """Run the Windows system tray application"""
        self.setup_tray()
        return self.app.exec_()
        
    def setup_tray(self):
        """Setup system tray icon and menu"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(None, "Error", "System tray is not available")
            return False
            
        self.create_tray_icon()
        self.create_menu()
        
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.setToolTip("Focus Guard - Stopped")
        self.tray_icon.show()
        
        # Setup update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(5000)
        
        return True
        
    def create_tray_icon(self):
        """Create simple tray icons"""
        # Create stopped icon (red)
        pixmap = QPixmap(16, 16)
        pixmap.fill()
        from PyQt5.QtGui import QPainter, QBrush, QColor
        painter = QPainter(pixmap)
        painter.setBrush(QBrush(QColor("red")))
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        self.stopped_icon = QIcon(pixmap)
        
        # Create running icon (green)
        pixmap = QPixmap(16, 16)
        pixmap.fill()
        painter = QPainter(pixmap)
        painter.setBrush(QBrush(QColor("green")))
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        self.running_icon = QIcon(pixmap)
        
    def create_menu(self):
        """Create system tray menu"""
        self.menu = QMenu()
        
        # Status indicator
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
        
        # Status
        self.status_detail_action = QAction("Show Status")
        self.status_detail_action.triggered.connect(self.show_status)
        self.menu.addAction(self.status_detail_action)
        
        self.menu.addSeparator()
        
        # Exit
        self.exit_action = QAction("Exit")
        self.exit_action.triggered.connect(self.exit_app)
        self.menu.addAction(self.exit_action)
        
    def start_monitoring(self):
        """Start monitoring"""
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
            
            self.tray_icon.showMessage(
                "Focus Guard",
                "Monitoring started",
                QSystemTrayIcon.Information,
                2000
            )
            
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to start monitoring: {e}")
            
    def stop_monitoring(self):
        """Stop monitoring"""
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
                self.config.save_config(self.config.default_config)
                
            # Open with Windows default editor
            os.system(f'notepad "{config_path}"')
            
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to open configuration: {e}")
            
    def show_status(self):
        """Show detailed status"""
        try:
            config_data = self.config.load_config()
            
            status_text = f"""Focus Guard Status

Platform: Windows
Monitoring: {'Running' if self.is_monitoring else 'Stopped'}
Blocked domains: {len(config_data.get('blocked_domains', []))}
Check interval: {config_data.get('check_interval', 30)}s
Configuration: {self.config.get_config_path()}"""
            
            QMessageBox.information(None, "Status", status_text)
            
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to get status: {e}")
            
    def update_status(self):
        """Update status display"""
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
