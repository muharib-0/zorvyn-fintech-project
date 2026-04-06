from django.contrib import admin
from .models import FinancialRecord


@admin.register(FinancialRecord)
class FinancialRecordAdmin(admin.ModelAdmin):
    """Admin registration for FinancialRecord."""
    list_display = ('id', 'record_type', 'category', 'amount', 'date',
                    'created_by', 'is_deleted', 'created_at')
    list_filter = ('record_type', 'category', 'is_deleted', 'date')
    search_fields = ('notes', 'category')
    date_hierarchy = 'date'
    ordering = ('-date', '-created_at')
    raw_id_fields = ('created_by',)
