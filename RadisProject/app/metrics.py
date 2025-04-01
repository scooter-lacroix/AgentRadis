import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ToolMetric:
    tool_name: str
    start_time: float
    end_time: float
    duration: float
    success: bool
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MetricsTracker:
    def __init__(self):
        self.tool_executions: List[ToolMetric] = []
        self.error_counts: Dict[str, int] = {}  # tool_name -> error count
        self.total_execution_time: float = 0.0
        self.start_time = time.time()

    def start_operation(self, tool_name: str) -> float:
        """Start timing a tool operation.

        Args:
            tool_name: Name of the tool being executed

        Returns:
            float: Start timestamp
        """
        return time.time()

    def end_operation(
        self,
        tool_name: str,
        start_time: float,
        success: bool,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record the completion of a tool operation.

        Args:
            tool_name: Name of the tool that was executed
            start_time: Operation start timestamp
            success: Whether the operation succeeded
            error: Error message if the operation failed
            metadata: Additional operation metadata
        """
        end_time = time.time()
        duration = end_time - start_time

        metric = ToolMetric(
            tool_name=tool_name,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            success=success,
            error=error,
            metadata=metadata,
        )

        self.tool_executions.append(metric)
        self.total_execution_time += duration

        if not success and error:
            self.error_counts[tool_name] = self.error_counts.get(tool_name, 0) + 1

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all tracked metrics.

        Returns:
            Dict containing metrics summary
        """
        tool_stats: Dict[str, Dict[str, Any]] = {}

        for metric in self.tool_executions:
            if metric.tool_name not in tool_stats:
                tool_stats[metric.tool_name] = {
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "total_duration": 0.0,
                    "average_duration": 0.0,
                    "error_count": self.error_counts.get(metric.tool_name, 0),
                }

            stats = tool_stats[metric.tool_name]
            stats["total_calls"] += 1
            stats["total_duration"] += metric.duration

            if metric.success:
                stats["successful_calls"] += 1
            else:
                stats["failed_calls"] += 1

            stats["average_duration"] = stats["total_duration"] / stats["total_calls"]

        return {
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "total_execution_time": self.total_execution_time,
            "total_operations": len(self.tool_executions),
            "total_errors": sum(self.error_counts.values()),
            "tool_statistics": tool_stats,
        }

    def get_operation_history(self) -> List[Dict[str, Any]]:
        """Get detailed history of all operations.

        Returns:
            List of all operation metrics
        """
        return [metric.to_dict() for metric in self.tool_executions]

    def export_metrics(self, file_path: str) -> None:
        """Export metrics to a JSON file.

        Args:
            file_path: Path to save the metrics JSON file
        """
        metrics_data = {
            "summary": self.get_metrics_summary(),
            "operation_history": self.get_operation_history(),
        }

        with open(file_path, "w") as f:
            json.dump(metrics_data, f, indent=2)

    def reset(self) -> None:
        """Reset all metrics."""
        self.tool_executions = []
        self.error_counts = {}
        self.total_execution_time = 0.0
        self.start_time = time.time()

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors by tool.

        Returns:
            Dict containing error statistics by tool
        """
        error_summary = {}
        for metric in self.tool_executions:
            if not metric.success and metric.error:
                if metric.tool_name not in error_summary:
                    error_summary[metric.tool_name] = []
                error_summary[metric.tool_name].append(
                    {
                        "timestamp": datetime.fromtimestamp(
                            metric.start_time
                        ).isoformat(),
                        "error": metric.error,
                        "metadata": metric.metadata,
                    }
                )
        return error_summary
