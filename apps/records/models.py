from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal


# ---------------------------------------------------------------------------
# Category membership sets — used by the serializer for cross-validation
# and by the analytics module for cost-centre grouping.
# Defined here to keep the model as the single source of truth.
# ---------------------------------------------------------------------------

EXPENSE_ONLY_CATEGORIES = frozenset([
    'OFFICE_RENT', 'SALARIES', 'CONTRACTOR_FEES', 'EMPLOYEE_BENEFITS',
    'RECRUITMENT', 'SOFTWARE_TOOLS', 'AI_TOOLS', 'CLOUD_INFRASTRUCTURE',
    'EQUIPMENT_HARDWARE', 'UTILITIES_INTERNET', 'ADVERTISING_MARKETING',
    'FOOD_BEVERAGES', 'TRAVEL_TRANSPORT', 'LEGAL_COMPLIANCE', 'OTHER_EXPENSE',
])

INCOME_ONLY_CATEGORIES = frozenset([
    'CLIENT_REVENUE', 'PRODUCT_SALES', 'SUBSCRIPTION_REVENUE', 'CONSULTING',
    'INVESTMENT_FUNDING', 'INTEREST_INCOME', 'GRANT_SUBSIDY', 'OTHER_INCOME',
])


class FinancialRecord(models.Model):
    """
    Financial record model representing a single company-level
    income or expense transaction.

    Key design decisions:
    - DecimalField for amount (avoids float precision errors with money)
    - Soft delete via is_deleted flag (financial records are never hard deleted)
    - created_by uses SET_NULL so records survive user deletion
    - Organizational categories with expense/income separation enforced
      at the serializer level (not DB level — keeps the model simple)
    - Indexes on hot filter/dashboard columns for aggregation performance
    """

    class RecordType(models.TextChoices):
        INCOME  = 'INCOME',  'Income'
        EXPENSE = 'EXPENSE', 'Expense'

    class Category(models.TextChoices):
        # -- Expense-only --------------------------------------------------
        OFFICE_RENT            = 'OFFICE_RENT',            'Office Rent'
        SALARIES               = 'SALARIES',               'Salaries'
        CONTRACTOR_FEES        = 'CONTRACTOR_FEES',        'Contractor Fees'
        EMPLOYEE_BENEFITS      = 'EMPLOYEE_BENEFITS',      'Employee Benefits'
        RECRUITMENT            = 'RECRUITMENT',            'Recruitment'
        SOFTWARE_TOOLS         = 'SOFTWARE_TOOLS',         'Software & Tools'
        AI_TOOLS               = 'AI_TOOLS',               'AI Tools'
        CLOUD_INFRASTRUCTURE   = 'CLOUD_INFRASTRUCTURE',   'Cloud Infrastructure'
        EQUIPMENT_HARDWARE     = 'EQUIPMENT_HARDWARE',     'Equipment & Hardware'
        UTILITIES_INTERNET     = 'UTILITIES_INTERNET',     'Utilities & Internet'
        ADVERTISING_MARKETING  = 'ADVERTISING_MARKETING',  'Advertising & Marketing'
        FOOD_BEVERAGES         = 'FOOD_BEVERAGES',         'Food & Beverages'
        TRAVEL_TRANSPORT       = 'TRAVEL_TRANSPORT',       'Travel & Transport'
        LEGAL_COMPLIANCE       = 'LEGAL_COMPLIANCE',       'Legal & Compliance'
        OTHER_EXPENSE          = 'OTHER_EXPENSE',          'Other Expense'
        # -- Income-only ---------------------------------------------------
        CLIENT_REVENUE         = 'CLIENT_REVENUE',         'Client Revenue'
        PRODUCT_SALES          = 'PRODUCT_SALES',          'Product Sales'
        SUBSCRIPTION_REVENUE   = 'SUBSCRIPTION_REVENUE',   'Subscription Revenue'
        CONSULTING             = 'CONSULTING',             'Consulting'
        INVESTMENT_FUNDING     = 'INVESTMENT_FUNDING',     'Investment & Funding'
        INTEREST_INCOME        = 'INTEREST_INCOME',        'Interest Income'
        GRANT_SUBSIDY          = 'GRANT_SUBSIDY',          'Grant & Subsidy'
        OTHER_INCOME           = 'OTHER_INCOME',           'Other Income'

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Transaction amount. Must be greater than 0.',
    )
    record_type = models.CharField(
        max_length=7,
        choices=RecordType.choices,
        help_text='Whether this is an income or expense record.',
    )
    category = models.CharField(
        max_length=25,          # longest key: ADVERTISING_MARKETING = 21 chars
        choices=Category.choices,
        help_text='Category of the financial record.',
    )
    date = models.DateField(
        help_text='Date of the transaction.',
    )
    notes = models.TextField(
        blank=True,
        default='',
        help_text='Optional notes about the transaction.',
    )
    is_deleted = models.BooleanField(
        default=False,
        help_text='Soft delete flag. True = record is preserved but hidden.',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='financial_records',
        help_text='User who created this record. Preserved even if user is deleted.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'financial_records'
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['record_type'], name='idx_record_type'),
            models.Index(fields=['category'],    name='idx_category'),
            models.Index(fields=['date'],         name='idx_date'),
            models.Index(fields=['is_deleted'],   name='idx_is_deleted'),
        ]

    def __str__(self):
        return f'{self.record_type} - {self.get_category_display()}: {self.amount} ({self.date})'
