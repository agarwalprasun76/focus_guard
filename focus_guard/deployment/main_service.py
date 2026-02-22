#!/usr/bin/env python
"""
Focus Guard Activity Monitor - Main Entry Point

This is the main entry point for the deployed activity monitor.
It can run as a Windows service or standalone application.
"""

import sys
import argparse
import logging
import os
import json
from pathlib import Path

# Ensure the package is importable
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    app_path = Path(sys.executable).parent
else:
    # Running as script
    app_path = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(app_path))

from focus_guard.deployment.config import DeploymentConfig
from focus_guard.deployment.service import ActivityMonitorService, run_standalone, run_as_service
from focus_guard.deployment.email_reporter import EmailReporter
from focus_guard.deployment.runtime_startup import RuntimeStartupOrchestrator


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def _apply_runtime_env_overrides(args):
    """Apply runtime startup overrides from CLI args into environment variables."""
    if getattr(args, "no_admin_gateway", False):
        os.environ["FOCUS_GUARD_START_ADMIN_GATEWAY"] = "0"
    if getattr(args, "admin_gateway_host", None):
        os.environ["FOCUS_GUARD_ADMIN_GATEWAY_HOST"] = args.admin_gateway_host
    if getattr(args, "admin_gateway_port", None) is not None:
        os.environ["FOCUS_GUARD_ADMIN_GATEWAY_PORT"] = str(args.admin_gateway_port)
    if getattr(args, "strict_runtime_startup", False):
        os.environ["FOCUS_GUARD_STRICT_RUNTIME_STARTUP"] = "1"


def _build_runtime_orchestrator(config: DeploymentConfig) -> RuntimeStartupOrchestrator:
    """Build runtime orchestrator using deployment config + env overrides."""
    admin_host = os.getenv("FOCUS_GUARD_ADMIN_GATEWAY_HOST", "127.0.0.1").strip() or "127.0.0.1"

    admin_port_raw = os.getenv("FOCUS_GUARD_ADMIN_GATEWAY_PORT", "58393").strip()
    try:
        admin_port = int(admin_port_raw)
    except ValueError:
        admin_port = 58393

    start_admin_gateway = os.getenv("FOCUS_GUARD_START_ADMIN_GATEWAY", "1").strip().lower() in {
        "1",
        "true",
        "yes",
    }

    return RuntimeStartupOrchestrator(
        tab_server_host=config.tab_server_host,
        tab_server_port=config.tab_server_port,
        admin_gateway_host=admin_host,
        admin_gateway_port=admin_port,
        start_admin_gateway=start_admin_gateway,
        logger=logging.getLogger(__name__),
    )


def _render_diagnostics_text(diagnostics: dict) -> str:
    """Render diagnostics payload into a human-readable text format."""
    runtime = diagnostics.get("runtime", {})
    tab = runtime.get("tab_server", {})
    admin = runtime.get("admin_gateway", {})
    env = diagnostics.get("environment", {})
    readiness = diagnostics.get("readiness", {})
    recommendations = diagnostics.get("recommendations", [])

    lines: list[str] = []
    lines.append("FocusGuard Runtime Diagnostics")
    lines.append("=" * 30)
    lines.append(f"Timestamp (UTC): {diagnostics.get('timestamp_utc', 'unknown')}")
    lines.append("")

    lines.append("Readiness")
    lines.append("-" * 9)
    lines.append(f"overall_healthy: {readiness.get('overall_healthy')}")
    lines.append(f"overall_ready: {readiness.get('overall_ready')}")
    lines.append(f"can_start_tab_server: {readiness.get('can_start_tab_server')}")
    lines.append(f"can_start_admin_gateway: {readiness.get('can_start_admin_gateway')}")
    lines.append("")

    lines.append("Tab Server")
    lines.append("-" * 10)
    lines.append(f"endpoint: {tab.get('host')}:{tab.get('port')}")
    lines.append(f"port_available: {tab.get('port_available')}")
    lines.append(f"health_status: {tab.get('health_status')}")
    lines.append(f"healthy: {tab.get('healthy')}")
    lines.append(f"health_payload: {tab.get('health_payload')}")
    lines.append("")

    lines.append("Admin Gateway")
    lines.append("-" * 13)
    lines.append(f"endpoint: {admin.get('host')}:{admin.get('port')}")
    lines.append(f"managed_start_enabled: {admin.get('managed_start_enabled')}")
    lines.append(f"port_available: {admin.get('port_available')}")
    lines.append(f"health_status: {admin.get('health_status')}")
    lines.append(f"meta_status: {admin.get('meta_status')}")
    lines.append(f"healthy: {admin.get('healthy')}")
    lines.append(f"fallback_port_candidate: {admin.get('fallback_port_candidate')}")
    lines.append(f"health_payload: {admin.get('health_payload')}")
    lines.append(f"meta_payload: {admin.get('meta_payload')}")
    lines.append("")

    lines.append("Environment")
    lines.append("-" * 11)
    lines.append(f"python_executable: {env.get('python_executable')}")
    lines.append(f"platform: {env.get('platform')}")
    lines.append(f"uvicorn_module_available: {env.get('uvicorn_module_available')}")
    lines.append(f"is_admin: {env.get('is_admin')}")
    startup_env = env.get("startup_env", {})
    if startup_env:
        lines.append("startup_env:")
        for key, value in startup_env.items():
            lines.append(f"  {key}={value}")
    lines.append("")

    lines.append("Recommendations")
    lines.append("-" * 15)
    if recommendations:
        for idx, recommendation in enumerate(recommendations, start=1):
            lines.append(f"{idx}. {recommendation}")
    else:
        lines.append("(none)")

    return "\n".join(lines)


def cmd_run(args):
    """Run the activity monitor."""
    config = DeploymentConfig.load()
    _apply_runtime_env_overrides(args)
    
    if args.service:
        run_as_service()
    else:
        run_standalone(config)


def cmd_diagnostics(args):
    """Print runtime startup diagnostics as JSON."""
    config = DeploymentConfig.load()
    _apply_runtime_env_overrides(args)

    orchestrator = _build_runtime_orchestrator(config)
    diagnostics = orchestrator.collect_diagnostics()
    if args.format == "text":
        print(_render_diagnostics_text(diagnostics))
    else:
        print(json.dumps(diagnostics, indent=2, sort_keys=True))

    if args.require_ready and not diagnostics.get("readiness", {}).get("overall_ready", False):
        return 2
    return 0


def cmd_config(args):
    """Show or edit configuration."""
    config = DeploymentConfig.load()
    
    if args.show:
        import json
        from dataclasses import asdict
        print(json.dumps({
            'machine_name': config.machine_name,
            'user_name': config.user_name,
            'email': asdict(config.email),
            'reporting': asdict(config.reporting),
            'storage': asdict(config.storage),
            'monitoring': asdict(config.monitoring)
        }, indent=2))
    
    elif args.set:
        # Parse key=value pairs
        for item in args.set:
            if '=' in item:
                key, value = item.split('=', 1)
                parts = key.split('.')
                
                # Navigate to the right config section
                obj = config
                for part in parts[:-1]:
                    obj = getattr(obj, part)
                
                # Set the value
                attr_name = parts[-1]
                current_value = getattr(obj, attr_name)
                
                # Convert value to appropriate type
                if isinstance(current_value, bool):
                    value = value.lower() in ('true', '1', 'yes')
                elif isinstance(current_value, int):
                    value = int(value)
                elif isinstance(current_value, float):
                    value = float(value)
                elif isinstance(current_value, list):
                    value = value.split(',')
                
                setattr(obj, attr_name, value)
        
        config.save()
        print("Configuration updated")


def cmd_test_email(args):
    """Test email configuration."""
    config = DeploymentConfig.load()
    reporter = EmailReporter(config)
    
    success, message = reporter.test_email_connection()
    print(message)
    return 0 if success else 1


def cmd_report(args):
    """Generate and send a report."""
    config = DeploymentConfig.load()
    reporter = EmailReporter(config)
    
    db_path = config.storage.get_data_directory() / 'usage.db'
    
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1
    
    if args.type == 'hourly':
        success = reporter.send_hourly_report(db_path)
    else:
        success = reporter.send_daily_report(db_path, args.date)
    
    if success:
        print("Report sent successfully")
        return 0
    else:
        print("Failed to send report")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Focus Guard Activity Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run the activity monitor')
    run_parser.add_argument('--service', action='store_true', help='Run as Windows service')
    run_parser.add_argument(
        '--strict-runtime-startup',
        action='store_true',
        help='Fail startup if tab server/admin gateway runtime dependencies cannot be started',
    )
    run_parser.add_argument(
        '--no-admin-gateway',
        action='store_true',
        help='Do not auto-start admin gateway from this process',
    )
    run_parser.add_argument(
        '--admin-gateway-host',
        default=None,
        help='Admin gateway host override for managed startup (default: 127.0.0.1)',
    )
    run_parser.add_argument(
        '--admin-gateway-port',
        type=int,
        default=None,
        help='Admin gateway port override for managed startup (default: 58393)',
    )
    run_parser.set_defaults(func=cmd_run)

    # Diagnostics command
    diagnostics_parser = subparsers.add_parser(
        'diagnostics',
        help='Print runtime startup diagnostics (tab server/admin gateway/ports/readiness)',
    )
    diagnostics_parser.add_argument(
        '--require-ready',
        action='store_true',
        help='Return non-zero exit code when overall runtime readiness is false',
    )
    diagnostics_parser.add_argument(
        '--format',
        choices=['json', 'text'],
        default='json',
        help='Output format for diagnostics report',
    )
    diagnostics_parser.add_argument(
        '--strict-runtime-startup',
        action='store_true',
        help='Set strict mode env flag in diagnostics context',
    )
    diagnostics_parser.add_argument(
        '--no-admin-gateway',
        action='store_true',
        help='Disable managed admin-gateway startup in diagnostics context',
    )
    diagnostics_parser.add_argument(
        '--admin-gateway-host',
        default=None,
        help='Admin gateway host override in diagnostics context (default: 127.0.0.1)',
    )
    diagnostics_parser.add_argument(
        '--admin-gateway-port',
        type=int,
        default=None,
        help='Admin gateway port override in diagnostics context (default: 58393)',
    )
    diagnostics_parser.set_defaults(func=cmd_diagnostics)
    
    # Config command
    config_parser = subparsers.add_parser('config', help='View or edit configuration')
    config_parser.add_argument('--show', action='store_true', help='Show current configuration')
    config_parser.add_argument('--set', nargs='+', metavar='KEY=VALUE', 
                               help='Set configuration values')
    config_parser.set_defaults(func=cmd_config)
    
    # Test email command
    test_parser = subparsers.add_parser('test-email', help='Test email configuration')
    test_parser.set_defaults(func=cmd_test_email)
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate and send a report')
    report_parser.add_argument('--type', choices=['hourly', 'daily'], default='daily',
                               help='Report type')
    report_parser.add_argument('--date', help='Date for daily report (YYYY-MM-DD)')
    report_parser.set_defaults(func=cmd_report)
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    if args.command is None:
        # Default: run standalone
        config = DeploymentConfig.load()
        run_standalone(config)
    else:
        return args.func(args)


if __name__ == '__main__':
    sys.exit(main() or 0)
