"""
Email reporter for sending activity summaries.

This module handles generating and sending email reports with usage summaries.
Reuses SQLiteUsageDatabase from the core activity module for data access.
"""

import smtplib
import ssl
import sqlite3
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

from focus_guard.deployment.config import DeploymentConfig, EmailConfig
from focus_guard.core.activity.enhanced_logger import SQLiteUsageDatabase

logger = logging.getLogger(__name__)


class EmailReporter:
    """
    Generates and sends email reports with activity summaries.
    """
    
    def __init__(self, config: DeploymentConfig):
        """
        Initialize the email reporter.
        
        Args:
            config: Deployment configuration
        """
        self.config = config
        self.email_config = config.email
        self.last_hourly_report: Optional[datetime] = None
        self.last_daily_report: Optional[datetime] = None
    
    def send_hourly_report(self, db_path: Path) -> bool:
        """
        Send an hourly activity report.
        
        Args:
            db_path: Path to the usage database
            
        Returns:
            True if sent successfully
        """
        if not self.email_config.enabled or not self.email_config.is_configured():
            logger.warning("Email not configured, skipping hourly report")
            return False

        try:
            # Get configured reporting window (minute-level for testability and parity
            # with schedule.hourly_interval_minutes).
            end_time = datetime.now()
            try:
                interval_minutes = max(1, int(self.config.reporting.schedule.get_hourly_interval_minutes()))
            except Exception:
                interval_minutes = max(
                    1,
                    int(getattr(self.config.reporting.schedule, 'hourly_interval_hours', 1) or 1) * 60,
                )

            start_time = end_time - timedelta(minutes=interval_minutes)

            diagnostics = self._get_recent_activity_diagnostics(db_path, interval_minutes)
            logger.info(
                "Hourly report diagnostics (%d min): sessions_in_window=%d, open_sessions=%d, "
                "visible_foreground_samples=%d, db=%s",
                interval_minutes,
                diagnostics['sessions_in_window'],
                diagnostics['open_sessions'],
                diagnostics['visible_foreground_samples'],
                db_path,
            )
            
            stats = self._get_period_stats(db_path, start_time, end_time)
            
            subject = f"[FocusGuard] Hourly Report - {self.config.machine_name} - {end_time.strftime('%H:%M')}"
            
            body = self._generate_hourly_report_html(stats, start_time, end_time)

            top_apps_5m = self._get_top_apps_summary(db_path, lookback_minutes=5, limit=3)
            logger.info("Hourly report top apps (last 5m): %s", top_apps_5m)
            
            success = self._send_email(subject, body)
            
            if success:
                self.last_hourly_report = datetime.now()
                logger.info(f"Hourly report sent to {len(self.email_config.recipients)} recipients")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send hourly report: {e}")
            return False

    def _get_recent_activity_diagnostics(self, db_path: Path, lookback_minutes: int) -> Dict[str, int]:
        """Collect compact diagnostics to identify missing report wiring quickly."""
        diagnostics = {
            'sessions_in_window': 0,
            'open_sessions': 0,
            'visible_foreground_samples': 0,
        }

        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=max(1, int(lookback_minutes or 1)))
        start_ts = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_ts = end_time.strftime('%Y-%m-%d %H:%M:%S')

        try:
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()

                diagnostics['sessions_in_window'] = int(
                    cursor.execute(
                        '''
                        SELECT COUNT(*)
                        FROM usage_sessions
                        WHERE (end_time IS NULL OR end_time > ?)
                          AND start_time < ?
                        ''',
                        (start_ts, end_ts),
                    ).fetchone()[0]
                    or 0
                )

                diagnostics['open_sessions'] = int(
                    cursor.execute(
                        "SELECT COUNT(*) FROM usage_sessions WHERE end_time IS NULL"
                    ).fetchone()[0]
                    or 0
                )

                has_visible_windows = cursor.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='visible_windows' LIMIT 1"
                ).fetchone()
                if has_visible_windows:
                    diagnostics['visible_foreground_samples'] = int(
                        cursor.execute(
                            '''
                            SELECT COUNT(*)
                            FROM visible_windows
                            WHERE is_foreground = 1
                              AND replace(substr(timestamp,1,19),'T',' ') >= ?
                              AND replace(substr(timestamp,1,19),'T',' ') < ?
                            ''',
                            (start_ts, end_ts),
                        ).fetchone()[0]
                        or 0
                    )
        except Exception as exc:
            logger.warning("Could not gather report diagnostics from usage DB %s: %s", db_path, exc)

        return diagnostics

    def _get_top_apps_summary(self, db_path: Path, lookback_minutes: int = 5, limit: int = 3) -> str:
        """Build a compact top-apps summary string for quick runtime triage logs."""
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=max(1, int(lookback_minutes or 1)))
        start_ts = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_ts = end_time.strftime('%Y-%m-%d %H:%M:%S')

        try:
            with sqlite3.connect(str(db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                has_activity_samples = cursor.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='activity_samples' LIMIT 1"
                ).fetchone()
                if has_activity_samples:
                    cursor.execute(
                        '''
                        SELECT app_name, COALESCE(SUM(sample_seconds), 0) AS total_active
                        FROM activity_samples
                        WHERE replace(substr(timestamp,1,19),'T',' ') >= ?
                          AND replace(substr(timestamp,1,19),'T',' ') < ?
                          AND is_foreground = 1
                        GROUP BY app_name
                        ORDER BY total_active DESC
                        LIMIT ?
                        ''',
                        (start_ts, end_ts, max(1, int(limit or 1))),
                    )
                    sampled_apps = [dict(row) for row in cursor.fetchall()]
                    positive_sampled = [a for a in sampled_apps if float(a.get('total_active') or 0.0) > 0.0]
                    if positive_sampled:
                        return ", ".join(
                            f"{a['app_name']}={float(a['total_active'])/60:.1f}m" for a in positive_sampled
                        )

                cursor.execute(
                    '''
                    SELECT app_name, COALESCE(SUM(active_duration), 0) AS total_active
                    FROM usage_sessions
                    WHERE (end_time IS NULL OR end_time > ?)
                      AND start_time < ?
                    GROUP BY app_name
                    ORDER BY total_active DESC
                    LIMIT ?
                    ''',
                    (start_ts, end_ts, max(1, int(limit or 1))),
                )
                top_apps = [dict(row) for row in cursor.fetchall()]

                positive_apps = [a for a in top_apps if float(a.get('total_active') or 0.0) > 0.0]
                if positive_apps:
                    return ", ".join(
                        f"{a['app_name']}={float(a['total_active'])/60:.1f}m" for a in positive_apps
                    )

                has_visible_windows = cursor.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='visible_windows' LIMIT 1"
                ).fetchone()
                if not has_visible_windows:
                    return "no_app_activity"

                sample_interval = max(1, int(getattr(self.config.monitoring, 'sampling_interval', 5) or 5))
                cursor.execute(
                    '''
                    SELECT app_name, COUNT(*) AS sample_count
                    FROM visible_windows
                    WHERE is_foreground = 1
                      AND replace(substr(timestamp,1,19),'T',' ') >= ?
                      AND replace(substr(timestamp,1,19),'T',' ') < ?
                    GROUP BY app_name
                    ORDER BY sample_count DESC
                    LIMIT ?
                    ''',
                    (start_ts, end_ts, max(1, int(limit or 1))),
                )
                fallback_apps = [dict(row) for row in cursor.fetchall()]
                if fallback_apps:
                    return ", ".join(
                        f"{a['app_name']}={float(int(a['sample_count'] or 0) * sample_interval)/60:.1f}m"
                        for a in fallback_apps
                    )
        except Exception as exc:
            logger.warning("Could not build top-apps summary from usage DB %s: %s", db_path, exc)

        return "no_app_activity"
    
    def send_daily_report(self, db_path: Path, date: Optional[str] = None) -> bool:
        """
        Send a daily activity report.
        
        Args:
            db_path: Path to the usage database
            date: Date string (YYYY-MM-DD) or None for yesterday
            
        Returns:
            True if sent successfully
        """
        if not self.email_config.enabled or not self.email_config.is_configured():
            logger.warning("Email not configured, skipping daily report")
            return False
        
        try:
            if date is None:
                report_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                report_date = date
            
            stats = self._get_daily_stats(db_path, report_date)
            
            subject = f"[FocusGuard] Daily Report - {self.config.machine_name} - {report_date}"
            
            body = self._generate_daily_report_html(stats, report_date)
            
            success = self._send_email(subject, body)
            
            if success:
                self.last_daily_report = datetime.now()
                logger.info(f"Daily report sent to {len(self.email_config.recipients)} recipients")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")
            return False
    
    def _get_period_stats(self, db_path: Path, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get statistics for a specific time period.

        Uses a three-tier data strategy:
          1. activity_samples  – per-tick samples (most accurate for arbitrary windows)
          2. usage_sessions    – completed sessions (includes open-session estimation)
          3. visible_windows   – raw foreground samples (last-resort fallback)
        """
        stats: Dict[str, Any] = {
            'sessions_count': 0,
            'total_active_time': 0.0,
            'top_applications': [],
            'top_domains': [],
            'blocked_count': 0,
            'override_count': 0,
        }

        start_ts = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_ts = end_time.strftime('%Y-%m-%d %H:%M:%S')
        now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            with sqlite3.connect(str(db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Count sessions overlapping the window — open sessions (end_time IS NULL)
                # are treated as still-running so they are never excluded.
                cursor.execute(
                    '''
                    SELECT COUNT(*) as sessions_count
                    FROM usage_sessions
                    WHERE (end_time IS NULL OR end_time > ?)
                      AND start_time < ?
                    ''',
                    (start_ts, end_ts),
                )
                stats['sessions_count'] = int(cursor.fetchone()['sessions_count'] or 0)

                # ── Tier 1: activity_samples ─────────────────────────
                # Timestamps are stored as ISO-8601 text (may include T separator
                # and/or microseconds). Use a plain text comparison which works
                # correctly because ISO-8601 strings sort lexicographically when
                # the date prefix (YYYY-MM-DD) matches. We normalise stored values
                # via substr to the first 19 characters ("YYYY-MM-DDTHH:MM:SS")
                # so the T-vs-space difference is harmless.
                has_activity_samples = cursor.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='activity_samples' LIMIT 1"
                ).fetchone()
                if has_activity_samples:
                    cursor.execute(
                        '''
                        SELECT COALESCE(SUM(sample_seconds), 0) as total_active_time,
                               COUNT(*) as sample_count
                        FROM activity_samples
                        WHERE timestamp >= ? AND timestamp < ?
                          AND is_foreground = 1
                        ''',
                        (start_ts, end_ts),
                    )

                    sample_row = cursor.fetchone()
                    sampled_active = float(sample_row['total_active_time'] or 0.0)
                    sampled_count = int(sample_row['sample_count'] or 0)

                    if sampled_active > 0.0 and sampled_count > 0:
                        stats['total_active_time'] = sampled_active
                        stats['sessions_count'] = max(int(stats['sessions_count'] or 0), 1)

                        cursor.execute(
                            '''
                            SELECT app_name, COALESCE(SUM(sample_seconds), 0) as total_time
                            FROM activity_samples
                            WHERE timestamp >= ? AND timestamp < ?
                              AND is_foreground = 1
                            GROUP BY app_name
                            ORDER BY total_time DESC
                            LIMIT ?
                            ''',
                            (start_ts, end_ts, self.config.reporting.include_top_apps),
                        )
                        stats['top_applications'] = [dict(row) for row in cursor.fetchall()]

                        cursor.execute(
                            '''
                            SELECT domain, COALESCE(SUM(sample_seconds), 0) as total_time
                            FROM activity_samples
                            WHERE timestamp >= ? AND timestamp < ?
                              AND is_foreground = 1
                              AND domain IS NOT NULL AND domain != ''
                            GROUP BY domain
                            ORDER BY total_time DESC
                            LIMIT ?
                            ''',
                            (start_ts, end_ts, self.config.reporting.include_top_domains),
                        )
                        stats['top_domains'] = [dict(row) for row in cursor.fetchall()]
                        return stats

                # ── Tier 2: usage_sessions ───────────────────────────
                # Fetch individual rows so we can estimate in-window active time
                # for open sessions (active_duration is 0 until the session closes).
                cursor.execute(
                    '''
                    SELECT app_name, domain, start_time, end_time, active_duration
                    FROM usage_sessions
                    WHERE (end_time IS NULL OR end_time > ?)
                      AND start_time < ?
                    ''',
                    (start_ts, end_ts),
                )
                session_rows = cursor.fetchall()

                total_active = 0.0
                app_times: Dict[str, float] = {}
                domain_times: Dict[str, float] = {}

                for row in session_rows:
                    stored_active = float(row['active_duration'] or 0)
                    if stored_active > 0:
                        duration = stored_active
                    else:
                        # Open session — estimate in-window active time
                        try:
                            sess_start = datetime.strptime(
                                str(row['start_time'])[:19].replace('T', ' '),
                                '%Y-%m-%d %H:%M:%S',
                            )
                        except (ValueError, TypeError):
                            sess_start = start_time
                        effective_end_str = row['end_time'] or now_ts
                        try:
                            sess_end = datetime.strptime(
                                str(effective_end_str)[:19].replace('T', ' '),
                                '%Y-%m-%d %H:%M:%S',
                            )
                        except (ValueError, TypeError):
                            sess_end = end_time
                        window_start = max(sess_start, start_time)
                        window_end = min(sess_end, end_time)
                        duration = max(0.0, (window_end - window_start).total_seconds())

                    total_active += duration

                    app = row['app_name'] or 'unknown'
                    app_times[app] = app_times.get(app, 0.0) + duration
                    dom = row['domain']
                    if dom:
                        domain_times[dom] = domain_times.get(dom, 0.0) + duration

                stats['sessions_count'] = max(stats['sessions_count'], len(session_rows))
                stats['total_active_time'] = total_active

                top_n_apps = self.config.reporting.include_top_apps
                stats['top_applications'] = [
                    {'app_name': k, 'total_time': v}
                    for k, v in sorted(app_times.items(), key=lambda x: x[1], reverse=True)[:top_n_apps]
                ]
                top_n_domains = self.config.reporting.include_top_domains
                stats['top_domains'] = [
                    {'domain': k, 'total_time': v}
                    for k, v in sorted(domain_times.items(), key=lambda x: x[1], reverse=True)[:top_n_domains]
                ]

                # ── Tier 3: visible_windows fallback ─────────────────
                if float(stats['total_active_time'] or 0.0) <= 0.0:
                    has_visible_windows = cursor.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='visible_windows' LIMIT 1"
                    ).fetchone()
                    if has_visible_windows:
                        sample_interval = max(1, int(getattr(self.config.monitoring, 'sampling_interval', 5) or 5))

                        cursor.execute(
                            '''
                            SELECT COUNT(*)
                            FROM visible_windows
                            WHERE is_foreground = 1
                              AND replace(substr(timestamp,1,19),'T',' ') >= ?
                              AND replace(substr(timestamp,1,19),'T',' ') < ?
                            ''',
                            (start_ts, end_ts),
                        )
                        foreground_samples = int(cursor.fetchone()[0] or 0)

                        if foreground_samples > 0:
                            stats['sessions_count'] = max(int(stats['sessions_count'] or 0), 1)
                            stats['total_active_time'] = float(foreground_samples * sample_interval)

                            cursor.execute(
                                '''
                                SELECT app_name, COUNT(*) as sample_count
                                FROM visible_windows
                                WHERE is_foreground = 1
                                  AND replace(substr(timestamp,1,19),'T',' ') >= ?
                                  AND replace(substr(timestamp,1,19),'T',' ') < ?
                                GROUP BY app_name
                                ORDER BY sample_count DESC
                                LIMIT ?
                                ''',
                                (start_ts, end_ts, self.config.reporting.include_top_apps),
                            )
                            stats['top_applications'] = [
                                {
                                    'app_name': row['app_name'],
                                    'total_time': float(int(row['sample_count'] or 0) * sample_interval),
                                }
                                for row in cursor.fetchall()
                            ]

                # ── Blocking and override stats ──────────────────
                try:
                    has_blocking = cursor.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='blocking_events' LIMIT 1"
                    ).fetchone()
                    if has_blocking:
                        row = cursor.execute(
                            "SELECT COUNT(*) as cnt FROM blocking_events WHERE timestamp >= ? AND timestamp <= ?",
                            (start_ts, end_ts),
                        ).fetchone()
                        stats['blocked_count'] = int(row['cnt'] or 0) if row else 0
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Error getting period stats: {e}")

        return stats
    
    def _get_daily_stats(self, db_path: Path, date: str) -> Dict[str, Any]:
        """
        Get statistics for a specific day.
        
        Reuses SQLiteUsageDatabase.get_daily_stats() for core data,
        then adds hourly breakdown if configured.
        """
        # Use existing database class for core stats (DRY)
        db = SQLiteUsageDatabase(str(db_path))
        stats = db.get_daily_stats(date)
        
        # Add hourly breakdown if configured (not in core class)
        stats['hourly_breakdown'] = []
        if self.config.reporting.include_hourly_breakdown:
            import sqlite3
            try:
                with sqlite3.connect(str(db_path)) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT 
                            strftime('%H', start_time) as hour,
                            SUM(active_duration) as active_time,
                            COUNT(*) as sessions
                        FROM usage_sessions 
                        WHERE DATE(start_time) = ?
                        GROUP BY strftime('%H', start_time)
                        ORDER BY hour
                    ''', (date,))
                    stats['hourly_breakdown'] = [dict(row) for row in cursor.fetchall()]
            except Exception as e:
                logger.error(f"Error getting hourly breakdown: {e}")
        
        return stats
    
    def _admin_urls(self) -> tuple[str, str]:
        """Return (admin dashboard URL, health/status URL) for use in email links."""
        base = "http://127.0.0.1:58393"
        return (f"{base}/admin", f"{base}/admin/status")

    def _generate_hourly_report_html(self, stats: Dict[str, Any], 
                                      start_time: datetime, end_time: datetime) -> str:
        """Generate HTML content for hourly report."""
        active_mins = stats['total_active_time'] / 60
        admin_url, status_url = self._admin_urls()
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; color: #2c3e50; }}
                h1 {{ color: #2c3e50; }}
                h2 {{ color: #34495e; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #3498db; color: white; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .summary {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .metric {{ font-size: 24px; font-weight: bold; color: #2980b9; }}
                .alert {{ background-color: #fef3cd; border: 1px solid #ffc107; padding: 12px; border-radius: 5px; margin: 10px 0; }}
                .footer {{ color: #7f8c8d; font-size: 12px; margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px; }}
                .dashboard-link {{ display: inline-block; background-color: #3498db; color: white; padding: 8px 16px; border-radius: 5px; text-decoration: none; font-weight: bold; margin: 5px 0; }}
            </style>
        </head>
        <body>
            <h1>🖥️ FocusGuard Hourly Report</h1>
            
            <div class="summary">
                <p><strong>Machine:</strong> {self.config.machine_name}</p>
                <p><strong>User:</strong> {self.config.user_name or 'Not specified'}</p>
                <p><strong>Period:</strong> {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%H:%M')}</p>
            </div>
            
            <h2>📊 Summary</h2>
            <div class="summary">
                <p>Active Time: <span class="metric">{active_mins:.1f} minutes</span></p>
                <p>Sessions: <span class="metric">{stats['sessions_count']}</span></p>
            </div>
        """
        
        if active_mins <= 0:
            html += f"""
            <div class="alert">
                <strong>⚠️ No activity detected.</strong> If you believe this is incorrect, check FocusGuard status at <a href="{status_url}" style="color: #856404;">{status_url}</a>
            </div>
            """
        
        if stats['top_applications']:
            html += """
            <h2>📱 Top Applications</h2>
            <table>
                <tr><th>#</th><th>Application</th><th>Time (min)</th></tr>
            """
            for i, app in enumerate(stats['top_applications'], 1):
                display_name = app['app_name']
                if display_name.lower().endswith('.exe'):
                    display_name = display_name[:-4]
                mins = app['total_time'] / 60
                html += f"<tr><td>{i}</td><td>{display_name}</td><td>{mins:.1f}</td></tr>"
            html += "</table>"
        
        if stats['top_domains']:
            html += """
            <h2>🌐 Top Domains</h2>
            <table>
                <tr><th>#</th><th>Domain</th><th>Time (min)</th></tr>
            """
            for i, domain in enumerate(stats['top_domains'], 1):
                mins = domain['total_time'] / 60
                html += f"<tr><td>{i}</td><td>{domain['domain']}</td><td>{mins:.1f}</td></tr>"
            html += "</table>"

        blocked_count = stats.get('blocked_count', 0)
        override_count = stats.get('override_count', 0)
        if blocked_count > 0 or override_count > 0:
            html += "<h2>🛡️ Blocking Activity</h2><div class='summary'>"
            if blocked_count > 0:
                html += f"<p>Sites blocked: <strong>{blocked_count}</strong></p>"
            if override_count > 0:
                html += f"<p>Overrides used: <strong>{override_count}</strong></p>"
            html += "</div>"
        
        html += f"""
            <div class="footer">
                <p><a class="dashboard-link" href="{admin_url}">Open FocusGuard Dashboard</a></p>
                <p>Open your FocusGuard dashboard to see detailed activity.</p>
                <p>View detailed activity, manage rules, and adjust time budgets from the dashboard.</p>
                <p>This report was automatically generated by FocusGuard Activity Monitor.</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _generate_daily_report_html(self, stats: Dict[str, Any], date: str) -> str:
        """Generate HTML content for daily report."""
        active_hours = stats['total_active_time'] / 3600
        active_mins = stats['total_active_time'] / 60
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #2c3e50; }}
                h2 {{ color: #34495e; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #3498db; color: white; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .summary {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .metric {{ font-size: 24px; font-weight: bold; color: #2980b9; }}
                .bar {{ background-color: #3498db; height: 20px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <h1>📅 FocusGuard Daily Report</h1>
            
            <div class="summary">
                <p><strong>Machine:</strong> {self.config.machine_name}</p>
                <p><strong>User:</strong> {self.config.user_name or 'Not specified'}</p>
                <p><strong>Date:</strong> {date}</p>
            </div>
            
            <h2>📊 Daily Summary</h2>
            <div class="summary">
                <p>Total Active Time: <span class="metric">{active_hours:.2f} hours ({active_mins:.0f} min)</span></p>
                <p>Total Monitored Time: <span class="metric">{stats.get('total_monitored_time', 0)/3600:.2f} hours ({stats.get('total_monitored_time', 0)/60:.0f} min)</span></p>
                <p>Idle Time: <span class="metric">{stats.get('total_idle_time', 0)/60:.0f} min</span></p>
                <p>Total Sessions: <span class="metric">{stats['sessions_count']}</span></p>
            </div>
        """
        
        # Build comprehensive app view combining active time and visibility
        html += self._build_comprehensive_apps_table(stats)
        
        if stats['top_domains']:
            html += """
            <h2>🌐 Top Domains</h2>
            <table>
                <tr><th>#</th><th>Domain</th><th>Time</th><th>%</th></tr>
            """
            total_time = stats['total_active_time'] or 1
            for i, domain in enumerate(stats['top_domains'], 1):
                mins = domain['total_time'] / 60
                pct = (domain['total_time'] / total_time) * 100
                html += f"<tr><td>{i}</td><td>{domain['domain']}</td><td>{mins:.1f} min</td><td>{pct:.1f}%</td></tr>"
            html += "</table>"
        
        if stats.get('hourly_breakdown'):
            html += """
            <h2>⏰ Hourly Breakdown</h2>
            <table>
                <tr><th>Hour</th><th>Active Time</th><th>Sessions</th></tr>
            """
            for hour_data in stats['hourly_breakdown']:
                hour = int(hour_data['hour'])
                mins = hour_data['active_time'] / 60
                html += f"<tr><td>{hour:02d}:00</td><td>{mins:.1f} min</td><td>{hour_data['sessions']}</td></tr>"
            html += "</table>"
        
        admin_url, status_url = self._admin_urls()
        if float(stats.get('total_active_time', 0)) <= 0:
            html += f"""
            <div style="background-color: #fef3cd; border: 1px solid #ffc107; padding: 12px; border-radius: 5px; margin: 10px 0;">
                <strong>⚠️ No activity detected.</strong> If you believe this is incorrect, check FocusGuard status at <a href="{status_url}" style="color: #856404;">{status_url}</a>
            </div>
            """
        
        html += f"""
            <div style="color: #7f8c8d; font-size: 12px; margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px;">
                <p><a href="{admin_url}" style="display: inline-block; background-color: #3498db; color: white; padding: 8px 16px; border-radius: 5px; text-decoration: none; font-weight: bold;">Open FocusGuard Dashboard</a></p>
                <p>Open your FocusGuard dashboard to see detailed activity.</p>
                <p>View detailed activity, manage rules, and adjust time budgets from the dashboard.</p>
                <p>This report was automatically generated by FocusGuard Activity Monitor.</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    # System apps to filter out from reports (not useful for monitoring)
    SYSTEM_APPS_FILTER = {
        'applicationframehost.exe', 'systemsettings.exe', 'easysettingbox.exe',
        'textinputhost.exe', 'shellexperiencehost.exe', 'searchhost.exe',
        'startmenuexperiencehost.exe', 'runtimebroker.exe', 'dwm.exe',
        'taskhostw.exe', 'sihost.exe', 'ctfmon.exe', 'explorer.exe',
        'searchui.exe', 'lockapp.exe', 'fontdrvhost.exe', 'winlogon.exe',
        'csrss.exe', 'smss.exe', 'services.exe', 'lsass.exe', 'svchost.exe',
        'mc-webview-cnt.exe', 'widgets.exe', 'gamebar.exe', 'gamebarftserver.exe'
    }
    
    def _build_comprehensive_apps_table(self, stats: Dict[str, Any]) -> str:
        """
        Build a single comprehensive applications table combining active time and visibility data.
        Filters out system apps that don't add value to the report.
        """
        # Merge data from top_applications (active time) and visible_applications (screen presence)
        apps_data = {}
        
        # Add active time data
        for app in stats.get('top_applications', []):
            app_name = app['app_name']
            if app_name.lower() in self.SYSTEM_APPS_FILTER:
                continue
            apps_data[app_name] = {
                'app_name': app_name,
                'active_time': app.get('total_time', 0),
                'times_seen': 0,
                'foreground_pct': 0,
                'screen_pct': 0
            }
        
        # Merge visibility data
        for app in stats.get('visible_applications', []):
            app_name = app['app_name']
            if app_name.lower() in self.SYSTEM_APPS_FILTER:
                continue
            
            fg_pct = (app['foreground_count'] / app['sample_count'] * 100) if app['sample_count'] > 0 else 0
            screen_pct = app.get('avg_screen_percent') or 0
            
            if app_name in apps_data:
                apps_data[app_name]['times_seen'] = app['sample_count']
                apps_data[app_name]['foreground_pct'] = fg_pct
                apps_data[app_name]['screen_pct'] = screen_pct
            else:
                apps_data[app_name] = {
                    'app_name': app_name,
                    'active_time': 0,
                    'times_seen': app['sample_count'],
                    'foreground_pct': fg_pct,
                    'screen_pct': screen_pct
                }
        
        if not apps_data:
            return ""
        
        # Sort by active time first, then by times_seen
        sorted_apps = sorted(apps_data.values(), 
                            key=lambda x: (x['active_time'], x['times_seen']), 
                            reverse=True)
        
        total_time = stats['total_active_time'] or 1
        
        html = """
            <h2>📱 Application Usage</h2>
            <p style="color: #7f8c8d; font-size: 12px;">Combined view: active time + screen presence (background apps like videos)</p>
            <table>
                <tr>
                    <th>#</th>
                    <th>Application</th>
                    <th>Active Time</th>
                    <th>% of Active</th>
                    <th>On Screen</th>
                    <th>Foreground %</th>
                </tr>
        """
        
        for i, app in enumerate(sorted_apps[:15], 1):
            mins = app['active_time'] / 60
            pct = (app['active_time'] / total_time) * 100 if app['active_time'] > 0 else 0
            times_seen = app['times_seen']
            fg_pct = app['foreground_pct']
            
            # Format the display name (remove .exe suffix for cleaner look)
            display_name = app['app_name']
            if display_name.lower().endswith('.exe'):
                display_name = display_name[:-4]
            
            # Show active time or "background only" indicator
            if app['active_time'] > 0:
                time_str = f"{mins:.1f} min"
                pct_str = f"{pct:.1f}%"
            else:
                time_str = "<em>background</em>"
                pct_str = "-"
            
            html += f"""
                <tr>
                    <td>{i}</td>
                    <td>{display_name}</td>
                    <td>{time_str}</td>
                    <td>{pct_str}</td>
                    <td>{times_seen}x</td>
                    <td>{fg_pct:.0f}%</td>
                </tr>
            """
        
        html += "</table>"
        return html
    
    def _send_email(self, subject: str, html_body: str) -> bool:
        """
        Send an email with the given subject and HTML body.
        
        Args:
            subject: Email subject
            html_body: HTML content for email body
            
        Returns:
            True if sent successfully
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.email_config.sender_name} <{self.email_config.sender_email}>"
            msg['To'] = ", ".join(self.email_config.recipients)
            msg['Subject'] = subject
            
            # Create plain text version
            plain_text = "Please view this email in an HTML-capable email client."
            
            msg.attach(MIMEText(plain_text, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Connect and send
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.email_config.smtp_server, self.email_config.smtp_port) as server:
                if self.email_config.use_tls:
                    server.starttls(context=context)
                server.login(self.email_config.smtp_username, self.email_config.smtp_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def test_email_connection(self) -> tuple[bool, str]:
        """
        Test the email configuration by sending a test email.
        
        Returns:
            Tuple of (success, message)
        """
        if not self.email_config.is_configured():
            return False, "Email not properly configured"
        
        try:
            subject = f"[FocusGuard] Test Email - {self.config.machine_name}"
            body = f"""
            <html>
            <body>
                <h1>FocusGuard Email Test</h1>
                <p>This is a test email from FocusGuard Activity Monitor.</p>
                <p><strong>Machine:</strong> {self.config.machine_name}</p>
                <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>If you received this email, your email configuration is working correctly!</p>
            </body>
            </html>
            """
            
            success = self._send_email(subject, body)
            
            if success:
                return True, f"Test email sent to {', '.join(self.email_config.recipients)}"
            else:
                return False, "Failed to send test email"
                
        except Exception as e:
            return False, f"Error: {str(e)}"
