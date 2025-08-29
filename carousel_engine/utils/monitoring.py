"""
Monitoring and metrics utilities
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class MetricPoint:
    """Individual metric measurement"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    

class MetricsCollector:
    """Collect and store application metrics"""
    
    def __init__(self, max_points: int = 1000):
        """Initialize metrics collector
        
        Args:
            max_points: Maximum number of metric points to store
        """
        self.max_points = max_points
        self.metrics: List[MetricPoint] = []
        
    def record_metric(
        self, 
        name: str, 
        value: float, 
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a metric value
        
        Args:
            name: Metric name
            value: Metric value
            tags: Optional tags for metric
        """
        try:
            point = MetricPoint(
                name=name,
                value=value,
                timestamp=datetime.utcnow(),
                tags=tags or {}
            )
            
            self.metrics.append(point)
            
            # Trim old metrics if we exceed max_points
            if len(self.metrics) > self.max_points:
                self.metrics = self.metrics[-self.max_points:]
                
            logger.debug("Recorded metric", name=name, value=value, tags=tags)
            
        except Exception as e:
            logger.error("Failed to record metric", name=name, error=str(e))
    
    def get_metrics(
        self, 
        name: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[MetricPoint]:
        """Get stored metrics
        
        Args:
            name: Filter by metric name
            since: Filter metrics since this timestamp
            limit: Limit number of results
            
        Returns:
            List of metric points
        """
        filtered_metrics = self.metrics
        
        # Filter by name
        if name:
            filtered_metrics = [m for m in filtered_metrics if m.name == name]
        
        # Filter by time
        if since:
            filtered_metrics = [m for m in filtered_metrics if m.timestamp >= since]
        
        # Sort by timestamp (newest first)
        filtered_metrics.sort(key=lambda m: m.timestamp, reverse=True)
        
        # Apply limit
        if limit:
            filtered_metrics = filtered_metrics[:limit]
            
        return filtered_metrics
    
    def get_metric_summary(self, name: str, minutes: int = 60) -> Dict[str, Any]:
        """Get metric summary statistics
        
        Args:
            name: Metric name
            minutes: Time window in minutes
            
        Returns:
            Summary statistics
        """
        since = datetime.utcnow() - timedelta(minutes=minutes)
        points = self.get_metrics(name=name, since=since)
        
        if not points:
            return {
                "name": name,
                "count": 0,
                "time_window_minutes": minutes
            }
        
        values = [p.value for p in points]
        
        return {
            "name": name,
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[0] if values else None,
            "time_window_minutes": minutes,
            "first_timestamp": points[-1].timestamp.isoformat(),
            "latest_timestamp": points[0].timestamp.isoformat()
        }


class PerformanceTimer:
    """Context manager for timing operations"""
    
    def __init__(self, operation_name: str, metrics_collector: Optional[MetricsCollector] = None):
        """Initialize performance timer
        
        Args:
            operation_name: Name of operation being timed
            metrics_collector: Optional metrics collector to record timing
        """
        self.operation_name = operation_name
        self.metrics_collector = metrics_collector
        self.start_time = None
        self.end_time = None
        
    def __enter__(self):
        """Start timing"""
        self.start_time = time.time()
        logger.debug("Started timing operation", operation=self.operation_name)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record result"""
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        # Record metric if collector provided
        if self.metrics_collector:
            self.metrics_collector.record_metric(
                f"operation_duration_{self.operation_name}",
                duration,
                {"operation": self.operation_name}
            )
        
        if exc_type is None:
            logger.info("Completed operation", operation=self.operation_name, duration=duration)
        else:
            logger.error(
                "Operation failed", 
                operation=self.operation_name, 
                duration=duration,
                error=str(exc_val)
            )
    
    @property
    def duration(self) -> Optional[float]:
        """Get operation duration
        
        Returns:
            Duration in seconds, or None if not completed
        """
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


class CostTracker:
    """Track API costs and usage"""
    
    def __init__(self, max_cost_per_run: float = 1.0):
        """Initialize cost tracker
        
        Args:
            max_cost_per_run: Maximum allowed cost per operation
        """
        self.max_cost_per_run = max_cost_per_run
        self.costs: List[Dict[str, Any]] = []
        
    def record_cost(
        self, 
        service: str, 
        operation: str, 
        cost: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record API cost
        
        Args:
            service: Service name (e.g., 'openai', 'google_drive')
            operation: Operation name (e.g., 'image_generation', 'file_upload')
            cost: Cost in USD
            metadata: Additional metadata
        """
        cost_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": service,
            "operation": operation,
            "cost": cost,
            "metadata": metadata or {}
        }
        
        self.costs.append(cost_record)
        
        logger.info(
            "Recorded API cost",
            service=service,
            operation=operation,
            cost=cost
        )
    
    def get_total_cost(
        self, 
        since: Optional[datetime] = None,
        service: Optional[str] = None
    ) -> float:
        """Get total cost
        
        Args:
            since: Calculate cost since this timestamp
            service: Filter by service name
            
        Returns:
            Total cost in USD
        """
        filtered_costs = self.costs
        
        if since:
            since_iso = since.isoformat()
            filtered_costs = [
                c for c in filtered_costs 
                if c["timestamp"] >= since_iso
            ]
        
        if service:
            filtered_costs = [
                c for c in filtered_costs 
                if c["service"] == service
            ]
        
        return sum(c["cost"] for c in filtered_costs)
    
    def check_cost_limit(self, additional_cost: float = 0.0) -> bool:
        """Check if operation would exceed cost limit
        
        Args:
            additional_cost: Additional cost to check
            
        Returns:
            True if within limit, False if would exceed
        """
        current_total = self.get_total_cost()
        return (current_total + additional_cost) <= self.max_cost_per_run
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost summary
        
        Returns:
            Cost summary statistics
        """
        if not self.costs:
            return {
                "total_operations": 0,
                "total_cost": 0.0,
                "cost_limit": self.max_cost_per_run,
                "within_limit": True
            }
        
        total_cost = self.get_total_cost()
        service_costs = {}
        
        for cost in self.costs:
            service = cost["service"]
            service_costs[service] = service_costs.get(service, 0) + cost["cost"]
        
        return {
            "total_operations": len(self.costs),
            "total_cost": total_cost,
            "cost_limit": self.max_cost_per_run,
            "within_limit": total_cost <= self.max_cost_per_run,
            "cost_by_service": service_costs,
            "latest_operation": self.costs[-1] if self.costs else None
        }


# Global instances
metrics_collector = MetricsCollector()
cost_tracker = CostTracker()