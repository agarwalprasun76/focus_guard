"""
Cross-platform GUI entry point for Focus Guard
Delegates to platform-specific GUI implementations
"""
import sys
import click
from typing import Optional

from focus_guard.core.platform_utils.detector import PlatformDetector


class GUIMain:
    """Cross-platform GUI main class"""
    
    def __init__(self, platform: Optional[str] = None):
        self.detector = PlatformDetector()
        self.platform = platform or self.detector.detect_platform()
        
    def run(self):
        """Run the appropriate GUI for the current platform"""
        try:
            if self.platform == 'windows':
                from focus_guard.core.platform_utils.windows.gui import WindowsGUI
                gui = WindowsGUI()
                return gui.run()
            elif self.platform == 'macos':
                click.echo("🚧 macOS GUI implementation coming soon")
                return 1
            elif self.platform == 'linux':
                click.echo("🚧 Linux GUI implementation coming soon")
                return 1
            else:
                click.echo(f"❌ Unsupported platform: {self.platform}")
                return 1
                
        except ImportError as e:
            click.echo(f"❌ GUI dependencies not available: {e}")
            click.echo("Try: pip install PyQt5")
            return 1
        except Exception as e:
            click.echo(f"❌ Error starting GUI: {e}")
            return 1


def main():
    """Main GUI entry point"""
    gui = GUIMain()
    return gui.run()


if __name__ == '__main__':
    import sys
    sys.exit(main())
