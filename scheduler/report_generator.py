"""
Report generation system for change detection results.

This module provides:
- Daily change reports in JSON and CSV formats
- Report data aggregation and formatting
- Report storage and retrieval
- Export functionality
"""

import csv
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from scheduler.models import DailyReport, ChangeLog, ChangeType, ChangeSeverity, ChangeDetectionResult

logger = structlog.get_logger(__name__)


class ReportGenerator:
    """Generator for daily change reports."""
    
    def __init__(self, db_manager, reports_dir: str = "reports"):
        """
        Initialize report generator.
        
        Args:
            db_manager: Database manager instance
            reports_dir: Directory to store reports
        """
        self.db_manager = db_manager
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(exist_ok=True)
        self.logger = logger.bind(component="report_generator")
    
    async def generate_daily_report(
        self, 
        report_date: Optional[datetime] = None,
        format: str = "json"
    ) -> DailyReport:
        """
        Generate daily change report.
        
        Args:
            report_date: Date for the report (defaults to today)
            format: Report format (json/csv)
            
        Returns:
            DailyReport instance
        """
        if report_date is None:
            report_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        report_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        self.logger.info(
            "Generating daily report",
            report_id=report_id,
            report_date=report_date,
            format=format
        )
        
        try:
            # Get detection results for the date
            detection_results = await self._get_detection_results_for_date(report_date)
            
            # Get change logs for the date
            change_logs = await self._get_change_logs_for_date(report_date)
            
            # Get system statistics
            system_stats = await self._get_system_statistics()
            
            # Aggregate report data
            report_data = await self._aggregate_report_data(
                detection_results, change_logs, system_stats
            )
            
            # Create daily report
            daily_report = DailyReport(
                report_id=report_id,
                report_date=report_date,
                generated_at=start_time,
                **report_data
            )
            
            # Store report in database
            await self._store_report(daily_report)
            
            # Export report to file
            if format == "json":
                await self._export_json_report(daily_report)
            elif format == "csv":
                await self._export_csv_report(daily_report)
            
            self.logger.info(
                "Generated daily report",
                report_id=report_id,
                changes_detected=daily_report.changes_detected,
                format=format
            )
            
            return daily_report
            
        except Exception as e:
            self.logger.error(
                "Failed to generate daily report",
                report_id=report_id,
                error=str(e)
            )
            raise
    
    async def _get_detection_results_for_date(self, report_date: datetime) -> List[ChangeDetectionResult]:
        """Get detection results for a specific date."""
        try:
            start_of_day = report_date
            end_of_day = report_date + timedelta(days=1)
            
            cursor = self.db_manager.database.detection_results.find({
                "run_timestamp": {
                    "$gte": start_of_day,
                    "$lt": end_of_day
                }
            })
            
            results = []
            async for doc in cursor:
                results.append(ChangeDetectionResult(**doc))
            
            self.logger.debug(
                "Retrieved detection results",
                date=report_date,
                count=len(results)
            )
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Failed to get detection results",
                date=report_date,
                error=str(e)
            )
            return []
    
    async def _get_change_logs_for_date(self, report_date: datetime) -> List[ChangeLog]:
        """Get change logs for a specific date."""
        try:
            start_of_day = report_date
            end_of_day = report_date + timedelta(days=1)
            
            cursor = self.db_manager.database.change_logs.find({
                "detected_at": {
                    "$gte": start_of_day,
                    "$lt": end_of_day
                }
            })
            
            logs = []
            async for doc in cursor:
                # Convert string URL back to HttpUrl
                if 'source_url' in doc and doc['source_url']:
                    from pydantic import HttpUrl
                    doc['source_url'] = HttpUrl(doc['source_url'])
                logs.append(ChangeLog(**doc))
            
            self.logger.debug(
                "Retrieved change logs",
                date=report_date,
                count=len(logs)
            )
            
            return logs
            
        except Exception as e:
            self.logger.error(
                "Failed to get change logs",
                date=report_date,
                error=str(e)
            )
            return []
    
    async def _get_system_statistics(self) -> Dict[str, Any]:
        """Get system statistics."""
        try:
            # Get total books count
            total_books = await self.db_manager.collection.count_documents({})
            
            # Get books by status
            active_books = await self.db_manager.collection.count_documents({
                "crawl_status": "success"
            })
            
            removed_books = await self.db_manager.collection.count_documents({
                "crawl_status": "removed"
            })
            
            # Get categories
            pipeline = [
                {"$group": {"_id": "$category"}},
                {"$count": "total_categories"}
            ]
            category_result = await self.db_manager.collection.aggregate(pipeline).to_list(1)
            total_categories = category_result[0]["total_categories"] if category_result else 0
            
            return {
                "total_books": total_books,
                "active_books": active_books,
                "removed_books": removed_books,
                "total_categories": total_categories
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get system statistics",
                error=str(e)
            )
            return {
                "total_books": 0,
                "active_books": 0,
                "removed_books": 0,
                "total_categories": 0
            }
    
    async def _aggregate_report_data(
        self, 
        detection_results: List[ChangeDetectionResult],
        change_logs: List[ChangeLog],
        system_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Aggregate data for the daily report."""
        try:
            # Initialize counters
            total_books_checked = 0
            changes_detected = 0
            new_books = 0
            updated_books = 0
            removed_books = 0
            total_processing_time = 0.0
            changes_by_type = {}
            changes_by_severity = {}
            significant_changes = []
            new_books_list = []
            errors = []
            
            # Aggregate detection results
            for result in detection_results:
                total_books_checked += result.total_books_checked
                changes_detected += result.changes_detected
                new_books += result.new_books
                updated_books += result.updated_books
                removed_books += result.removed_books
                total_processing_time += result.detection_duration_seconds
                errors.extend(result.errors)
                
                # Merge change type counts
                for change_type, count in result.changes_by_type.items():
                    changes_by_type[change_type] = changes_by_type.get(change_type, 0) + count
                
                # Merge severity counts
                for severity, count in result.changes_by_severity.items():
                    changes_by_severity[severity] = changes_by_severity.get(severity, 0) + count
            
            # Process change logs
            for log in change_logs:
                # Add significant changes (high/medium severity)
                if log.severity in [ChangeSeverity.HIGH, ChangeSeverity.MEDIUM]:
                    significant_changes.append(log)
                
                # Track new books
                if log.change_type == ChangeType.NEW_BOOK:
                    new_books_list.append({
                        "book_id": log.book_id,
                        "name": log.new_value,
                        "detected_at": log.detected_at.isoformat()
                    })
            
            # Calculate averages
            avg_processing_time = (
                total_processing_time / len(detection_results) 
                if detection_results else 0.0
            )
            
            # Calculate system health score
            system_health_score = self._calculate_health_score(
                total_books_checked, changes_detected, len(errors)
            )
            
            return {
                "total_books_in_system": system_stats["total_books"],
                "books_checked": total_books_checked,
                "changes_detected": changes_detected,
                "new_books_added": new_books,
                "books_updated": updated_books,
                "books_removed": removed_books,
                "changes_by_type": changes_by_type,
                "changes_by_severity": changes_by_severity,
                "total_processing_time_seconds": total_processing_time,
                "average_book_processing_time": avg_processing_time,
                "significant_changes": significant_changes,
                "new_books": new_books_list,
                "errors_encountered": errors,
                "system_health_score": system_health_score
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to aggregate report data",
                error=str(e)
            )
            raise
    
    def _calculate_health_score(
        self, 
        books_checked: int, 
        changes_detected: int, 
        errors_count: int
    ) -> float:
        """Calculate system health score (0.0 to 1.0)."""
        try:
            if books_checked == 0:
                return 0.0
            
            # Base score from successful processing
            success_rate = 1.0 - (errors_count / max(books_checked, 1))
            
            # Bonus for detecting changes (system is working)
            change_bonus = min(changes_detected / max(books_checked, 1), 0.1)
            
            # Final score
            health_score = min(success_rate + change_bonus, 1.0)
            
            return round(health_score, 2)
            
        except Exception as e:
            self.logger.error(
                "Failed to calculate health score",
                error=str(e)
            )
            return 0.0
    
    async def _store_report(self, report: DailyReport) -> None:
        """Store report in database."""
        try:
            report_dict = report.model_dump()
            await self.db_manager.database.daily_reports.insert_one(report_dict)
            
            self.logger.debug(
                "Stored daily report",
                report_id=report.report_id
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to store daily report",
                report_id=report.report_id,
                error=str(e)
            )
    
    async def _export_json_report(self, report: DailyReport) -> None:
        """Export report to JSON file."""
        try:
            filename = f"daily_report_{report.report_date.strftime('%Y%m%d')}.json"
            filepath = self.reports_dir / filename
            
            # Convert to dict and handle datetime serialization
            report_dict = report.model_dump()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_dict, f, indent=2, default=str, ensure_ascii=False)
            
            self.logger.info(
                "Exported JSON report",
                filepath=str(filepath)
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to export JSON report",
                error=str(e)
            )
    
    async def _export_csv_report(self, report: DailyReport) -> None:
        """Export report to CSV file."""
        try:
            filename = f"daily_report_{report.report_date.strftime('%Y%m%d')}.csv"
            filepath = self.reports_dir / filename
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow([
                    'Report ID', 'Report Date', 'Generated At',
                    'Total Books in System', 'Books Checked', 'Changes Detected',
                    'New Books Added', 'Books Updated', 'Books Removed',
                    'Total Processing Time (s)', 'Average Processing Time (s)',
                    'System Health Score'
                ])
                
                # Write main report data
                writer.writerow([
                    report.report_id,
                    report.report_date.strftime('%Y-%m-%d'),
                    report.generated_at.strftime('%Y-%m-%d %H:%M:%S'),
                    report.total_books_in_system,
                    report.books_checked,
                    report.changes_detected,
                    report.new_books_added,
                    report.books_updated,
                    report.books_removed,
                    report.total_processing_time_seconds,
                    report.average_book_processing_time,
                    report.system_health_score
                ])
                
                # Write changes by type
                writer.writerow([])  # Empty row
                writer.writerow(['Changes by Type'])
                for change_type, count in report.changes_by_type.items():
                    writer.writerow([change_type.value, count])
                
                # Write changes by severity
                writer.writerow([])  # Empty row
                writer.writerow(['Changes by Severity'])
                for severity, count in report.changes_by_severity.items():
                    writer.writerow([severity.value, count])
                
                # Write significant changes
                if report.significant_changes:
                    writer.writerow([])  # Empty row
                    writer.writerow([
                        'Significant Changes',
                        'Change Type', 'Severity', 'Summary', 'Detected At'
                    ])
                    for change in report.significant_changes:
                        writer.writerow([
                            '',
                            change.change_type.value,
                            change.severity.value,
                            change.change_summary,
                            change.detected_at.strftime('%Y-%m-%d %H:%M:%S')
                        ])
            
            self.logger.info(
                "Exported CSV report",
                filepath=str(filepath)
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to export CSV report",
                error=str(e)
            )
    
    async def get_report_history(self, days: int = 7) -> List[DailyReport]:
        """Get report history for the last N days."""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            cursor = self.db_manager.database.daily_reports.find({
                "report_date": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }).sort("report_date", -1)
            
            reports = []
            async for doc in cursor:
                reports.append(DailyReport(**doc))
            
            self.logger.debug(
                "Retrieved report history",
                days=days,
                count=len(reports)
            )
            
            return reports
            
        except Exception as e:
            self.logger.error(
                "Failed to get report history",
                error=str(e)
            )
            return []
    
    async def cleanup_old_reports(self, retention_days: int = 30) -> int:
        """Clean up old reports beyond retention period."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            result = await self.db_manager.database.daily_reports.delete_many({
                "report_date": {"$lt": cutoff_date}
            })
            
            deleted_count = result.deleted_count
            
            self.logger.info(
                "Cleaned up old reports",
                deleted_count=deleted_count,
                retention_days=retention_days
            )
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(
                "Failed to cleanup old reports",
                error=str(e)
            )
            return 0

