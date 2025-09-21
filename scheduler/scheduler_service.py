"""
Main scheduler service for Part 2: Scheduler and Change Detection.

This module provides:
- Daily scheduling with APScheduler
- Change detection orchestration
- Integration with all scheduler components
- Error handling and recovery
"""

import asyncio
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from scheduler.models import SchedulerConfig, AlertConfig
from scheduler.change_detector import ChangeDetector
from scheduler.fingerprinting import FingerprintManager
from scheduler.alerting import AlertManager
from scheduler.report_generator import ReportGenerator
from crawler.database import MongoDBManager
from utilities.logger import setup_logging

logger = structlog.get_logger(__name__)


class SchedulerService:
    """Main scheduler service for change detection."""
    
    def __init__(self, config: SchedulerConfig, db_manager: MongoDBManager):
        """
        Initialize scheduler service.
        
        Args:
            config: Scheduler configuration
            db_manager: Database manager instance
        """
        self.config = config
        self.db_manager = db_manager
        self.scheduler = AsyncIOScheduler(timezone=config.timezone)
        self.logger = logger.bind(component="scheduler_service")
        
        # Initialize components
        self.fingerprint_manager = FingerprintManager(db_manager)
        self.change_detector = ChangeDetector(db_manager, self.fingerprint_manager)
        self.alert_manager = AlertManager(config.alert_config)
        self.report_generator = ReportGenerator(db_manager)
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        # Setup scheduler event listeners
        self._setup_scheduler_listeners()
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _setup_scheduler_listeners(self) -> None:
        """Setup scheduler event listeners."""
        def job_executed_listener(event):
            self.logger.info(
                "Job executed successfully",
                job_id=event.job_id,
                job_name=event.job_id,
                duration=event.retval.get('duration', 0) if event.retval else 0
            )
        
        def job_error_listener(event):
            self.logger.error(
                "Job execution failed",
                job_id=event.job_id,
                job_name=event.job_id,
                error=str(event.exception)
            )
        
        self.scheduler.add_listener(job_executed_listener, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(job_error_listener, EVENT_JOB_ERROR)
    
    async def start(self, test_mode: bool = False, run_once: bool = False) -> None:
        """Start the scheduler service."""
        try:
            if run_once:
                self.logger.info("Starting scheduler service in RUN ONCE MODE")
            elif test_mode:
                self.logger.info("Starting scheduler service in TEST MODE")
            else:
                self.logger.info("Starting scheduler service")
            
            # Connect to database
            await self.db_manager.connect()
            
            # Setup database collections for scheduler
            await self._setup_database_collections()
            
            if run_once:
                # Run change detection once and exit
                await self._run_once_mode()
                return
            
            # Add scheduled jobs (test mode or normal mode)
            if test_mode:
                await self._add_test_scheduled_jobs()
                self.logger.info("Test jobs added (2-minute intervals)")
            else:
                await self._add_scheduled_jobs()
                self.logger.info("Production jobs added")
            
            # Start scheduler
            self.scheduler.start()
            
            self.logger.info(
                "Scheduler service started",
                timezone=self.config.timezone,
                schedule_hour=self.config.schedule_hour,
                schedule_minute=self.config.schedule_minute
            )
            
            # Keep the service running
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt, shutting down...")
                self.stop()
                
        except Exception as e:
            self.logger.error(
                "Failed to start scheduler service",
                error=str(e)
            )
            raise
    
    async def _run_once_mode(self) -> None:
        """Run change detection once and exit."""
        try:
            # Get total book count first
            total_books = await self.db_manager.collection.count_documents({})
            self.logger.info(f"Running change detection once on {total_books} books...")
            
            # Run change detection with reduced verbosity
            result = await self.run_manual_change_detection(verbose=False)
            
            # Generate a simple report
            if result['success']:
                self.logger.info(
                    "Change detection completed successfully",
                    changes_detected=result.get('changes_detected', 0),
                    updated_books=result.get('updated_books', 0),
                    duration=result.get('duration', 0)
                )
                
                # Generate a simple report
                if self.config.generate_daily_reports:
                    self.logger.info("Generating daily report...")
                    report = await self.report_generator.generate_daily_report(
                        report_date=datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
                        format=self.config.report_format
                    )
                    self.logger.info(
                        "Daily report generated",
                        report_id=report.report_id,
                        changes_detected=report.changes_detected
                    )
            else:
                self.logger.error(
                    "Change detection failed",
                    error=result.get('error', 'Unknown error')
                )
            
            self.logger.info("Run once mode completed. Exiting...")
            
        except Exception as e:
            self.logger.error(
                "Error in run once mode",
                error=str(e)
            )
            raise
    
    def stop(self) -> None:
        """Stop the scheduler service."""
        try:
            self.logger.info("Stopping scheduler service")
            
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
            
            self.logger.info("Scheduler service stopped")
            
        except Exception as e:
            self.logger.error(
                "Error stopping scheduler service",
                error=str(e)
            )
    
    async def _setup_database_collections(self) -> None:
        """Setup database collections for scheduler functionality."""
        try:
            # Create collections if they don't exist
            collections = [
                'fingerprints',
                'change_logs', 
                'detection_results',
                'daily_reports'
            ]
            
            for collection_name in collections:
                if collection_name not in await self.db_manager.database.list_collection_names():
                    await self.db_manager.database.create_collection(collection_name)
                    self.logger.debug(f"Created collection: {collection_name}")
            
            # Create indexes for performance
            await self._create_scheduler_indexes()
            
            self.logger.info("Database collections setup completed")
            
        except Exception as e:
            self.logger.error(
                "Failed to setup database collections",
                error=str(e)
            )
            raise
    
    async def _create_scheduler_indexes(self) -> None:
        """Create indexes for scheduler collections."""
        try:
            # Fingerprints collection indexes
            await self.db_manager.database.fingerprints.create_index("book_id", unique=True)
            await self.db_manager.database.fingerprints.create_index("source_url")
            await self.db_manager.database.fingerprints.create_index("updated_at")
            
            # Change logs collection indexes
            await self.db_manager.database.change_logs.create_index("change_id", unique=True)
            await self.db_manager.database.change_logs.create_index("book_id")
            await self.db_manager.database.change_logs.create_index("detected_at")
            await self.db_manager.database.change_logs.create_index("change_type")
            await self.db_manager.database.change_logs.create_index("severity")
            
            # Detection results collection indexes
            await self.db_manager.database.detection_results.create_index("detection_id", unique=True)
            await self.db_manager.database.detection_results.create_index("run_timestamp")
            
            # Daily reports collection indexes
            await self.db_manager.database.daily_reports.create_index("report_id", unique=True)
            await self.db_manager.database.daily_reports.create_index("report_date")
            
            self.logger.debug("Created scheduler indexes")
            
        except Exception as e:
            self.logger.error(
                "Failed to create scheduler indexes",
                error=str(e)
            )
    
    async def _add_scheduled_jobs(self) -> None:
        """Add scheduled jobs to the scheduler."""
        try:
            # Change detection job (daily at specified time)
            if self.config.enable_change_detection:
                self.scheduler.add_job(
                    func=self._daily_change_detection_job,
                    trigger=CronTrigger(
                        hour=self.config.schedule_hour,
                        minute=self.config.schedule_minute,
                        timezone=self.config.timezone
                    ),
                    id='daily_change_detection',
                    name='Daily Change Detection',
                    max_instances=1,
                    replace_existing=True
                )
                self.logger.info(
                    "Added daily change detection job",
                    hour=self.config.schedule_hour,
                    minute=self.config.schedule_minute,
                    timezone=self.config.timezone
                )
            
            # Report generation job (daily at specified time + 5 minutes)
            if self.config.generate_daily_reports:
                report_hour = self.config.schedule_hour
                report_minute = self.config.schedule_minute + 5
                if report_minute >= 60:
                    report_hour = (report_hour + 1) % 24
                    report_minute = report_minute - 60
                
                self.scheduler.add_job(
                    func=self._daily_report_generation_job,
                    trigger=CronTrigger(
                        hour=report_hour,
                        minute=report_minute,
                        timezone=self.config.timezone
                    ),
                    id='daily_report_generation',
                    name='Daily Report Generation',
                    max_instances=1,
                    replace_existing=True
                )
                self.logger.info(
                    "Added daily report generation job",
                    hour=report_hour,
                    minute=report_minute,
                    timezone=self.config.timezone
                )
            
            # Report cleanup job (daily at 1 AM)
            self.scheduler.add_job(
                func=self._report_cleanup_job,
                trigger=CronTrigger(
                    hour=1,
                    minute=0,
                    timezone=self.config.timezone
                ),
                id='report_cleanup',
                name='Daily Report Cleanup',
                max_instances=1,
                replace_existing=True
            )
            self.logger.info(
                "Added daily report cleanup job",
                hour=1,
                minute=0,
                timezone=self.config.timezone
            )
            
            # Fingerprint cleanup job (daily at 1:30 AM)
            self.scheduler.add_job(
                func=self._fingerprint_cleanup_job,
                trigger=CronTrigger(
                    hour=1,
                    minute=30,
                    timezone=self.config.timezone
                ),
                id='fingerprint_cleanup',
                name='Daily Fingerprint Cleanup',
                max_instances=1,
                replace_existing=True
            )
            self.logger.info(
                "Added daily fingerprint cleanup job",
                hour=1,
                minute=30,
                timezone=self.config.timezone
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to add scheduled jobs",
                error=str(e)
            )
            raise
    
    async def _add_test_scheduled_jobs(self) -> None:
        """Add test scheduled jobs (every 2 minutes) for testing purposes."""
        try:
            # Test change detection job (every 2 minutes)
            if self.config.enable_change_detection:
                self.scheduler.add_job(
                    func=self._daily_change_detection_job,
                    trigger='interval',
                    minutes=2,  # Run every 2 minutes for testing
                    id='test_change_detection',
                    name='Test Change Detection (2min)',
                    max_instances=1,
                    replace_existing=True
                )
                self.logger.info("Added test change detection job (every 2 minutes)")
            
            # Test report generation job (every 4 minutes)
            if self.config.generate_daily_reports:
                self.scheduler.add_job(
                    func=self._daily_report_generation_job,
                    trigger='interval',
                    minutes=4,  # Run every 4 minutes for testing
                    id='test_report_generation',
                    name='Test Report Generation (4min)',
                    max_instances=1,
                    replace_existing=True
                )
                self.logger.info("Added test report generation job (every 4 minutes)")
            
            # Test cleanup job (every 10 minutes)
            self.scheduler.add_job(
                func=self._report_cleanup_job,
                trigger='interval',
                minutes=10,  # Run every 10 minutes for testing
                id='test_report_cleanup',
                name='Test Report Cleanup (10min)',
                max_instances=1,
                replace_existing=True
            )
            self.logger.info("Added test report cleanup job (every 10 minutes)")
            
            # Test fingerprint cleanup job (every 15 minutes)
            self.scheduler.add_job(
                func=self._fingerprint_cleanup_job,
                trigger='interval',
                minutes=15,  # Run every 15 minutes for testing
                id='test_fingerprint_cleanup',
                name='Test Fingerprint Cleanup (15min)',
                max_instances=1,
                replace_existing=True
            )
            self.logger.info("Added test fingerprint cleanup job (every 15 minutes)")
            
        except Exception as e:
            self.logger.error(
                "Failed to add test scheduled jobs",
                error=str(e)
            )
            raise
    
    async def _daily_change_detection_job(self) -> Dict:
        """Daily change detection job."""
        start_time = datetime.utcnow()
        job_id = f"change_detection_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        self.logger.info(
            "Starting daily change detection job",
            job_id=job_id
        )
        
        try:
            # Run change detection
            detection_result = await self.change_detector.detect_changes(
                max_books=None,  # Check all books
                batch_size=self.config.batch_size,
                verbose=True
            )
            
            # Get change logs for alerting
            if detection_result.changes_detected > 0:
                change_logs = await self._get_recent_change_logs()
                await self.alert_manager.process_changes(change_logs)
            
            # Calculate job duration
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            result = {
                'job_id': job_id,
                'success': detection_result.success,
                'changes_detected': detection_result.changes_detected,
                'new_books': detection_result.new_books,
                'updated_books': detection_result.updated_books,
                'removed_books': detection_result.removed_books,
                'duration': duration,
                'errors': detection_result.errors
            }
            
            self.logger.info(
                "Daily change detection job completed",
                job_id=job_id,
                **result
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Daily change detection job failed",
                error=str(e)
            )
            return {
                'job_id': job_id,
                'success': False,
                'error': str(e),
                'duration': (datetime.utcnow() - start_time).total_seconds()
            }
    
    async def _daily_report_generation_job(self) -> Dict:
        """Daily report generation job."""
        start_time = datetime.utcnow()
        job_id = f"report_generation_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        self.logger.info(
            "Starting daily report generation job",
            job_id=job_id
        )
        
        try:
            # Generate daily report
            report = await self.report_generator.generate_daily_report(
                report_date=datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
                format=self.config.report_format
            )
            
            # Send daily summary log
            report_data = {
                'total_books_checked': report.books_checked,
                'changes_detected': report.changes_detected,
                'new_books': report.new_books_added,
                'updated_books': report.books_updated,
                'removed_books': report.books_removed,
                'changes_by_type': {k.value: v for k, v in report.changes_by_type.items()},
                'changes_by_severity': {k.value: v for k, v in report.changes_by_severity.items()}
            }
            await self.alert_manager.send_daily_summary(report_data)
            
            # Calculate job duration
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            result = {
                'job_id': job_id,
                'success': True,
                'report_id': report.report_id,
                'changes_detected': report.changes_detected,
                'duration': duration
            }
            
            self.logger.info(
                "Daily report generation job completed",
                job_id=job_id,
                **result
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Daily report generation job failed",
                job_id=job_id,
                error=str(e)
            )
            return {
                'job_id': job_id,
                'success': False,
                'error': str(e),
                'duration': (datetime.utcnow() - start_time).total_seconds()
            }
    
    async def _report_cleanup_job(self) -> Dict:
        """Weekly report cleanup job."""
        start_time = datetime.utcnow()
        job_id = f"report_cleanup_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        self.logger.info(
            "Starting report cleanup job",
            job_id=job_id
        )
        
        try:
            # Cleanup old reports
            deleted_count = await self.report_generator.cleanup_old_reports(
                retention_days=self.config.report_retention_days
            )
            
            # Calculate job duration
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            result = {
                'job_id': job_id,
                'success': True,
                'deleted_reports': deleted_count,
                'duration': duration
            }
            
            self.logger.info(
                "Report cleanup job completed",
                job_id=job_id,
                **result
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Report cleanup job failed",
                job_id=job_id,
                error=str(e)
            )
            return {
                'job_id': job_id,
                'success': False,
                'error': str(e),
                'duration': (datetime.utcnow() - start_time).total_seconds()
            }
    
    async def _fingerprint_cleanup_job(self) -> Dict:
        """Daily fingerprint cleanup job."""
        start_time = datetime.utcnow()
        job_id = f"fingerprint_cleanup_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        self.logger.info(
            "Starting fingerprint cleanup job",
            job_id=job_id
        )
        
        try:
            # Cleanup orphaned fingerprints
            orphaned_count = await self.fingerprint_manager.cleanup_orphaned_fingerprints()
            
            # Calculate job duration
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            result = {
                'job_id': job_id,
                'success': True,
                'orphaned_fingerprints_removed': orphaned_count,
                'duration': duration
            }
            
            self.logger.info(
                "Fingerprint cleanup job completed",
                job_id=job_id,
                **result
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Fingerprint cleanup job failed",
                job_id=job_id,
                error=str(e)
            )
            return {
                'job_id': job_id,
                'success': False,
                'error': str(e),
                'duration': (datetime.utcnow() - start_time).total_seconds()
            }
    
    async def _get_recent_change_logs(self) -> list:
        """Get recent change logs for alerting."""
        try:
            # Get change logs from the last hour
            since_time = datetime.utcnow() - timedelta(hours=1)
            
            cursor = self.db_manager.database.change_logs.find({
                "detected_at": {"$gte": since_time}
            })
            
            logs = []
            async for doc in cursor:
                # Convert string URL back to HttpUrl
                if 'source_url' in doc and doc['source_url']:
                    from pydantic import HttpUrl
                    doc['source_url'] = HttpUrl(doc['source_url'])
                logs.append(doc)
            
            return logs
            
        except Exception as e:
            self.logger.error(
                "Failed to get recent change logs",
                error=str(e)
            )
            return []
    
    async def run_manual_change_detection(self, verbose: bool = True) -> Dict:
        """Run change detection manually (for testing/debugging)."""
        if verbose:
            self.logger.info("Running manual change detection")
        
        try:
            result = await self.change_detector.detect_changes(
                max_books=None,  # Process all books
                batch_size=self.config.batch_size,
                verbose=verbose
            )
            
            # Process alerts if changes detected
            if result.changes_detected > 0:
                change_logs = await self._get_recent_change_logs()
                await self.alert_manager.process_changes(change_logs)
            
            return {
                'success': result.success,
                'changes_detected': result.changes_detected,
                'new_books': result.new_books,
                'updated_books': result.updated_books,
                'removed_books': result.removed_books,
                'duration': result.detection_duration_seconds
            }
            
        except Exception as e:
            self.logger.error(
                "Manual change detection failed",
                error=str(e)
            )
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_scheduler_status(self) -> Dict:
        """Get current scheduler status."""
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
            
            return {
                'running': self.scheduler.running,
                'timezone': self.config.timezone,
                'jobs': jobs,
                'job_count': len(jobs)
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get scheduler status",
                error=str(e)
            )
            return {
                'running': False,
                'error': str(e)
            }
