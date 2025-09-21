#!/usr/bin/env python3
"""
Daemon Management Script - Start, stop, and check status of scheduler daemon.

Usage:
    python manage_daemon.py start    # Start the daemon
    python manage_daemon.py stop     # Stop the daemon
    python manage_daemon.py status   # Check daemon status
    python manage_daemon.py restart  # Restart the daemon
"""

import asyncio
import os
import signal
import sys
import subprocess
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utilities.config import config


class DaemonManager:
    """Manages the scheduler daemon process."""
    
    def __init__(self):
        self.daemon_script = project_root / "scheduler_daemon.py"
        self.pid_file = project_root / "scheduler_daemon.pid"
    
    def start(self):
        """Start the scheduler daemon."""
        if self.is_running():
            print("❌ Scheduler daemon is already running!")
            return False
        
        print("🚀 Starting scheduler daemon...")
        
        try:
            # Start daemon in background
            process = subprocess.Popen(
                [sys.executable, str(self.daemon_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=project_root
            )
            
            # Save PID
            with open(self.pid_file, 'w') as f:
                f.write(str(process.pid))
            
            # Wait a moment to check if it started successfully
            time.sleep(2)
            
            if process.poll() is None:  # Still running
                print("✅ Scheduler daemon started successfully!")
                print(f"📋 PID: {process.pid}")
                print(f"⏰ Schedule: Daily at {config.schedule_hour:02d}:{config.schedule_minute:02d} {config.timezone}")
                print(f"📁 Working Directory: {project_root}")
                return True
            else:
                print("❌ Failed to start scheduler daemon!")
                stdout, stderr = process.communicate()
                if stderr:
                    print(f"Error: {stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting daemon: {e}")
            return False
    
    def stop(self):
        """Stop the scheduler daemon."""
        if not self.is_running():
            print("❌ Scheduler daemon is not running!")
            return False
        
        try:
            # Read PID from file
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            print(f"🛑 Stopping scheduler daemon (PID: {pid})...")
            
            # Send SIGTERM for graceful shutdown
            os.kill(pid, signal.SIGTERM)
            
            # Wait for process to stop
            for i in range(10):  # Wait up to 10 seconds
                try:
                    os.kill(pid, 0)  # Check if process exists
                    time.sleep(1)
                except ProcessLookupError:
                    # Process has stopped
                    break
            else:
                # Force kill if still running
                print("⚠️  Force killing daemon...")
                os.kill(pid, signal.SIGKILL)
            
            # Remove PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
            
            print("✅ Scheduler daemon stopped successfully!")
            return True
            
        except FileNotFoundError:
            print("❌ PID file not found. Daemon may not be running.")
            return False
        except ProcessLookupError:
            print("❌ Process not found. Daemon may have already stopped.")
            if self.pid_file.exists():
                self.pid_file.unlink()
            return False
        except Exception as e:
            print(f"❌ Error stopping daemon: {e}")
            return False
    
    def restart(self):
        """Restart the scheduler daemon."""
        print("🔄 Restarting scheduler daemon...")
        self.stop()
        time.sleep(2)
        return self.start()
    
    def status(self):
        """Check daemon status."""
        if self.is_running():
            try:
                # Read PID from file
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                print("✅ Scheduler daemon is running!")
                print(f"📋 PID: {pid}")
                print(f"⏰ Schedule: Daily at {config.schedule_hour:02d}:{config.schedule_minute:02d} {config.timezone}")
                print(f"📁 Working Directory: {project_root}")
                
                # Show next run time (approximate)
                from datetime import datetime, timedelta
                now = datetime.now()
                next_run = now.replace(hour=config.schedule_hour, minute=config.schedule_minute, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                print(f"🕐 Next Run: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                
                return True
                
            except Exception as e:
                print(f"❌ Error reading daemon status: {e}")
                return False
        else:
            print("❌ Scheduler daemon is not running!")
            return False
    
    def is_running(self):
        """Check if daemon is running."""
        if not self.pid_file.exists():
            return False
        
        try:
            # Read PID from file
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process exists
            os.kill(pid, 0)
            return True
            
        except (FileNotFoundError, ProcessLookupError, ValueError):
            # Clean up stale PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
            return False
        except Exception:
            return False


def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python manage_daemon.py [start|stop|restart|status]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    manager = DaemonManager()
    
    if command == "start":
        success = manager.start()
        sys.exit(0 if success else 1)
    elif command == "stop":
        success = manager.stop()
        sys.exit(0 if success else 1)
    elif command == "restart":
        success = manager.restart()
        sys.exit(0 if success else 1)
    elif command == "status":
        success = manager.status()
        sys.exit(0 if success else 1)
    else:
        print(f"Unknown command: {command}")
        print("Usage: python manage_daemon.py [start|stop|restart|status]")
        sys.exit(1)


if __name__ == "__main__":
    main()
