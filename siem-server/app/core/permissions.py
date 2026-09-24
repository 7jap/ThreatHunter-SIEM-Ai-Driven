class Permissions:
    # Users
    USERS_VIEW = "users.view"
    USERS_CREATE = "users.create"
    USERS_UPDATE = "users.update"
    USERS_DISABLE = "users.disable"
    USERS_DELETE = "users.delete"
    
    # Roles
    ROLES_VIEW = "roles.view"
    ROLES_CREATE = "roles.create"
    ROLES_UPDATE = "roles.update"
    ROLES_DELETE = "roles.delete"
    
    # Alerts
    ALERTS_VIEW = "alerts.view"
    ALERTS_SEARCH = "alerts.search"
    ALERTS_INVESTIGATE = "alerts.investigate"
    
    # Agents
    AGENTS_VIEW = "agents.view"
    AGENTS_APPROVE = "agents.approve"
    AGENTS_DISABLE = "agents.disable"
    AGENTS_REVOKE = "agents.revoke"
    
    # AI
    AI_CHAT = "ai.chat"
    AI_INVESTIGATE = "ai.investigate"
    AI_VIEW = "ai.view"
    AI_CONFIGURE = "ai.configure"
    AI_PROVIDERS_MANAGE = "ai.providers.manage"
    
    # System & Audit & Backup
    SYSTEM_VIEW = "system.view"
    SYSTEM_CONFIGURE = "system.configure"
    BACKUP_CREATE = "backup.create"
    BACKUP_RESTORE = "backup.restore"
    BACKUP_VIEW = "backup.view"
    AUDIT_VIEW = "audit.view"

    @classmethod
    def get_all(cls):
        return [value for key, value in cls.__dict__.items() if not key.startswith("__") and isinstance(value, str)]
