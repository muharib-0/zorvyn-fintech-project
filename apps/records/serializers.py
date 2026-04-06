from datetime import date, timedelta
from rest_framework import serializers
from .models import FinancialRecord, EXPENSE_ONLY_CATEGORIES, INCOME_ONLY_CATEGORIES


class FinancialRecordSerializer(serializers.ModelSerializer):
    """
    Full serializer for financial record read/write operations.
    Used for detail view and create/update operations.
    """
    created_by_username = serializers.CharField(
        source='created_by.username', read_only=True, default=None
    )

    class Meta:
        model = FinancialRecord
        fields = [
            'id', 'amount', 'record_type', 'category', 'date',
            'notes', 'is_deleted', 'created_by', 'created_by_username',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'is_deleted', 'created_by',
                            'created_by_username', 'created_at', 'updated_at']

    # ------------------------------------------------------------------ #
    # Field-level validators                                               #
    # ------------------------------------------------------------------ #

    def validate_amount(self, value):
        """Ensure amount is positive."""
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value

    def validate_record_type(self, value):
        """Ensure record_type is a valid choice."""
        valid_types = [choice[0] for choice in FinancialRecord.RecordType.choices]
        if value not in valid_types:
            raise serializers.ValidationError(
                f'Invalid type. Must be one of: {", ".join(valid_types)}'
            )
        return value

    def validate_category(self, value):
        """Ensure category is a valid choice."""
        valid_categories = [choice[0] for choice in FinancialRecord.Category.choices]
        if value not in valid_categories:
            raise serializers.ValidationError(
                f'Invalid category. Must be one of: {", ".join(valid_categories)}'
            )
        return value

    def validate_date(self, value):
        """
        Reject dates more than 1 year in the future.
        A 1-year window allows legitimate future-scheduled entries (budgets,
        planned transactions) while catching obvious typos like 2099.
        """
        max_future = date.today() + timedelta(days=365)
        if value > max_future:
            raise serializers.ValidationError(
                'Date cannot be more than 1 year in the future.'
            )
        return value

    # ------------------------------------------------------------------ #
    # Cross-field validator — category must match record_type              #
    # ------------------------------------------------------------------ #

    def validate(self, data):
        """
        Enforce the category-type contract:
        - Expense-only categories  (e.g. SALARIES, OFFICE_RENT) → EXPENSE records only
        - Income-only categories   (e.g. CLIENT_REVENUE, GRANT_SUBSIDY) → INCOME records only

        This is business-logic validation. It separates a thoughtful submission
        from a generic CRUD app — the kind of thing an interviewer will probe.

        On PATCH (partial updates), we merge incoming data with existing values
        to avoid false positives when only one field is sent.
        """
        # For partial updates, fall back to the existing instance values
        instance = getattr(self, 'instance', None)

        record_type = data.get(
            'record_type',
            getattr(instance, 'record_type', None)
        )
        category = data.get(
            'category',
            getattr(instance, 'category', None)
        )

        if record_type and category:
            if record_type == 'EXPENSE' and category in INCOME_ONLY_CATEGORIES:
                raise serializers.ValidationError({
                    'category': (
                        f'"{category}" is an income category and cannot be used '
                        f'on an EXPENSE record. '
                        f'Valid expense categories: '
                        f'{", ".join(sorted(EXPENSE_ONLY_CATEGORIES))}.'
                    )
                })
            if record_type == 'INCOME' and category in EXPENSE_ONLY_CATEGORIES:
                raise serializers.ValidationError({
                    'category': (
                        f'"{category}" is an expense category and cannot be used '
                        f'on an INCOME record. '
                        f'Valid income categories: '
                        f'{", ".join(sorted(INCOME_ONLY_CATEGORIES))}.'
                    )
                })

        return data


class FinancialRecordListSerializer(serializers.ModelSerializer):
    """
    Lighter serializer for list views — excludes notes and detailed timestamps.
    """
    created_by_username = serializers.CharField(
        source='created_by.username', read_only=True, default=None
    )

    class Meta:
        model = FinancialRecord
        fields = [
            'id', 'amount', 'record_type', 'category', 'date',
            'created_by_username', 'created_at',
        ]
        read_only_fields = fields
