"""
Main entry point for Part 2: Scheduler and Change Detection.

This script starts the scheduler service for monitoring book changes.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import structlog
from utilities.logger import setup_logging
from utilities.config import config
from crawler.database import MongoDBManager
from scheduler.scheduler_service import SchedulerService
from scheduler.models import SchedulerConfig, AlertConfig


async def main():
    """Main function to start the scheduler service."""
    try:
        # Setup logging
        setup_logging(
            log_level=config.log_level,
            log_format=config.log_format,
            log_file=config.log_file,
            debug=config.debug
        )
        
        logger = structlog.get_logger(__name__)
        logger.info("Starting Part 2: Scheduler and Change Detection")
        
        # Create database manager
        db_manager = MongoDBManager(
            connection_url=config.mongodb_url,
            database_name=config.mongodb_database,
            collection_name=config.mongodb_collection
        )
        
        # Create alert configuration (logging only)
        alert_config = AlertConfig(
            enabled=getattr(config, 'alerting_enabled', True),
            log_enabled=getattr(config, 'log_enabled', True),
            min_severity_for_log=getattr(config, 'min_severity_for_log', 'low'),
            max_alerts_per_hour=getattr(config, 'max_alerts_per_hour', 10),
            alert_cooldown_minutes=getattr(config, 'alert_cooldown_minutes', 30)
        )
        
        # Create scheduler configuration
        scheduler_config = SchedulerConfig(
            schedule_hour=getattr(config, 'schedule_hour', 2),
            schedule_minute=getattr(config, 'schedule_minute', 0),
            timezone=getattr(config, 'timezone', 'UTC'),
            enable_change_detection=getattr(config, 'enable_change_detection', True),
            enable_new_book_detection=getattr(config, 'enable_new_book_detection', True),
            enable_removed_book_detection=getattr(config, 'enable_removed_book_detection', True),
            max_concurrent_books=getattr(config, 'max_concurrent_books', 50),
            batch_size=getattr(config, 'batch_size', 100),
            request_timeout=getattr(config, 'request_timeout', 30),
            enable_content_fingerprinting=getattr(config, 'enable_content_fingerprinting', True),
            fingerprint_fields=getattr(config, 'fingerprint_fields', [
                "name", "description", "category", "price_including_tax", 
                "availability", "rating", "number_of_reviews"
            ]),
            generate_daily_reports=getattr(config, 'generate_daily_reports', True),
            report_format=getattr(config, 'report_format', 'json'),
            report_retention_days=getattr(config, 'report_retention_days', 30),
            alert_config=alert_config
        )
        
        # Create and start scheduler service
        scheduler_service = SchedulerService(scheduler_config, db_manager)
        
        logger.info(
            "Scheduler service configured",
            schedule_hour=scheduler_config.schedule_hour,
            schedule_minute=scheduler_config.schedule_minute,
            timezone=scheduler_config.timezone,
            change_detection_enabled=scheduler_config.enable_change_detection,
            report_generation_enabled=scheduler_config.generate_daily_reports
        )
        
        # Check command line arguments
        test_mode = False
        run_once = False
        
        if len(sys.argv) > 1:
            if sys.argv[1] == '--test':
                test_mode = True
                logger.info("Running in TEST MODE - Jobs will run every 2 minutes")
                print("\n" + "="*60)
                print("🧪 TEST MODE ENABLED")
                print("="*60)
                print("✅ Change Detection: Every 2 minutes")
                print("✅ Report Generation: Every 4 minutes") 
                print("✅ Report Cleanup: Every 10 minutes")
                print("="*60)
            elif sys.argv[1] == '--once':
                run_once = True
                logger.info("Running in RUN ONCE MODE - Single execution")
                print("\n" + "="*60)
                print("🔄 RUN ONCE MODE ENABLED")
                print("="*60)
                print("✅ Change Detection: Single run")
                print("✅ Report Generation: Single run") 
                print("✅ Exit after completion")
                print("="*60)
            else:
                print(f"Unknown argument: {sys.argv[1]}")
                print("Usage: python scheduler_main.py [--test|--once|--daemon]")
                sys.exit(1)
        else:
            logger.info("Running in DAEMON MODE - Jobs will run daily at specified time")
            print("\n" + "="*60)
            print("🏭 DAEMON MODE ENABLED")
            print("="*60)
            print(f"✅ Change Detection: Daily at {scheduler_config.schedule_hour:02d}:{scheduler_config.schedule_minute:02d} {scheduler_config.timezone}")
            print(f"✅ Report Generation: Daily at {scheduler_config.schedule_hour:02d}:{scheduler_config.schedule_minute + 5:02d} {scheduler_config.timezone}") 
            print(f"✅ Report Cleanup: Daily at 01:00 {scheduler_config.timezone}")
            print("✅ Scheduler runs continuously as daemon")
            print("="*60)
        
        # Start the service
        await scheduler_service.start(test_mode=test_mode, run_once=run_once)
        
    except KeyboardInterrupt:
        try:
            logger.info("Received keyboard interrupt, shutting down...")
        except NameError:
            print("Received keyboard interrupt, shutting down...")
    except Exception as e:
        try:
            logger.error("Failed to start scheduler service", error=str(e))
        except NameError:
            print(f"Failed to start scheduler service: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

