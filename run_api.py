#!/usr/bin/env python3
"""
Script to run the FilersKeepers API server.
"""

import uvicorn
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api.config import config


def main():
    """Run the API server."""
    print("🚀 Starting FilersKeepers API Server")
    print(f"📡 Host: {config.host}")
    print(f"🔌 Port: {config.port}")
    print(f"🌐 Debug: {config.debug}")
    print(f"📚 Database: {config.mongodb_database}")
    print("=" * 50)
    
    uvicorn.run(
        "api.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level=config.log_level.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()
