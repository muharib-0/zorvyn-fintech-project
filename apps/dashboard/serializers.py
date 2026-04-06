"""
Dashboard specific serializers, e.g., for recent transactions.
"""
from rest_framework import serializers
from apps.records.models import FinancialRecord


class RecentRecordLimitedSerializer(serializers.ModelSerializer):
    """
    Limited view of a recent financial record.
    Used for VIEWER role responses.
    """
    class Meta:
        model = FinancialRecord
        fields = ['record_type', 'category', 'amount', 'date']


class RecentRecordFullSerializer(serializers.ModelSerializer):
    """
    Full view of a recent financial record with notes and created_by.
    Used for ANALYST and ADMIN role responses.
    """
    created_by = serializers.StringRelatedField()

    class Meta:
        model = FinancialRecord
        fields = ['id', 'record_type', 'category', 'amount', 'date', 'notes', 'created_by']
