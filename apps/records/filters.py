"""
Django-filter filterset for financial records.
Supports filtering by record_type, category, and date range.
"""
import django_filters
from .models import FinancialRecord


class FinancialRecordFilter(django_filters.FilterSet):
    """
    FilterSet for FinancialRecord.

    Filters:
    - record_type: exact match (INCOME or EXPENSE)
    - category: exact match (SALARY, RENT, etc.)
    - date_after: records on or after this date
    - date_before: records on or before this date
    """
    date_after = django_filters.DateFilter(
        field_name='date',
        lookup_expr='gte',
        label='Date from (YYYY-MM-DD)',
    )
    date_before = django_filters.DateFilter(
        field_name='date',
        lookup_expr='lte',
        label='Date to (YYYY-MM-DD)',
    )

    class Meta:
        model = FinancialRecord
        fields = ['record_type', 'category']
