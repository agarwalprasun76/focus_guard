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
