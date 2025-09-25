"""
Windows CLI for Focus Guard MVP
Minimal command-line interface for Windows-only implementation
"""
import click
import sys
import os
import json
from pathlib import Path
from typing import Dict, Any

from focus_guard.core.coordinator import FocusGuardCoordinator
from focus_guard.core.platform_utils.windows.windows_config import WindowsConfig


class WindowsCLI:
    """Windows-specific CLI implementation for Focus Guard MVP"""
    
    def __init__(self):
        """Initialize Windows CLI"""
        pass
    
    def start(self, config=None, daemon=False):
        """Start Focus Guard monitoring"""
        click.echo("Starting Focus Guard Windows MVP...")
        
        try:
            # Load configuration
            windows_config = WindowsConfig(config_path=config)
            config_data = windows_config.load_config()
            
            click.echo(f"Configuration loaded: {len(config_data)} settings")
            click.echo(f"Monitoring {len(config_data.get('blocked_domains', []))} blocked domains")
            
            # Initialize coordinator
            coordinator = FocusGuardCoordinator()
            
            if daemon:
                click.echo("Running in daemon mode...")
                # Run in background
                import threading
                monitor_thread = threading.Thread(target=coordinator.start)
                monitor_thread.daemon = True
                monitor_thread.start()
                click.echo("Focus Guard started in background")
            else:
                click.echo("Starting interactive monitoring...")
                coordinator.start()
                click.echo("Focus Guard monitoring active")
                
        except Exception as e:
            click.echo(f"Error starting Focus Guard: {e}", err=True)
            sys.exit(1)
    
    def stop(self):
        """Stop Focus Guard monitoring"""
        click.echo("Stopping Focus Guard...")
        
        try:
            coordinator = FocusGuardCoordinator()
            coordinator.stop()
            click.echo("Focus Guard stopped")
        except Exception as e:
            click.echo(f"Error stopping Focus Guard: {e}", err=True)
            sys.exit(1)
    
    def status(self, format='simple'):
        """Show current monitoring status"""
        click.echo("Focus Guard Status")
        click.echo("=" * 30)
        
        try:
            config = WindowsConfig()
            config_data = config.load_config()
            
            if format == 'simple':
                click.echo("Status: Running")
                click.echo(f"Blocked domains: {len(config_data.get('blocked_domains', []))}")
                click.echo(f"Check interval: {config_data.get('check_interval', 30)}s")
                click.echo(f"Monitoring: {'Enabled' if config_data.get('monitoring_enabled', True) else 'Disabled'}")
            else:
                click.echo(json.dumps(config_data, indent=2))
                
        except Exception as e:
            click.echo(f"Error getting status: {e}", err=True)
    
    def config(self):
        """Open configuration editor"""
        try:
            config = WindowsConfig()
            config_path = config.config_path
            
            # Ensure config directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create default config if it doesn't exist
            if not config_path.exists():
                default_config = {
                    "monitoring_enabled": True,
                    "check_interval": 30,
                    "blocked_domains": ["facebook.com", "youtube.com", "twitter.com"],
                    "allowed_apps": ["notepad.exe", "chrome.exe"],
                    "notification_enabled": True
                }
                config.save_config(default_config)
                click.echo(f"Created default configuration at: {config_path}")
            
            click.echo(f"Opening configuration file: {config_path}")
            click.echo("Edit the configuration file, save it, and close the editor to continue...")
            
            if os.name == 'nt':  # Windows
                os.system(f'notepad "{config_path}"')
            else:
                click.echo(f"Edit configuration file: {config_path}")
                
        except Exception as e:
            click.echo(f"Error opening config: {e}", err=True)


# Also provide CLI entry point for direct usage
@click.group()
@click.version_option(version="1.0.0-mvp")
def cli():
    """Focus Guard Windows CLI - Minimal MVP
    
    Windows-only productivity monitoring system
    """
    pass


@cli.command()
@click.option('--config', '-c', help='Configuration file path')
@click.option('--daemon', '-d', is_flag=True, help='Run in background')
def start(config, daemon):
    """Start Focus Guard monitoring"""
    windows_cli = WindowsCLI()
    windows_cli.start(config=config, daemon=daemon)


@cli.command()
def stop():
    """Stop Focus Guard monitoring"""
    windows_cli = WindowsCLI()
    windows_cli.stop()


@cli.command()
@click.option('--format', '-f', type=click.Choice(['simple', 'detailed']), default='simple')
def status(format):
    """Show current monitoring status"""
    windows_cli = WindowsCLI()
    windows_cli.status(format=format)


@cli.command()
def config():
    """Open configuration editor"""
    windows_cli = WindowsCLI()
    windows_cli.config()


@cli.command()
def version():
    """Show version information"""
    click.echo("Focus Guard Windows MVP v1.0.0")
    click.echo("Windows-only productivity monitoring system")
    click.echo("Built with Python, PyQt5, and psutil")


def main():
    """Main entry point for Windows CLI"""
    cli()


if __name__ == '__main__':
    main()
