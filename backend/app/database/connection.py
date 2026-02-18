"""
MedAssist AI - Database Connection Management
Handles Prisma client initialization and lifecycle
"""

from prisma import Prisma
import logging

logger = logging.getLogger(__name__)

# Global Prisma client instance
db = Prisma()


async def connect_db():
    """Connect to the database"""
    try:
        await db.connect()
        logger.info("Successfully connected to MongoDB database")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def disconnect_db():
    """Disconnect from the database"""
    try:
        await db.disconnect()
        logger.info("Successfully disconnected from database")
    except Exception as e:
        logger.error(f"Failed to disconnect from database: {e}")
        raise


def get_db() -> Prisma:
    """Get database instance for dependency injection"""
    return db
