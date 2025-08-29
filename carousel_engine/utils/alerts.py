"""
Alerting and notification utilities
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class AlertLevel(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Alert:
    """Alert message"""
    
    def __init__(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        self.level = level
        self.title = title
        self.message = message
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.utcnow()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            "level": self.level.value,
            "title": self.title,
            "message": self.message,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class AlertManager:
    """Manage alerts and notifications"""
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.handlers: List[Callable[[Alert], None]] = []
        self.alert_counts = {level: 0 for level in AlertLevel}
        
    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add alert handler
        
        Args:
            handler: Function to handle alerts
        """
        self.handlers.append(handler)
        logger.info("Added alert handler", handler=handler.__name__)
        
    def send_alert(self, alert: Alert) -> None:
        """Send alert to all handlers
        
        Args:
            alert: Alert to send
        """
        try:
            # Store alert
            self.alerts.append(alert)
            self.alert_counts[alert.level] += 1
            
            # Trim old alerts (keep last 1000)
            if len(self.alerts) > 1000:
                self.alerts = self.alerts[-1000:]
            
            # Send to handlers
            for handler in self.handlers:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(
                        "Alert handler failed",
                        handler=handler.__name__,
                        error=str(e)
                    )
            
            logger.info(
                "Alert sent",
                level=alert.level.value,
                title=alert.title,
                handlers=len(self.handlers)
            )
            
        except Exception as e:
            logger.error("Failed to send alert", error=str(e))
    
    def create_alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Create and send alert
        
        Args:
            level: Alert level
            title: Alert title
            message: Alert message
            metadata: Additional metadata
        """
        alert = Alert(level, title, message, metadata)
        self.send_alert(alert)
    
    def get_alerts(
        self,
        level: Optional[AlertLevel] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Alert]:
        """Get stored alerts
        
        Args:
            level: Filter by alert level
            since: Get alerts since this timestamp
            limit: Limit number of results
            
        Returns:
            List of alerts
        """
        filtered_alerts = self.alerts
        
        # Filter by level
        if level:
            filtered_alerts = [a for a in filtered_alerts if a.level == level]
        
        # Filter by time
        if since:
            filtered_alerts = [a for a in filtered_alerts if a.timestamp >= since]
        
        # Sort by timestamp (newest first)
        filtered_alerts.sort(key=lambda a: a.timestamp, reverse=True)
        
        # Apply limit
        if limit:
            filtered_alerts = filtered_alerts[:limit]
            
        return filtered_alerts
    
    def get_alert_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get alert summary statistics
        
        Args:
            hours: Time window in hours
            
        Returns:
            Alert summary
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        recent_alerts = self.get_alerts(since=since)
        
        level_counts = {level.value: 0 for level in AlertLevel}
        for alert in recent_alerts:
            level_counts[alert.level.value] += 1
        
        return {
            "time_window_hours": hours,
            "total_alerts": len(recent_alerts),
            "by_level": level_counts,
            "latest_alert": recent_alerts[0].to_dict() if recent_alerts else None,
            "all_time_counts": {level.value: count for level, count in self.alert_counts.items()}
        }


class HealthChecker:
    """Monitor system health and send alerts"""
    
    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager
        self.checks: Dict[str, Callable[[], bool]] = {}
        self.last_check_results: Dict[str, bool] = {}
        
    def add_health_check(self, name: str, check_func: Callable[[], bool]) -> None:
        """Add health check function
        
        Args:
            name: Check name
            check_func: Function that returns True if healthy
        """
        self.checks[name] = check_func
        logger.info("Added health check", name=name)
        
    async def run_health_checks(self) -> Dict[str, bool]:
        """Run all health checks
        
        Returns:
            Dictionary of check results
        """
        results = {}
        
        for name, check_func in self.checks.items():
            try:
                logger.debug("Running health check", name=name)
                result = check_func()
                results[name] = result
                
                # Check if status changed
                previous_result = self.last_check_results.get(name)
                if previous_result is not None and previous_result != result:
                    # Status changed, send alert
                    if result:
                        self.alert_manager.create_alert(
                            AlertLevel.INFO,
                            f"Health check recovered: {name}",
                            f"Health check '{name}' is now healthy"
                        )
                    else:
                        self.alert_manager.create_alert(
                            AlertLevel.ERROR,
                            f"Health check failed: {name}",
                            f"Health check '{name}' is now unhealthy"
                        )
                
                self.last_check_results[name] = result
                
            except Exception as e:
                logger.error("Health check failed", name=name, error=str(e))
                results[name] = False
                
                # Send alert for check failure
                self.alert_manager.create_alert(
                    AlertLevel.ERROR,
                    f"Health check error: {name}",
                    f"Health check '{name}' failed with error: {e}"
                )
        
        return results


# Alert handlers
def console_alert_handler(alert: Alert) -> None:
    """Print alert to console"""
    print(f"[{alert.level.value.upper()}] {alert.title}: {alert.message}")


def log_alert_handler(alert: Alert) -> None:
    """Log alert using structured logger"""
    logger.log(
        alert.level.value,
        "Alert triggered",
        title=alert.title,
        message=alert.message,
        metadata=alert.metadata
    )


async def webhook_alert_handler(alert: Alert, webhook_url: str) -> None:
    """Send alert to webhook endpoint"""
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=alert.to_dict(),
                timeout=10.0
            )
            response.raise_for_status()
            
        logger.info("Alert sent to webhook", webhook_url=webhook_url)
        
    except Exception as e:
        logger.error("Failed to send webhook alert", error=str(e))


# Global alert manager
alert_manager = AlertManager()

# Add default handlers
alert_manager.add_handler(console_alert_handler)
alert_manager.add_handler(log_alert_handler)