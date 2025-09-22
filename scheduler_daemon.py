#!/usr/bin/env python3
"""
Scheduler Daemon - Runs scheduler_main.py at scheduled times using APScheduler.

This daemon runs continuously in the background and executes the scheduler
at the time specified in your environment configuration (SCHEDULE_HOUR, SCHEDULE_MINUTE).
"""

import asyncio
import os
import signal
import sys
import subprocess
from datetime import datetime
from pathlib import Path

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utilities.logger import setup_logging
from utilities.config import config

logger = logging.getLogger(__name__)


class SchedulerDaemon:
    """Daemon that schedules and runs scheduler_main.py at specified times."""
    
    def __init__(self):
        """Initialize the scheduler daemon."""
        self.scheduler = AsyncIOScheduler(timezone=config.timezone)
        self.running = False
        self.logger = logger
        
        # Setup signal handlers for graceful shutdown
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
            duration = event.retval.get('duration', 0) if event.retval else 0
            self.logger.info(f"Scheduled job executed successfully - job_id: {event.job_id}, duration: {duration}")
        
        def job_error_listener(event):
            self.logger.error(f"Scheduled job execution failed - job_id: {event.job_id}, error: {str(event.exception)}")
        
        self.scheduler.add_listener(job_executed_listener, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(job_error_listener, EVENT_JOB_ERROR)
    
    async def start(self) -> None:
        """Start the scheduler daemon."""
        try:
            self.logger.info("Starting Scheduler Daemon")
            
            # Add the scheduled job
            await self._add_scheduled_job()
            
            # Start the scheduler
            self.scheduler.start()
            self.running = True
            
            self.logger.info(f"Scheduler Daemon started successfully - schedule: {config.schedule_hour:02d}:{config.schedule_minute:02d}, timezone: {config.timezone}, next_run: {self._get_next_run_time()}")
            
            print("\n" + "="*70)
            print("🚀 SCHEDULER DAEMON STARTED")
            print("="*70)
            print(f"⏰ Schedule: Daily at {config.schedule_hour:02d}:{config.schedule_minute:02d} {config.timezone}")
            print(f"🔄 Next Run: {self._get_next_run_time()}")
            print(f"📁 Working Directory: {project_root}")
            print(f"🐍 Python Command: {sys.executable}")
            print("="*70)
            print("💡 Press Ctrl+C to stop the daemon")
            print("="*70)
            
            # Keep the daemon running
            try:
                while self.running:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt, shutting down...")
                self.stop()
                
        except Exception as e:
            self.logger.error(f"Failed to start scheduler daemon - error: {str(e)}")
            raise
    
    async def _add_scheduled_job(self) -> None:
        """Add the scheduled job to run scheduler_main.py."""
        try:
            self.scheduler.add_job(
                func=self._run_scheduler_job,
                trigger=CronTrigger(
                    hour=config.schedule_hour,
                    minute=config.schedule_minute,
                    timezone=config.timezone
                ),
                id='daily_scheduler_run',
                name='Daily Scheduler Execution',
                max_instances=1,
                replace_existing=True
            )
            
            self.logger.info(f"Added scheduled job - hour: {config.schedule_hour}, minute: {config.schedule_minute}, timezone: {config.timezone}")
            
        except Exception as e:
            self.logger.error(f"Failed to add scheduled job - error: {str(e)}")
            raise
    
    async def _run_scheduler_job(self) -> dict:
        """Execute the scheduler_main.py script."""
        start_time = datetime.utcnow()
        job_id = f"scheduler_run_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        self.logger.info(f"Starting scheduled scheduler execution - job_id: {job_id}")
        
        try:
            # Change to project directory
            os.chdir(project_root)
            
            # Run scheduler_main.py with --once flag
            cmd = [sys.executable, "scheduler_main.py", "--once"]
            
            self.logger.info(f"Executing scheduler command: {' '.join(cmd)}, working_directory: {project_root}")
            
            # Execute the command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_root
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=3600  # 1 hour timeout
                )
            except asyncio.TimeoutError:
                self.logger.error("Scheduler execution timed out after 1 hour")
                process.kill()
                await process.wait()
                raise Exception("Scheduler execution timed out")
            
            # Check return code
            if process.returncode == 0:
                self.logger.info(f"Scheduler execution completed successfully - job_id: {job_id}, return_code: {process.returncode}")
                
                # Log stdout if available
                if stdout:
                    self.logger.debug(f"Scheduler stdout: {stdout.decode().strip()}")
                
                result = {
                    'job_id': job_id,
                    'success': True,
                    'return_code': process.returncode,
                    'duration': (datetime.utcnow() - start_time).total_seconds()
                }
                
            else:
                stderr_output = stderr.decode().strip() if stderr else None
                self.logger.error(f"Scheduler execution failed - job_id: {job_id}, return_code: {process.returncode}, stderr: {stderr_output}")
                
                result = {
                    'job_id': job_id,
                    'success': False,
                    'return_code': process.returncode,
                    'error': stderr.decode().strip() if stderr else "Unknown error",
                    'duration': (datetime.utcnow() - start_time).total_seconds()
                }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Scheduler execution failed with exception - job_id: {job_id}, error: {str(e)}")
            return {
                'job_id': job_id,
                'success': False,
                'error': str(e),
                'duration': (datetime.utcnow() - start_time).total_seconds()
            }
    
    def _get_next_run_time(self) -> str:
        """Get the next scheduled run time."""
        try:
            jobs = self.scheduler.get_jobs()
            if jobs:
                next_run = jobs[0].next_run_time
                if next_run:
                    return next_run.strftime("%Y-%m-%d %H:%M:%S %Z")
            return "Not scheduled"
        except Exception:
            return "Unknown"
    
    def stop(self) -> None:
        """Stop the scheduler daemon."""
        try:
            self.logger.info("Stopping Scheduler Daemon")
            
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
            
            self.running = False
            self.logger.info("Scheduler Daemon stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping scheduler daemon - error: {str(e)}")
    
    def get_status(self) -> dict:
        """Get daemon status information."""
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
                'running': self.running and self.scheduler.running,
                'timezone': config.timezone,
                'schedule_hour': config.schedule_hour,
                'schedule_minute': config.schedule_minute,
                'jobs': jobs,
                'job_count': len(jobs),
                'next_run': self._get_next_run_time()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get daemon status - error: {str(e)}")
            return {
                'running': False,
                'error': str(e)
            }


async def main():
    """Main function to start the scheduler daemon."""
    try:
        # Setup logging
        setup_logging(
            log_level=config.log_level,
            log_format=config.log_format,
            log_file=config.log_file,
            debug=config.debug
        )
        
        logger = logging.getLogger(__name__)
        logger.info("Starting Scheduler Daemon")
        
        # Create and start daemon
        daemon = SchedulerDaemon()
        await daemon.start()
        
    except KeyboardInterrupt:
        try:
            logger.info("Received keyboard interrupt, shutting down...")
        except NameError:
            print("Received keyboard interrupt, shutting down...")
    except Exception as e:
        try:
            logger.error(f"Failed to start scheduler daemon - error: {str(e)}")
        except NameError:
            print(f"Failed to start scheduler daemon: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
