"""
Dashboard service layer.

All aggregation and analytics logic lives here — views remain thin controllers.

Caching strategy (Redis cache-aside):
  - Every expensive aggregation is wrapped in a cache-aside pattern.
  - Cache TTL: 15 minutes (auto-expires even if invalidation is missed).
  - Cache is invalidated whenever a financial record is written, updated,
    or soft-deleted (see apps/records/services.py::invalidate_dashboard_cache).
  - Cache HIT  → Redis returns data, DB is never touched.
  - Cache MISS → DB is queried, result stored in Redis, returned to caller.
"""
from django.core.cache import cache
from django.db.models import Sum, Q, Count
from django.db.models.functions import TruncMonth
from decimal import Decimal

from apps.records.models import FinancialRecord

# ---------------------------------------------------------------------------
# Cache keys  — centralised so invalidation never misses a key
# ---------------------------------------------------------------------------
CACHE_KEY_SUMMARY         = 'dashboard:summary'
CACHE_KEY_CATEGORY_TOTALS = 'dashboard:category_totals'
CACHE_KEY_MONTHLY_TRENDS  = 'dashboard:monthly_trends'
CACHE_TTL                 = 60 * 15   # 15 minutes


def invalidate_dashboard_cache():
    """
    Clear all dashboard cache keys.
    Must be called whenever a FinancialRecord is created, updated, or deleted.
    """
    cache.delete_many([
        CACHE_KEY_SUMMARY,
        CACHE_KEY_CATEGORY_TOTALS,
        CACHE_KEY_MONTHLY_TRENDS,
    ])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _active_records():
    """Base queryset of non-deleted records."""
    return FinancialRecord.objects.filter(is_deleted=False)


# ---------------------------------------------------------------------------
# Core aggregations (cached)
# ---------------------------------------------------------------------------

def get_summary() -> dict:
    """
    Overall financial summary: total income, total expense, net balance.
    Result is cached for CACHE_TTL seconds.
    """
    cached = cache.get(CACHE_KEY_SUMMARY)
    if cached is not None:
        return cached

    result = _active_records().aggregate(
        total_income=Sum('amount', filter=Q(record_type='INCOME')),
        total_expense=Sum('amount', filter=Q(record_type='EXPENSE')),
        total_records=Count('id'),
    )

    total_income  = result['total_income']  or Decimal('0.00')
    total_expense = result['total_expense'] or Decimal('0.00')

    data = {
        'total_income':   total_income,
        'total_expense':  total_expense,
        'net_balance':    total_income - total_expense,
        'total_records':  result['total_records'],
    }
    cache.set(CACHE_KEY_SUMMARY, data, CACHE_TTL)
    return data


def get_category_totals() -> list:
    """
    Totals broken down by category and record type.
    Result is cached for CACHE_TTL seconds.
    Used by both the category-totals endpoint and pandas analytics.
    """
    cached = cache.get(CACHE_KEY_CATEGORY_TOTALS)
    if cached is not None:
        return cached

    results = list(
        _active_records()
        .values('category', 'record_type')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('category', 'record_type')
    )
    cache.set(CACHE_KEY_CATEGORY_TOTALS, results, CACHE_TTL)
    return results


def get_monthly_trends() -> list:
    """
    Month-wise income vs expense trends.
    Each row: {month, month_label, record_type, total, count}
    - month       : date (YYYY-MM-01) — for sorting/comparison
    - month_label : "YYYY-MM" string — ready for frontend display
    Result is cached for CACHE_TTL seconds.
    """
    cached = cache.get(CACHE_KEY_MONTHLY_TRENDS)
    if cached is not None:
        return cached

    results = (
        _active_records()
        .annotate(month=TruncMonth('date'))
        .values('month', 'record_type')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('month', 'record_type')
    )

    rows = [
        {
            **row,
            'month_label': row['month'].strftime('%Y-%m') if row['month'] else None,
        }
        for row in results
    ]
    cache.set(CACHE_KEY_MONTHLY_TRENDS, rows, CACHE_TTL)
    return rows


def get_recent_transactions(count: int = 10):
    """
    Most recent N transactions (not cached — cheap query, changes on every write).
    """
    return (
        _active_records()
        .select_related('created_by')
        .order_by('-date', '-created_at')[:count]
    )
