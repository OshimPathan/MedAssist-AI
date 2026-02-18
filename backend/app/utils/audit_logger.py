"""
MedAssist AI - Audit Logger
Compliance-ready audit logging for all system actions
"""

import logging
from datetime import datetime
from typing import Optional
from app.database.connection import get_db

logger = logging.getLogger(__name__)


async def log_action(
    action: str,
    resource: str,
    user_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
):
    """Log an auditable action to the database"""
    try:
        db = get_db()
        await db.auditlog.create(
            data={
                "action": action,
                "resource": resource,
                "userId": user_id,
                "details": details if details else {},
                "ipAddress": ip_address,
            }
        )
        logger.info(f"Audit: {action} on {resource} by {user_id or 'system'}")
    except Exception as e:
        # Never let audit logging failures break the main flow
        logger.error(f"Audit log failed: {e}")
