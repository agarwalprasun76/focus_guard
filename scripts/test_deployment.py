#!/usr/bin/env python
"""
Focus Guard Deployment - Local Testing Script

This script allows you to test the deployment service locally without
installing it as a Windows service. Perfect for verifying functionality
before deploying to another machine.

Usage:
    python scripts/test_deployment.py                    # Run with defaults
    python scripts/test_deployment.py --test-email      # Test email config
    python scripts/test_deployment.py --show-config     # Show current config
    python scripts/test_deployment.py --monitor         # Run activity monitor
    python scripts/test_deployment.py --report          # Generate test report
    python scripts/test_deployment.py --stats           # Show resource stats
"""

import sys
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from focus_guard.deployment.config import DeploymentConfig, create_default_config
from focus_guard.deployment.email_reporter import EmailReporter
from focus_guard.deployment.service import ActivityMonitorService
from focus_guard.deployment.lightweight import ResourceLimits, RESOURCE_GUIDELINES
from focus_guard.deployment.hardening import get_hardening_status, SECURITY_RECOMMENDATIONS


def setup_logging(verbose: bool = False):
    """Configure logging for testing."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )


def show_config(config: DeploymentConfig):
    """Display current configuration."""
    print("\n" + "="*60)
    print("  CURRENT CONFIGURATION")
    print("="*60)
    
    print(f"\n  Machine: {config.machine_name}")
    print(f"  User: {config.user_name or '(not set)'}")
    
    print("\n  Email Settings:")
    print(f"    Enabled: {config.email.enabled}")
    print(f"    SMTP Server: {config.email.smtp_server}:{config.email.smtp_port}")
    print(f"    Username: {config.email.smtp_username or '(not set)'}")
    print(f"    Password: {'***' if config.email.smtp_password else '(not set)'}")
    print(f"    Recipients: {', '.join(config.email.recipients) or '(none)'}")
    
    print("\n  Reporting Settings:")
    print(f"    Hourly reports: {config.reporting.hourly_report}")
    print(f"    Daily reports: {config.reporting.daily_report}")
    print(f"    Frequency: {config.reporting.report_frequency}")
    
    print("\n  Storage Settings:")
    print(f"    Data directory: {config.storage.get_data_directory()}")
    print(f"    Log retention: {config.storage.log_retention_days} days")
    
    print("\n  Monitoring Settings:")
    print(f"    Sampling interval: {config.monitoring.sampling_interval}s")
    print(f"    Pause when locked: {config.monitoring.pause_when_locked}")
    
    print("="*60 + "\n")


def configure_email_interactive(config: DeploymentConfig) -> DeploymentConfig:
    """Interactive email configuration."""
    print("\n" + "="*60)
    print("  EMAIL CONFIGURATION")
    print("="*60)
    print("\n  For Gmail, you need an App Password:")
    print("  1. Go to Google Account > Security")
    print("  2. Enable 2-Factor Authentication")
    print("  3. Go to App Passwords > Generate")
    print("  4. Use that password below (not your regular password)")
    print()
    
    config.email.smtp_username = input("  Gmail address: ").strip()
    config.email.smtp_password = input("  App password: ").strip()
    config.email.sender_email = config.email.smtp_username
    
    recipients = input("  Recipient email(s) (comma-separated): ").strip()
    config.email.recipients = [r.strip() for r in recipients.split(',') if r.strip()]
    
    config.user_name = input("  Monitored user's name: ").strip()
    
    # Save config
    config.save()
    print("\n  Configuration saved!")
    
    return config


def test_email(config: DeploymentConfig):
    """Test email configuration."""
    print("\n" + "="*60)
    print("  TESTING EMAIL CONFIGURATION")
    print("="*60)
    
    if not config.email.is_configured():
        print("\n  Email not configured. Running setup...")
        config = configure_email_interactive(config)
    
    print(f"\n  Sending test email to: {', '.join(config.email.recipients)}")
    
    reporter = EmailReporter(config)
    success, message = reporter.test_email_connection()
    
    if success:
        print(f"  ✓ {message}")
    else:
        print(f"  ✗ {message}")
    
    print("="*60 + "\n")
    return success


def run_monitor(config: DeploymentConfig, duration: int = 60):
    """Run the activity monitor for testing."""
    print("\n" + "="*60)
    print("  RUNNING ACTIVITY MONITOR (TEST MODE)")
    print("="*60)
    print(f"\n  Duration: {duration} seconds")
    print(f"  Sampling interval: {config.monitoring.sampling_interval}s")
    print(f"  Data directory: {config.storage.get_data_directory()}")
    print("\n  Press Ctrl+C to stop early\n")
    print("-"*60)
    
    service = ActivityMonitorService(config)
    
    try:
        service.start()
        
        start_time = time.time()
        while time.time() - start_time < duration:
            elapsed = int(time.time() - start_time)
            remaining = duration - elapsed
            print(f"\r  Running... {elapsed}s elapsed, {remaining}s remaining", end="", flush=True)
            time.sleep(1)
        
        print("\n" + "-"*60)
        print("  Test duration complete.")
        
    except KeyboardInterrupt:
        print("\n" + "-"*60)
        print("  Stopped by user.")
    
    finally:
        service.stop()
    
    print("="*60 + "\n")


def generate_test_report(config: DeploymentConfig):
    """Generate a test report from existing data."""
    print("\n" + "="*60)
    print("  GENERATING TEST REPORT")
    print("="*60)
    
    db_path = config.storage.get_data_directory() / 'usage.db'
    
    if not db_path.exists():
        print(f"\n  Database not found: {db_path}")
        print("  Run the monitor first to collect some data.")
        print("="*60 + "\n")
        return
    
    reporter = EmailReporter(config)
    
    # Get today's date
    today = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\n  Database: {db_path}")
    print(f"  Date: {today}")
    
    # Get stats
    stats = reporter._get_daily_stats(db_path, today)
    
    print(f"\n  Sessions: {stats['sessions_count']}")
    print(f"  Active time: {stats['total_active_time']/60:.1f} minutes")
    
    if stats['top_applications']:
        print("\n  Top Applications:")
        for i, app in enumerate(stats['top_applications'][:5], 1):
            mins = app['total_time'] / 60
            print(f"    {i}. {app['app_name']}: {mins:.1f} min")
    
    if config.email.is_configured():
        send = input("\n  Send this report via email? (y/n): ").strip().lower()
        if send == 'y':
            success = reporter.send_daily_report(db_path, today)
            if success:
                print("  ✓ Report sent!")
            else:
                print("  ✗ Failed to send report")
    
    print("="*60 + "\n")


def show_resource_stats():
    """Show current resource usage."""
    print("\n" + "="*60)
    print("  RESOURCE USAGE")
    print("="*60)
    
    try:
        import psutil
        process = psutil.Process()
        
        print(f"\n  Memory: {process.memory_info().rss / (1024*1024):.1f} MB")
        print(f"  CPU: {process.cpu_percent(interval=1):.1f}%")
        print(f"  Threads: {process.num_threads()}")
        
    except ImportError:
        print("\n  Install psutil for resource stats: pip install psutil")
    
    print(RESOURCE_GUIDELINES)


def show_hardening_status():
    """Show current hardening/protection status."""
    print("\n" + "="*60)
    print("  HARDENING STATUS")
    print("="*60)
    
    status = get_hardening_status()
    
    print(f"\n  Service installed: {'✓' if status['service_exists'] else '✗'}")
    print(f"  Service running: {'✓' if status['service_running'] else '✗'}")
    print(f"  Recovery configured: {'✓' if status['recovery_configured'] else '✗'}")
    print(f"  Backup task exists: {'✓' if status['scheduled_task_exists'] else '✗'}")
    
    print(SECURITY_RECOMMENDATIONS)


def main():
    parser = argparse.ArgumentParser(
        description="Focus Guard Deployment - Local Testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test_deployment.py --show-config
  python scripts/test_deployment.py --setup-email
  python scripts/test_deployment.py --test-email
  python scripts/test_deployment.py --monitor --duration 120
  python scripts/test_deployment.py --report
        """
    )
    
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output')
    parser.add_argument('--show-config', action='store_true',
                       help='Show current configuration')
    parser.add_argument('--setup-email', action='store_true',
                       help='Interactive email setup')
    parser.add_argument('--test-email', action='store_true',
                       help='Test email configuration')
    parser.add_argument('--monitor', action='store_true',
                       help='Run activity monitor')
    parser.add_argument('--duration', type=int, default=60,
                       help='Monitor duration in seconds (default: 60)')
    parser.add_argument('--report', action='store_true',
                       help='Generate test report')
    parser.add_argument('--stats', action='store_true',
                       help='Show resource usage stats')
    parser.add_argument('--hardening', action='store_true',
                       help='Show hardening/protection status')
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    # Load or create config
    config = DeploymentConfig.load()
    if not config.machine_name:
        config = create_default_config()
    
    # Handle commands
    if args.show_config:
        show_config(config)
    elif args.setup_email:
        configure_email_interactive(config)
    elif args.test_email:
        test_email(config)
    elif args.monitor:
        run_monitor(config, args.duration)
    elif args.report:
        generate_test_report(config)
    elif args.stats:
        show_resource_stats()
    elif args.hardening:
        show_hardening_status()
    else:
        # Default: show menu
        print("\n" + "="*60)
        print("  FOCUS GUARD DEPLOYMENT - TEST MENU")
        print("="*60)
        print("""
  Available commands:

    --show-config    Show current configuration
    --setup-email    Interactive email setup
    --test-email     Test email configuration
    --monitor        Run activity monitor (add --duration N)
    --report         Generate test report from collected data
    --stats          Show resource usage statistics
    --hardening      Show protection/hardening status

  Example workflow:

    1. python scripts/test_deployment.py --show-config
    2. python scripts/test_deployment.py --setup-email
    3. python scripts/test_deployment.py --test-email
    4. python scripts/test_deployment.py --monitor --duration 120
    5. python scripts/test_deployment.py --report
        """)
        print("="*60 + "\n")


if __name__ == '__main__':
    main()
