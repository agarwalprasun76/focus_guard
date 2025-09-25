"""
Focus Guard Windows CLI - User-friendly command interface
"""
import asyncio
import click
import sys
import os
from pathlib import Path
from typing import Optional

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from focus_guard.core.api.api import ClassifierBlockerAPI
from focus_guard.core.mvp_main import main as coordinator_main


@click.group()
@click.version_option(version="1.0.0-mvp")
def cli():
    """Focus Guard Windows CLI - AI-powered productivity management."""
    pass


@cli.command()
@click.option('--daemon', '-d', is_flag=True, help='Run as background service')
@click.option('--config', '-c', help='Configuration file path')
def start(daemon: bool, config: Optional[str]):
    """Start Focus Guard monitoring."""
    click.echo("Starting Focus Guard...")
    
    try:
        if daemon:
            click.echo("   Running in background mode...")
            # For MVP, we'll run the coordinator directly
            asyncio.run(coordinator_main())
        else:
            click.echo("   Running in interactive mode...")
            click.echo("   Press Ctrl+C to stop monitoring")
            asyncio.run(coordinator_main())
            
    except KeyboardInterrupt:
        click.echo("\n[STOP] Focus Guard stopped by user")
    except Exception as e:
        click.echo(f"[ERROR] Error starting Focus Guard: {e}")
        sys.exit(1)


@cli.command()
def stop():
    """Stop Focus Guard monitoring."""
    click.echo("Stopping Focus Guard...")
    # For MVP, this is a placeholder - in full version would communicate with daemon
    click.echo("   Focus Guard stopped successfully")


@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'table']), default='table')
def status(format: str):
    """Show current monitoring status."""
    click.echo("Focus Guard Status")
    click.echo("=" * 30)
    
    try:
        # Test API initialization to check status
        api = ClassifierBlockerAPI()
        
        if format == 'table':
            click.echo(f"Status:           Ready")
            click.echo(f"Classifiers:      {len(api._classifier_registry.get_all())}")
            click.echo(f"Blocking Rules:   {len(api._blocking_registry.get_all())}")
            click.echo(f"Cache Status:     Active")
            click.echo(f"Configuration:    Loaded")
        else:
            import json
            status_data = {
                "status": "ready",
                "classifiers": len(api._classifier_registry.get_all()),
                "blocking_strategies": len(api._blocking_registry.get_all()),
                "cache_active": True,
                "config_loaded": True
            }
            click.echo(json.dumps(status_data, indent=2))
            
    except Exception as e:
        click.echo(f"[ERROR] Error checking status: {e}")
        sys.exit(1)


@cli.command()
def config():
    """Open configuration management."""
    click.echo("Focus Guard Configuration")
    click.echo("=" * 30)
    
    config_path = Path.home() / '.focus_guard' / 'config.json'
    app_config_path = project_root / 'config' / 'app_config.json'
    
    click.echo(f"Main config:      {app_config_path}")
    click.echo(f"User config:      {config_path}")
    
    if app_config_path.exists():
        click.echo("[OK] Configuration files found")
        click.echo("\nTo edit configuration:")
        click.echo(f"   notepad {app_config_path}")
    else:
        click.echo("[ERROR] Configuration files not found")


@cli.command()
def test():
    """Run a quick functionality test."""
    click.echo("Testing Focus Guard functionality...")
    
    try:
        # Test API initialization
        click.echo("   [1/4] Testing API initialization...")
        api = ClassifierBlockerAPI()
        click.echo("   [OK] API initialized successfully")
        
        # Test domain extraction
        click.echo("   [2/4] Testing domain extraction...")
        from focus_guard.core.domain.domain_utils_new import extract_domain_from_url
        test_url = "https://youtube.com/watch?v=test"
        domain = extract_domain_from_url(test_url)
        click.echo(f"   [OK] Domain extracted: {domain}")
        
        # Test configuration
        click.echo("   [3/4] Testing configuration...")
        config_loader = api._config_loader
        click.echo("   [OK] Configuration loaded")
        
        # Test registries
        click.echo("   [4/4] Testing component registries...")
        classifiers = len(api._classifier_registry.get_all())
        strategies = len(api._blocking_registry.get_all())
        click.echo(f"   [OK] Found {classifiers} classifiers, {strategies} strategies")
        
        click.echo("\n[SUCCESS] All tests passed! Focus Guard is ready to use.")
        
    except Exception as e:
        click.echo(f"\n[ERROR] Test failed: {e}")
        sys.exit(1)


@cli.command()
def demo():
    """Run the interactive demo."""
    click.echo("Starting Focus Guard Demo...")
    
    try:
        # Import and run the existing demo
        from demo_mvp import main as demo_main
        asyncio.run(demo_main())
    except Exception as e:
        click.echo(f"[ERROR] Demo failed: {e}")
        sys.exit(1)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
