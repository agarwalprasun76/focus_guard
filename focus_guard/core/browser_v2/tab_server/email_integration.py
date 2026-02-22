"""Integration between domain usage tracking and the email alert system.

This module provides functions to generate domain usage reports for inclusion
in activity monitor summary emails.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def get_domain_usage_report() -> Dict[str, Any]:
    """Get domain usage report for email summary.
    
    Returns:
        Dict containing domain usage statistics formatted for email.
    """
    try:
        from .domain_usage_tracker import get_domain_usage_tracker
        tracker = get_domain_usage_tracker()
        return tracker.get_summary_for_email()
    except Exception as e:
        logger.warning("Could not get domain usage report: %s", e)
        return {"error": str(e), "domains": []}


def format_domain_usage_for_email(summary: Optional[Dict[str, Any]] = None) -> str:
    """Format domain usage data as HTML for email reports.
    
    Args:
        summary: Optional pre-fetched summary. If None, fetches fresh data.
        
    Returns:
        HTML string for inclusion in email body.
    """
    if summary is None:
        summary = get_domain_usage_report()
    
    if "error" in summary:
        return f"<p><em>Domain usage data unavailable: {summary['error']}</em></p>"
    
    if not summary.get("domains"):
        return "<p><em>No blocked domain activity recorded today.</em></p>"
    
    html_parts = [
        "<h3>Blocked Domain Activity</h3>",
        f"<p>Date: {summary.get('date', 'Unknown')}</p>",
        f"<p>Total domains visited: {summary.get('total_domains_visited', 0)}</p>",
        f"<p>Total overrides used: {summary.get('total_overrides_used', 0)}</p>",
        f"<p>Total active time: {_format_duration(summary.get('total_active_time_seconds', 0))}</p>",
        "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse;'>",
        "<tr style='background-color: #f0f0f0;'>",
        "<th>Domain</th>",
        "<th>Active Time</th>",
        "<th>Overrides</th>",
        "<th>Sessions</th>",
        "<th>Limit Used</th>",
        "</tr>",
    ]
    
    for domain_data in summary.get("domains", []):
        limit_pct = domain_data.get("limit_percentage", 0)
        # Color code based on limit usage
        if limit_pct >= 90:
            row_style = "background-color: #ffcccc;"  # Red
        elif limit_pct >= 70:
            row_style = "background-color: #fff3cd;"  # Yellow
        else:
            row_style = ""
        
        html_parts.append(f"<tr style='{row_style}'>")
        html_parts.append(f"<td>{domain_data.get('domain', 'Unknown')}</td>")
        html_parts.append(f"<td>{domain_data.get('active_time_formatted', '0s')}</td>")
        html_parts.append(f"<td>{domain_data.get('override_count', 0)}</td>")
        html_parts.append(f"<td>{domain_data.get('session_count', 0)}</td>")
        html_parts.append(f"<td>{limit_pct:.0f}%</td>")
        html_parts.append("</tr>")
    
    html_parts.append("</table>")
    
    return "\n".join(html_parts)


def format_domain_usage_for_text(summary: Optional[Dict[str, Any]] = None) -> str:
    """Format domain usage data as plain text for email reports.
    
    Args:
        summary: Optional pre-fetched summary. If None, fetches fresh data.
        
    Returns:
        Plain text string for inclusion in email body.
    """
    if summary is None:
        summary = get_domain_usage_report()
    
    if "error" in summary:
        return f"Domain usage data unavailable: {summary['error']}"
    
    if not summary.get("domains"):
        return "No blocked domain activity recorded today."
    
    lines = [
        "=== Blocked Domain Activity ===",
        f"Date: {summary.get('date', 'Unknown')}",
        f"Total domains visited: {summary.get('total_domains_visited', 0)}",
        f"Total overrides used: {summary.get('total_overrides_used', 0)}",
        f"Total active time: {_format_duration(summary.get('total_active_time_seconds', 0))}",
        "",
        "Domain                          | Active Time | Overrides | Sessions | Limit",
        "-" * 80,
    ]
    
    for domain_data in summary.get("domains", []):
        domain = domain_data.get("domain", "Unknown")[:30].ljust(30)
        active_time = domain_data.get("active_time_formatted", "0s").ljust(11)
        overrides = str(domain_data.get("override_count", 0)).ljust(9)
        sessions = str(domain_data.get("session_count", 0)).ljust(8)
        limit_pct = f"{domain_data.get('limit_percentage', 0):.0f}%"
        
        lines.append(f"{domain} | {active_time} | {overrides} | {sessions} | {limit_pct}")
    
    return "\n".join(lines)


def _format_duration(seconds: float) -> str:
    """Format seconds as human-readable duration."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def get_daily_summary_alert_info() -> Dict[str, Any]:
    """Get data for a daily summary alert.
    
    Returns:
        Dict with alert information including domain usage.
    """
    summary = get_domain_usage_report()
    
    return {
        "title": "Daily Browser Activity Summary",
        "date": summary.get("date", datetime.now().strftime("%Y-%m-%d")),
        "total_domains": summary.get("total_domains_visited", 0),
        "total_overrides": summary.get("total_overrides_used", 0),
        "total_active_time_seconds": summary.get("total_active_time_seconds", 0),
        "total_active_time_formatted": _format_duration(summary.get("total_active_time_seconds", 0)),
        "domains": summary.get("domains", []),
        "html_report": format_domain_usage_for_email(summary),
        "text_report": format_domain_usage_for_text(summary),
    }
