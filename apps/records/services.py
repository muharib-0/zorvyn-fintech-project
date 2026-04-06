"""
Financial records service layer.
Business logic for record operations lives here, not in views.
"""
from .models import FinancialRecord


def get_active_records():
    """Return queryset of all non-deleted financial records."""
    return FinancialRecord.objects.filter(is_deleted=False)


def soft_delete_record(record):
    """
    Soft-delete a financial record by setting is_deleted=True.
    Financial records are never hard-deleted.
    Always invalidates the dashboard cache.
    """
    record.is_deleted = True
    record.save(update_fields=['is_deleted', 'updated_at'])
    _bust_cache()
    return record


def create_record(validated_data, user):
    """Create a new financial record and invalidate dashboard cache."""
    record = FinancialRecord.objects.create(created_by=user, **validated_data)
    _bust_cache()
    return record


def update_record(record, validated_data):
    """Update a financial record and invalidate dashboard cache."""
    for attr, value in validated_data.items():
        setattr(record, attr, value)
    record.save()
    _bust_cache()
    return record


# ---------------------------------------------------------------------------
# Internal helper — imported lazily to avoid circular imports
# ---------------------------------------------------------------------------

def _bust_cache():
    """Invalidate all dashboard cache keys after any record write."""
    from apps.dashboard.services import invalidate_dashboard_cache
    invalidate_dashboard_cache()
