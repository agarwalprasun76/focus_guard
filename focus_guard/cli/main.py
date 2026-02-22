"""
Cross-platform CLI entry point for Focus Guard
Uses platform-specific implementations under the hood
"""
import click
import sys
import os
from typing import Optional

from focus_guard.core.coordinator import FocusGuardCoordinator
from focus_guard.core.platform_utils.platform_detector import PlatformDetector


@click.group()
@click.version_option(version="1.0.0-mvp")
def cli():
    """Focus Guard CLI - Cross-platform productivity monitoring"""
    pass


@cli.command()
@click.option('--config', '-c', help='Configuration file path')
@click.option('--daemon', '-d', is_flag=True, help='Run in background')
@click.option('--platform', help='Force specific platform (windows, macos, linux)')
def start(config, daemon, platform):
    """Start Focus Guard monitoring"""
    click.echo("Starting Focus Guard...")
    
    try:
        # Detect platform or use forced platform
        detector = PlatformDetector()
        current_platform = platform or detector.detect_platform()
        
        click.echo(f"Platform detected: {current_platform}")
        
        # Use platform-specific implementation
        if current_platform == 'windows':
            from focus_guard.core.platform_utils.windows.windows_cli import WindowsCLI
            cli = WindowsCLI()
            cli.start(config=config, daemon=daemon)
        elif current_platform == 'macos':
            click.echo("macOS implementation coming soon")
        elif current_platform == 'linux':
            click.echo("Linux implementation coming soon")
        else:
            click.echo(f"Unsupported platform: {current_platform}")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Error starting Focus Guard: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--platform', help='Force specific platform')
def stop(platform):
    """Stop Focus Guard monitoring"""
    click.echo("Stopping Focus Guard...")
    
    try:
        detector = PlatformDetector()
        current_platform = platform or detector.detect_platform()
        
        if current_platform == 'windows':
            from focus_guard.core.platform_utils.windows.windows_cli import WindowsCLI
            cli = WindowsCLI()
            cli.stop()
        elif current_platform == 'macos':
            click.echo("macOS implementation coming soon")
        elif current_platform == 'linux':
            click.echo("Linux implementation coming soon")
        else:
            click.echo(f"Unsupported platform: {current_platform}")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Error stopping Focus Guard: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--format', '-f', type=click.Choice(['simple', 'detailed']), default='simple')
@click.option('--platform', help='Force specific platform')
def status(format, platform):
    """Show current monitoring status"""
    click.echo("Focus Guard Status")
    click.echo("=" * 30)
    
    try:
        detector = PlatformDetector()
        current_platform = platform or detector.detect_platform()
        
        if current_platform == 'windows':
            from focus_guard.core.platform_utils.windows.windows_cli import WindowsCLI
            cli = WindowsCLI()
            cli.status(format=format)
        elif current_platform == 'macos':
            click.echo("macOS implementation coming soon")
        elif current_platform == 'linux':
            click.echo("Linux implementation coming soon")
        else:
            click.echo(f"Unsupported platform: {current_platform}")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Error getting status: {e}", err=True)


@cli.command()
@click.option('--platform', help='Force specific platform')
def config(platform):
    """Open configuration editor"""
    click.echo("Opening configuration...")
    
    try:
        detector = PlatformDetector()
        current_platform = platform or detector.detect_platform()
        
        if current_platform == 'windows':
            from focus_guard.core.platform_utils.windows.windows_cli import WindowsCLI
            cli = WindowsCLI()
            cli.config()
        elif current_platform == 'macos':
            click.echo("macOS implementation coming soon")
        elif current_platform == 'linux':
            click.echo("Linux implementation coming soon")
        else:
            click.echo(f"Unsupported platform: {current_platform}")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Error opening config: {e}", err=True)


@cli.command('set-password')
def set_password():
    """Set the admin/parental password for protecting enforcement mode changes.

    This password prevents the monitored user from weakening FocusGuard
    (e.g., switching from 'enforcing' to 'tracking' mode) without authorization.
    """
    import hashlib

    click.echo("FocusGuard Admin Password Setup")
    click.echo("=" * 40)
    click.echo()
    click.echo("This password will be required to change the enforcement mode.")
    click.echo("Choose a strong password that the monitored user does not know.")
    click.echo()

    password = click.prompt("Enter new admin password", hide_input=True)
    if not password or len(password) < 4:
        click.echo("Error: Password must be at least 4 characters.", err=True)
        sys.exit(1)

    confirm = click.prompt("Confirm password", hide_input=True)
    if password != confirm:
        click.echo("Error: Passwords do not match.", err=True)
        sys.exit(1)

    password_hash = hashlib.sha256(password.encode()).hexdigest()

    try:
        from focus_guard.deployment.config import DeploymentConfig
        config = DeploymentConfig.load()
        config.config_password_hash = password_hash
        config.save()
        click.echo()
        click.echo("Admin password set successfully.")
        click.echo("Enforcement mode changes now require this password.")
    except Exception as e:
        click.echo(f"Error saving password: {e}", err=True)
        sys.exit(1)


@cli.command('remove-password')
def remove_password():
    """Remove the admin/parental password (requires current password)."""
    import hashlib

    try:
        from focus_guard.deployment.config import DeploymentConfig
        config = DeploymentConfig.load()

        if not config.config_password_hash:
            click.echo("No admin password is currently set.")
            return

        current = click.prompt("Enter current admin password", hide_input=True)
        current_hash = hashlib.sha256(current.encode()).hexdigest()

        if current_hash != config.config_password_hash:
            click.echo("Error: Incorrect password.", err=True)
            sys.exit(1)

        config.config_password_hash = ""
        config.save()
        click.echo("Admin password removed. Enforcement mode changes no longer require a password.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def version():
    """Show version information"""
    click.echo("Focus Guard MVP v1.0.0")
    click.echo("Cross-platform productivity monitoring system")
    
    try:
        from focus_guard.core.platform_utils.detector import PlatformDetector
        detector = PlatformDetector()
        platform = detector.detect_platform()
        click.echo(f"Current platform: {platform}")
        click.echo(f"Current platform: {platform}")
        click.echo("Platform detection available")
    except:
        click.echo("Platform detection available")


def main():
    """Main entry point for cross-platform CLI"""
    cli()


if __name__ == '__main__':
    main()
