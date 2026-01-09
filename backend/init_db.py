"""
Database initialization script for Phase 2
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import init_db
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


async def main():
    """Initialize database tables"""
    logger.info("database_init_start")
    
    try:
        await init_db()
        logger.info("database_init_success", 
                   message="All tables created successfully")
        print("\n✓ Database initialized successfully!")
        print("  - jobs table")
        print("  - candidates table")
        print("  - interviews table")
        print("  - interview_reports table")
        print("  - dimension_scores table")
        
    except Exception as e:
        logger.error("database_init_failed", error=str(e))
        print(f"\n✗ Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
