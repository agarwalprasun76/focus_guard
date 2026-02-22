"""Unified analytics service for Focus Guard.

Consolidates data from all logging components (AuditLogger, ActivityLogger,
SearchLogger, DomainUsageTracker) into a single API for dashboards and reports.

This provides immediate value to users by surfacing actionable insights.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DailyInsights:
    """Daily usage insights for the user."""
    date: str
    
    # Time metrics
    total_active_time_seconds: float = 0.0
    educational_time_seconds: float = 0.0
    distraction_time_seconds: float = 0.0
    
    # Blocking metrics
    sites_blocked: int = 0
    overrides_used: int = 0
    overrides_remaining: int = 0
    
    # Focus metrics
    focus_score: int = 100  # 0-100
    focus_streak_days: int = 0
    
    # Top domains
    top_educational_domains: List[Dict[str, Any]] = field(default_factory=list)
    top_distraction_domains: List[Dict[str, Any]] = field(default_factory=list)
    
    # Trends
    vs_yesterday: Dict[str, float] = field(default_factory=dict)
    vs_week_avg: Dict[str, float] = field(default_factory=dict)
    
    # Alerts
    alerts: List[Dict[str, str]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "time_metrics": {
                "total_active_seconds": self.total_active_time_seconds,
                "total_active_minutes": round(self.total_active_time_seconds / 60, 1),
                "educational_seconds": self.educational_time_seconds,
                "educational_minutes": round(self.educational_time_seconds / 60, 1),
                "distraction_seconds": self.distraction_time_seconds,
                "distraction_minutes": round(self.distraction_time_seconds / 60, 1),
                "educational_percentage": (
                    round(self.educational_time_seconds / self.total_active_time_seconds * 100, 1)
                    if self.total_active_time_seconds > 0 else 0
                ),
            },
            "blocking_metrics": {
                "sites_blocked": self.sites_blocked,
                "overrides_used": self.overrides_used,
                "overrides_remaining": self.overrides_remaining,
            },
            "focus_metrics": {
                "focus_score": self.focus_score,
                "focus_streak_days": self.focus_streak_days,
            },
            "top_domains": {
                "educational": self.top_educational_domains,
                "distraction": self.top_distraction_domains,
            },
            "trends": {
                "vs_yesterday": self.vs_yesterday,
                "vs_week_avg": self.vs_week_avg,
            },
            "alerts": self.alerts,
        }


class AnalyticsService:
    """Unified analytics service aggregating all logging data."""
    
    def __init__(self):
        self._audit_logger = None
        self._activity_logger = None
        self._search_logger = None
        self._domain_tracker = None
        self._master_budget = None
    
    def _get_audit_logger(self):
        if self._audit_logger is None:
            try:
                from .audit_logger import get_audit_logger
                self._audit_logger = get_audit_logger()
            except Exception as e:
                logger.debug("Could not load audit logger: %s", e)
        return self._audit_logger
    
    def _get_activity_logger(self):
        if self._activity_logger is None:
            try:
                from .activity_logger import get_activity_logger
                self._activity_logger = get_activity_logger()
            except Exception as e:
                logger.debug("Could not load activity logger: %s", e)
        return self._activity_logger
    
    def _get_search_logger(self):
        if self._search_logger is None:
            try:
                from .search_logger import get_search_logger
                self._search_logger = get_search_logger()
            except Exception as e:
                logger.debug("Could not load search logger: %s", e)
        return self._search_logger
    
    def _get_domain_tracker(self):
        if self._domain_tracker is None:
            try:
                from .domain_usage_tracker import get_domain_usage_tracker
                self._domain_tracker = get_domain_usage_tracker()
            except Exception as e:
                logger.debug("Could not load domain tracker: %s", e)
        return self._domain_tracker
    
    def _get_master_budget(self):
        if self._master_budget is None:
            try:
                from .domain_usage_tracker import get_master_distraction_budget
                self._master_budget = get_master_distraction_budget()
            except Exception as e:
                logger.debug("Could not load master budget: %s", e)
        return self._master_budget
    
    def get_daily_insights(self, date_str: Optional[str] = None) -> DailyInsights:
        """Get consolidated daily insights.
        
        Args:
            date_str: Date in YYYY-MM-DD format (defaults to today)
            
        Returns:
            DailyInsights with aggregated data from all sources
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        insights = DailyInsights(date=date_str)
        
        # Get domain usage data
        tracker = self._get_domain_tracker()
        if tracker:
            try:
                summary = tracker.get_daily_summary()
                insights.total_active_time_seconds = summary.get("total_active_seconds", 0)
                
                # Calculate educational vs distraction time
                by_category = summary.get("by_category", {})
                for cat, data in by_category.items():
                    cat_upper = cat.upper()
                    if cat_upper in ("EDUCATION", "PRODUCTIVITY", "TECHNOLOGY"):
                        insights.educational_time_seconds += data.get("active_seconds", 0)
                    elif cat_upper in ("ENTERTAINMENT", "GAMING", "SOCIAL_MEDIA", "ADULT"):
                        insights.distraction_time_seconds += data.get("active_seconds", 0)
                
                # Top domains
                top_domains = summary.get("top_domains", [])
                for dom in top_domains[:5]:
                    cat = dom.get("category", "UNKNOWN").upper()
                    entry = {
                        "domain": dom.get("domain", ""),
                        "minutes": round(dom.get("active_seconds", 0) / 60, 1),
                        "category": cat,
                    }
                    if cat in ("EDUCATION", "PRODUCTIVITY", "TECHNOLOGY"):
                        insights.top_educational_domains.append(entry)
                    elif cat in ("ENTERTAINMENT", "GAMING", "SOCIAL_MEDIA"):
                        insights.top_distraction_domains.append(entry)
            except Exception as e:
                logger.debug("Could not get domain usage: %s", e)
        
        # Get blocking/override data from audit logger
        audit = self._get_audit_logger()
        if audit:
            try:
                summary = audit.get_daily_summary(date_str)
                insights.overrides_used = summary.get("overrides_granted", 0)
                insights.sites_blocked = summary.get("overrides_denied", 0) + insights.overrides_used
            except Exception as e:
                logger.debug("Could not get audit data: %s", e)
        
        # Get master budget remaining
        budget = self._get_master_budget()
        if budget:
            try:
                status = budget.get_status()
                insights.overrides_remaining = status.get("overrides_remaining", 0)
            except Exception as e:
                logger.debug("Could not get budget status: %s", e)
        
        # Calculate focus score
        insights.focus_score = self._calculate_focus_score(insights)
        
        # Calculate streak
        insights.focus_streak_days = self._calculate_streak()
        
        # Generate alerts
        insights.alerts = self._generate_alerts(insights)
        
        return insights
    
    def _calculate_focus_score(self, insights: DailyInsights) -> int:
        """Calculate focus score (0-100) based on today's activity.
        
        Scoring factors:
        - Educational time ratio (40 points)
        - Low distraction time (30 points)
        - Few overrides used (20 points)
        - Blocked attempts (10 points)
        """
        score = 100
        
        total = insights.total_active_time_seconds
        if total > 0:
            # Educational ratio (40 points)
            edu_ratio = insights.educational_time_seconds / total
            edu_score = min(40, int(edu_ratio * 50))  # 80%+ edu = 40 points
            
            # Distraction penalty (30 points)
            dist_ratio = insights.distraction_time_seconds / total
            dist_penalty = min(30, int(dist_ratio * 60))  # 50%+ dist = -30 points
            
            score = 70 + edu_score - dist_penalty
        
        # Override penalty (20 points)
        if insights.overrides_used > 5:
            score -= min(20, (insights.overrides_used - 5) * 4)
        
        # Blocked attempts bonus (10 points) - resisting temptation is good
        if insights.sites_blocked > 0 and insights.overrides_used < 3:
            score += min(10, insights.sites_blocked * 2)
        
        return max(0, min(100, score))
    
    def _calculate_streak(self) -> int:
        """Calculate consecutive days with focus score >= 70."""
        streak = 0
        today = datetime.now().date()
        
        for days_ago in range(30):  # Check up to 30 days
            check_date = today - timedelta(days=days_ago)
            date_str = check_date.strftime("%Y-%m-%d")
            
            # Get that day's data
            audit = self._get_audit_logger()
            if audit:
                try:
                    summary = audit.get_daily_summary(date_str)
                    if summary.get("no_data"):
                        if days_ago == 0:
                            continue  # Today might not have data yet
                        break
                    
                    # Simple heuristic: good day if more denials than grants
                    granted = summary.get("overrides_granted", 0)
                    denied = summary.get("overrides_denied", 0)
                    
                    if granted <= 3 or denied > granted:
                        streak += 1
                    else:
                        break
                except Exception:
                    break
            else:
                break
        
        return streak
    
    def _generate_alerts(self, insights: DailyInsights) -> List[Dict[str, str]]:
        """Generate actionable alerts based on insights."""
        alerts = []
        
        # High distraction time
        if insights.distraction_time_seconds > 3600:  # > 1 hour
            alerts.append({
                "type": "warning",
                "title": "High distraction time",
                "message": f"You've spent {round(insights.distraction_time_seconds / 60)} minutes on distracting sites today.",
            })
        
        # Many overrides
        if insights.overrides_used >= 5:
            alerts.append({
                "type": "warning",
                "title": "Frequent overrides",
                "message": f"You've used {insights.overrides_used} overrides today. Consider taking a break.",
            })
        
        # Low educational time
        total = insights.total_active_time_seconds
        if total > 1800 and insights.educational_time_seconds < total * 0.3:
            alerts.append({
                "type": "info",
                "title": "Low educational content",
                "message": "Less than 30% of your browsing was educational today.",
            })
        
        # Great focus
        if insights.focus_score >= 90:
            alerts.append({
                "type": "success",
                "title": "Excellent focus!",
                "message": f"Your focus score is {insights.focus_score}. Keep up the great work!",
            })
        
        # Streak milestone
        if insights.focus_streak_days in (3, 7, 14, 30):
            alerts.append({
                "type": "success",
                "title": f"{insights.focus_streak_days}-day streak!",
                "message": f"You've maintained good focus for {insights.focus_streak_days} days in a row!",
            })
        
        return alerts
    
    def get_weekly_summary(self) -> Dict[str, Any]:
        """Get weekly summary with trends."""
        today = datetime.now().date()
        daily_data = []
        
        for days_ago in range(7):
            check_date = today - timedelta(days=days_ago)
            date_str = check_date.strftime("%Y-%m-%d")
            insights = self.get_daily_insights(date_str)
            daily_data.append(insights.to_dict())
        
        # Calculate averages
        total_edu = sum(d["time_metrics"]["educational_seconds"] for d in daily_data)
        total_dist = sum(d["time_metrics"]["distraction_seconds"] for d in daily_data)
        total_blocks = sum(d["blocking_metrics"]["sites_blocked"] for d in daily_data)
        avg_score = sum(d["focus_metrics"]["focus_score"] for d in daily_data) / 7
        
        return {
            "period": f"{(today - timedelta(days=6)).isoformat()} to {today.isoformat()}",
            "daily_data": list(reversed(daily_data)),  # Oldest first
            "totals": {
                "educational_minutes": round(total_edu / 60, 1),
                "distraction_minutes": round(total_dist / 60, 1),
                "sites_blocked": total_blocks,
            },
            "averages": {
                "focus_score": round(avg_score, 1),
                "educational_minutes_per_day": round(total_edu / 60 / 7, 1),
                "distraction_minutes_per_day": round(total_dist / 60 / 7, 1),
            },
        }
    
    def get_usage_heatmap(self, days: int = 7) -> Dict[str, Any]:
        """Get hourly usage heatmap for visualization."""
        activity = self._get_activity_logger()
        if not activity:
            return {"error": "Activity logger not available"}
        
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        try:
            entries = activity.get_recent_activity(limit=10000, since=since)
            
            # Build hourly counts
            hourly_counts = {h: {"total": 0, "distracting": 0, "blocked": 0} for h in range(24)}
            
            for entry in entries:
                try:
                    ts = datetime.fromisoformat(entry.timestamp)
                    hour = ts.hour
                    hourly_counts[hour]["total"] += 1
                    if entry.is_distracting:
                        hourly_counts[hour]["distracting"] += 1
                    if entry.is_blocked:
                        hourly_counts[hour]["blocked"] += 1
                except Exception:
                    pass
            
            return {
                "period_days": days,
                "hourly_data": [
                    {
                        "hour": h,
                        "total": hourly_counts[h]["total"],
                        "distracting": hourly_counts[h]["distracting"],
                        "blocked": hourly_counts[h]["blocked"],
                    }
                    for h in range(24)
                ],
            }
        except Exception as e:
            logger.error("Failed to build heatmap: %s", e)
            return {"error": str(e)}


# Singleton
_analytics_service: Optional[AnalyticsService] = None


def get_analytics_service() -> AnalyticsService:
    """Get the singleton AnalyticsService instance."""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    return _analytics_service
