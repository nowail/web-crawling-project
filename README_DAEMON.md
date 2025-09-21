# Scheduler Daemon

This daemon runs continuously in the background and automatically executes the scheduler at the time specified in your environment configuration.

## 🚀 Quick Start

### 1. Start the Daemon
```bash
python manage_daemon.py start
```

### 2. Check Status
```bash
python manage_daemon.py status
```

### 3. Stop the Daemon
```bash
python manage_daemon.py stop
```

### 4. Restart the Daemon
```bash
python manage_daemon.py restart
```

## ⚙️ Configuration

The daemon reads configuration from your environment variables:

```bash
# Set in your .env file or environment
SCHEDULE_HOUR=2        # Hour to run (24-hour format)
SCHEDULE_MINUTE=0      # Minute to run
TIMEZONE=UTC           # Timezone for scheduling
```

## 📋 How It Works

1. **Daemon Process**: Runs continuously in the background
2. **APScheduler**: Uses APScheduler to schedule jobs
3. **Automatic Execution**: Runs `scheduler_main.py --once` at the specified time
4. **Logging**: All activity is logged to `logs/crawler.log`
5. **PID Management**: Tracks the daemon process with a PID file

## 🔧 Manual Control

### Direct Daemon Execution
```bash
# Run daemon directly (foreground)
python scheduler_daemon.py

# Run daemon in background
nohup python scheduler_daemon.py > daemon.log 2>&1 &
```

### Check Running Processes
```bash
# Check if daemon is running
ps aux | grep scheduler_daemon.py | grep -v grep

# Check daemon logs
tail -f logs/crawler.log | grep scheduler_daemon
```

## 📊 Monitoring

### View Daemon Status
```bash
python manage_daemon.py status
```

### View Logs
```bash
# Real-time logs
tail -f logs/crawler.log

# Filter daemon logs
tail -f logs/crawler.log | grep "scheduler_daemon"
```

### Check Next Run Time
The daemon shows the next scheduled run time when you check status.

## 🛠️ Troubleshooting

### Daemon Won't Start
1. Check if already running: `python manage_daemon.py status`
2. Check logs: `tail -f logs/crawler.log`
3. Check MongoDB connection
4. Verify environment variables

### Daemon Won't Stop
1. Try graceful stop: `python manage_daemon.py stop`
2. Force kill: `pkill -f scheduler_daemon.py`
3. Remove PID file: `rm scheduler_daemon.pid`

### Scheduler Not Running at Scheduled Time
1. Check daemon status: `python manage_daemon.py status`
2. Verify timezone settings
3. Check logs for errors
4. Ensure MongoDB is running

## 🔄 System Integration

### macOS (LaunchAgent)
Create `~/Library/LaunchAgents/com.filerskeepers.scheduler.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.filerskeepers.scheduler</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/dev/Desktop/Assessments/FilersKeepersAssessment/scheduler_daemon.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/dev/Desktop/Assessments/FilersKeepersAssessment</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

### Linux (systemd)
```bash
# Copy service file
sudo cp scheduler-daemon.service /etc/systemd/system/

# Enable and start
sudo systemctl enable scheduler-daemon
sudo systemctl start scheduler-daemon

# Check status
sudo systemctl status scheduler-daemon
```

## 📝 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SCHEDULE_HOUR` | 2 | Hour to run scheduler (24-hour format) |
| `SCHEDULE_MINUTE` | 0 | Minute to run scheduler |
| `TIMEZONE` | UTC | Timezone for scheduling |
| `MONGODB_URL` | mongodb://localhost:27017 | MongoDB connection URL |
| `MONGODB_DATABASE` | filers_keepers | MongoDB database name |
| `LOG_LEVEL` | INFO | Logging level |
| `LOG_FILE` | logs/crawler.log | Log file path |

## 🎯 Benefits

- **Automatic**: Runs without manual intervention
- **Reliable**: Restarts automatically if it crashes
- **Configurable**: Easy to change schedule times
- **Monitored**: Full logging and status checking
- **Lightweight**: Minimal resource usage
- **Cross-platform**: Works on macOS, Linux, Windows
