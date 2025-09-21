"""
Alerting system for change detection notifications.

This module provides:
- Log-based alerting for significant changes
- Rate limiting and cooldown mechanisms
- Alert severity filtering
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import structlog

from scheduler.models import AlertConfig, ChangeLog, ChangeSeverity, ChangeType

logger = structlog.get_logger(__name__)


class AlertManager:
    """Manager for handling alerts and notifications."""
    
    def __init__(self, alert_config: AlertConfig):
        """
        Initialize alert manager.
        
        Args:
            alert_config: Alert configuration
        """
        self.config = alert_config
        self.logger = logger.bind(component="alert_manager")
        self.alert_history = {}  # Track alert history for rate limiting
        self.last_alert_times = {}  # Track last alert times for cooldown
    
    async def process_changes(self, changes: List[ChangeLog]) -> None:
        """
        Process a list of changes and send appropriate alerts.
        
        Args:
            changes: List of detected changes
        """
        if not self.config.enabled:
            self.logger.debug("Alerting is disabled")
            return
        
        try:
            # Filter changes by severity for logging
            log_changes = self._filter_changes_by_severity(
                changes, self.config.min_severity_for_log
            )
            
            # Send log alerts
            if self.config.log_enabled and log_changes:
                await self._send_log_alert(log_changes)
            
            self.logger.info(
                "Processed change alerts",
                total_changes=len(changes),
                log_changes=len(log_changes)
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to process change alerts",
                error=str(e)
            )
    
    def _filter_changes_by_severity(
        self, 
        changes: List[ChangeLog], 
        min_severity: ChangeSeverity
    ) -> List[ChangeLog]:
        """Filter changes by minimum severity level."""
        severity_order = {
            ChangeSeverity.LOW: 1,
            ChangeSeverity.MEDIUM: 2,
            ChangeSeverity.HIGH: 3,
            ChangeSeverity.CRITICAL: 4
        }
        
        min_level = severity_order.get(min_severity, 1)
        
        filtered_changes = []
        for change in changes:
            change_level = severity_order.get(change.severity, 1)
            if change_level >= min_level:
                filtered_changes.append(change)
        
        return filtered_changes
    
    
    async def _send_log_alert(self, changes: List[ChangeLog]) -> None:
        """Send log alert for changes."""
        try:
            # Check rate limiting
            if not self._check_rate_limit("log"):
                self.logger.warning("Log alert rate limited")
                return
            
            # Create log content
            log_message = self._create_log_content(changes)
            
            # Log the alert
            self.logger.warning(
                "Change detection alert",
                message=log_message,
                changes_count=len(changes)
            )
            
            # Update alert history
            self._update_alert_history("log")
            
        except Exception as e:
            self.logger.error(
                "Failed to send log alert",
                error=str(e)
            )
    
    
    def _create_log_content(self, changes: List[ChangeLog]) -> str:
        """Create log message content."""
        changes_summary = []
        
        for change in changes:
            changes_summary.append(
                f"{change.change_type.value}: {change.change_summary} "
                f"(Severity: {change.severity.value})"
            )
        
        return f"Detected {len(changes)} changes: " + "; ".join(changes_summary)
    
    
    def _check_rate_limit(self, alert_type: str) -> bool:
        """Check if alert is within rate limit."""
        current_time = datetime.utcnow()
        hour_ago = current_time - timedelta(hours=1)
        
        # Get alerts sent in the last hour
        recent_alerts = [
            time for time in self.alert_history.get(alert_type, [])
            if time > hour_ago
        ]
        
        # Check if within rate limit
        if len(recent_alerts) >= self.config.max_alerts_per_hour:
            return False
        
        return True
    
    def _check_cooldown(self, alert_type: str) -> bool:
        """Check if alert is not in cooldown period."""
        current_time = datetime.utcnow()
        last_alert_time = self.last_alert_times.get(alert_type)
        
        if last_alert_time is None:
            return True
        
        cooldown_period = timedelta(minutes=self.config.alert_cooldown_minutes)
        
        if current_time - last_alert_time < cooldown_period:
            return False
        
        return True
    
    def _update_alert_history(self, alert_type: str) -> None:
        """Update alert history for rate limiting."""
        current_time = datetime.utcnow()
        
        if alert_type not in self.alert_history:
            self.alert_history[alert_type] = []
        
        self.alert_history[alert_type].append(current_time)
        self.last_alert_times[alert_type] = current_time
        
        # Clean up old entries (older than 1 hour)
        hour_ago = current_time - timedelta(hours=1)
        self.alert_history[alert_type] = [
            time for time in self.alert_history[alert_type]
            if time > hour_ago
        ]
    
    async def send_daily_summary(self, report_data: Dict) -> None:
        """Send daily summary log."""
        try:
            # Create summary log message
            summary_message = f"""
Daily Book Change Report - {datetime.utcnow().strftime('%Y-%m-%d')}

Summary:
- Total books checked: {report_data.get('total_books_checked', 0)}
- Changes detected: {report_data.get('changes_detected', 0)}
- New books: {report_data.get('new_books', 0)}
- Updated books: {report_data.get('updated_books', 0)}
- Removed books: {report_data.get('removed_books', 0)}

Changes by Type:
"""
            
            for change_type, count in report_data.get('changes_by_type', {}).items():
                summary_message += f"- {change_type.replace('_', ' ').title()}: {count}\n"
            
            summary_message += "\nChanges by Severity:\n"
            
            for severity, count in report_data.get('changes_by_severity', {}).items():
                summary_message += f"- {severity.value.title()}: {count}\n"
            
            # Log the daily summary
            self.logger.info(
                "Daily change detection summary",
                message=summary_message.strip(),
                report_data=report_data
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to send daily summary",
                error=str(e)
            )

