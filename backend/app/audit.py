from .models import AuditLog, User


ACTION_LABELS = {
    "login": "تسجيل دخول ناجح",
    "login_failed": "محاولة تسجيل دخول فاشلة",
    "receipt": "استلام مخزني",
    "issue": "صرف مخزني",
    "transfer": "تحويل بين المخازن",
    "stocktake": "إكمال جرد",
    "adjustment": "تسوية جرد",
}


def add_audit_log(
    db,
    *,
    user: User | None,
    action: str,
    document_number: str | None = None,
    details: str = "",
    username: str | None = None,
    user_name: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user.id if user else None,
        username=username or (user.username if user else "unknown"),
        user_name=user_name or (user.display_name if user else "غير معروف"),
        action=action,
        action_label=ACTION_LABELS.get(action, action),
        document_number=document_number,
        details=details,
    )
    db.add(entry)
    return entry