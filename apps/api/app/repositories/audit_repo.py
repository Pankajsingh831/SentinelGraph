from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog

class AuditRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log_action(self, actor_type: str, actor_id: str, action: str,
                         resource_type: str, resource_id: str, metadata: dict = None):
        """Write an audit_logs entry."""
        log_entry = AuditLog(
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_=metadata
        )
        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)
        return log_entry
