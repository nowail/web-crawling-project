#!/usr/bin/env python3
"""
Fingerprint Management Utility

This script provides utilities to manage fingerprints:
- List all fingerprints
- Find fingerprint for a specific book
- Clean up orphaned fingerprints
- Show fingerprint statistics
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
from scheduler.fingerprinting import FingerprintManager


async def list_all_fingerprints():
    """List all fingerprints in the database."""
    print("\n" + "="*80)
    print("📋 ALL FINGERPRINTS")
    print("="*80)
    
    try:
        db_manager = MongoDBManager(
            connection_url=config.mongodb_url,
            database_name=config.mongodb_database,
            collection_name=config.mongodb_collection
        )
        
        await db_manager.connect()
        fingerprint_manager = FingerprintManager(db_manager)
        
        fingerprints = await fingerprint_manager.get_all_fingerprints()
        
        if not fingerprints:
            print("❌ No fingerprints found in database")
            return
        
        print(f"✅ Found {len(fingerprints)} fingerprints:")
        print()
        
        for i, fingerprint in enumerate(fingerprints, 1):
            print(f"{i:3d}. Book ID: {fingerprint.book_id}")
            print(f"     URL: {fingerprint.source_url}")
            print(f"     Created: {fingerprint.created_at}")
            print(f"     Updated: {fingerprint.updated_at}")
            print(f"     Content Hash: {fingerprint.content_hash[:16]}...")
            print()
        
    except Exception as e:
        print(f"❌ Error listing fingerprints: {e}")
    finally:
        if 'db_manager' in locals():
            await db_manager.disconnect()


async def find_fingerprint_by_url(source_url: str):
    """Find fingerprint for a specific book URL."""
    print(f"\n🔍 SEARCHING FOR FINGERPRINT")
    print(f"URL: {source_url}")
    print("="*80)
    
    try:
        db_manager = MongoDBManager(
            connection_url=config.mongodb_url,
            database_name=config.mongodb_database,
            collection_name=config.mongodb_collection
        )
        
        await db_manager.connect()
        fingerprint_manager = FingerprintManager(db_manager)
        
        # Generate book_id from URL
        import hashlib
        book_id = f"book_{hashlib.md5(source_url.encode('utf-8')).hexdigest()}"
        
        print(f"Generated Book ID: {book_id}")
        
        # Find fingerprint
        fingerprint = await fingerprint_manager.get_fingerprint(book_id)
        
        if fingerprint:
            print("✅ FINGERPRINT FOUND:")
            print(f"   Book ID: {fingerprint.book_id}")
            print(f"   Source URL: {fingerprint.source_url}")
            print(f"   Created: {fingerprint.created_at}")
            print(f"   Updated: {fingerprint.updated_at}")
            print(f"   Content Hash: {fingerprint.content_hash}")
            print(f"   Price Hash: {fingerprint.price_hash}")
            print(f"   Availability Hash: {fingerprint.availability_hash}")
            print(f"   Metadata Hash: {fingerprint.metadata_hash}")
        else:
            print("❌ No fingerprint found for this URL")
            
            # Check if book exists
            book = await db_manager.get_book_by_url(source_url)
            if book:
                print("ℹ️  Book exists in database but has no fingerprint")
            else:
                print("ℹ️  Book not found in database")
        
    except Exception as e:
        print(f"❌ Error finding fingerprint: {e}")
    finally:
        if 'db_manager' in locals():
            await db_manager.disconnect()


async def cleanup_orphaned_fingerprints():
    """Clean up orphaned fingerprints."""
    print("\n🧹 CLEANING UP ORPHANED FINGERPRINTS")
    print("="*80)
    
    try:
        db_manager = MongoDBManager(
            connection_url=config.mongodb_url,
            database_name=config.mongodb_database,
            collection_name=config.mongodb_collection
        )
        
        await db_manager.connect()
        fingerprint_manager = FingerprintManager(db_manager)
        
        # Get initial count
        fingerprints = await fingerprint_manager.get_all_fingerprints()
        initial_count = len(fingerprints)
        
        print(f"📊 Initial fingerprint count: {initial_count}")
        
        # Cleanup orphaned fingerprints
        orphaned_count = await fingerprint_manager.cleanup_orphaned_fingerprints()
        
        # Get final count
        fingerprints = await fingerprint_manager.get_all_fingerprints()
        final_count = len(fingerprints)
        
        print(f"🗑️  Orphaned fingerprints removed: {orphaned_count}")
        print(f"📊 Final fingerprint count: {final_count}")
        
        if orphaned_count > 0:
            print("✅ Cleanup completed successfully")
        else:
            print("ℹ️  No orphaned fingerprints found")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
    finally:
        if 'db_manager' in locals():
            await db_manager.disconnect()


async def show_statistics():
    """Show fingerprint and book statistics."""
    print("\n📊 FINGERPRINT STATISTICS")
    print("="*80)
    
    try:
        db_manager = MongoDBManager(
            connection_url=config.mongodb_url,
            database_name=config.mongodb_database,
            collection_name=config.mongodb_collection
        )
        
        await db_manager.connect()
        fingerprint_manager = FingerprintManager(db_manager)
        
        # Get counts
        fingerprints = await fingerprint_manager.get_all_fingerprints()
        fingerprint_count = len(fingerprints)
        
        book_count = await db_manager.collection.count_documents({})
        
        # Check for orphaned fingerprints
        orphaned_count = 0
        for fingerprint in fingerprints:
            book_exists = await db_manager.collection.find_one({
                "source_url": str(fingerprint.source_url)
            })
            if not book_exists:
                orphaned_count += 1
        
        print(f"📚 Total Books: {book_count}")
        print(f"🔍 Total Fingerprints: {fingerprint_count}")
        print(f"🔗 Books with Fingerprints: {fingerprint_count - orphaned_count}")
        print(f"🗑️  Orphaned Fingerprints: {orphaned_count}")
        print(f"📈 Coverage: {((fingerprint_count - orphaned_count) / book_count * 100):.1f}%" if book_count > 0 else "📈 Coverage: 0%")
        
        if orphaned_count > 0:
            print(f"\n⚠️  Warning: {orphaned_count} orphaned fingerprints found!")
            print("   Run cleanup to remove them.")
        
    except Exception as e:
        print(f"❌ Error getting statistics: {e}")
    finally:
        if 'db_manager' in locals():
            await db_manager.disconnect()


async def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python manage_fingerprints.py [list|find|cleanup|stats] [url]")
        print()
        print("Commands:")
        print("  list     - List all fingerprints")
        print("  find     - Find fingerprint for a specific URL")
        print("  cleanup  - Clean up orphaned fingerprints")
        print("  stats    - Show fingerprint statistics")
        print()
        print("Examples:")
        print("  python manage_fingerprints.py list")
        print("  python manage_fingerprints.py find 'https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html'")
        print("  python manage_fingerprints.py cleanup")
        print("  python manage_fingerprints.py stats")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    # Setup logging
    setup_logging(
        log_level=config.log_level,
        log_format=config.log_format,
        log_file=config.log_file,
        debug=config.debug
    )
    
    if command == "list":
        await list_all_fingerprints()
    elif command == "find":
        if len(sys.argv) < 3:
            print("❌ Error: URL required for find command")
            print("Usage: python manage_fingerprints.py find <url>")
            sys.exit(1)
        await find_fingerprint_by_url(sys.argv[2])
    elif command == "cleanup":
        await cleanup_orphaned_fingerprints()
    elif command == "stats":
        await show_statistics()
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: list, find, cleanup, stats")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
