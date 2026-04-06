"""
Dashboard views — all endpoints for the finance dashboard.

Endpoints:
  Viewer+ (all authenticated users):
    GET /api/dashboard/summary/
    GET /api/dashboard/category-totals/
    GET /api/dashboard/recent/
    GET /api/dashboard/revenue-breakdown/
    GET /api/dashboard/cost-center-breakdown/
    GET /api/dashboard/people-cost-ratio/

  Analyst+ (ANALYST and ADMIN roles):
    GET /api/dashboard/monthly-trends/
    GET /api/dashboard/burn-rate/
    GET /api/dashboard/runway/
    GET /api/dashboard/mom-change/
"""
from rest_framework import serializers as drf_serializers
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter

from . import services, analytics
from apps.users.permissions import IsViewerOrAbove, IsAnalystOrAbove
from apps.records.serializers import FinancialRecordListSerializer


# ===========================================================================
# Viewer+ endpoints
# ===========================================================================

class SummaryView(APIView):
    """
    GET /api/dashboard/summary/
    Total income, total expense, net balance, total record count.
    Accessible by Viewer+. Result is Redis-cached.
    """
    permission_classes = [IsAuthenticated, IsViewerOrAbove]

    @extend_schema(
        tags=['Dashboard'],
        summary='Financial summary',
        description='Aggregated totals: income, expense, net balance, record count. Redis-cached.',
        responses={
            200: inline_serializer(
                name='DashboardSummary',
                fields={
                    'total_income':  drf_serializers.DecimalField(max_digits=14, decimal_places=2),
                    'total_expense': drf_serializers.DecimalField(max_digits=14, decimal_places=2),
                    'net_balance':   drf_serializers.DecimalField(max_digits=14, decimal_places=2),
                    'total_records': drf_serializers.IntegerField(),
                },
            ),
        },
    )
    def get(self, request):
        return Response(services.get_summary())


class CategoryTotalsView(APIView):
    """
    GET /api/dashboard/category-totals/
    Raw per-category, per-type totals.
    Accessible by Analyst+. Result is Redis-cached.
    """
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]

    @extend_schema(
        tags=['Dashboard'],
        summary='Category breakdown',
        description='Financial totals grouped by category and record type (INCOME/EXPENSE). Requires Analyst or Admin role. Redis-cached.',
        responses={
            200: inline_serializer(
                name='CategoryTotal',
                fields={
                    'category':    drf_serializers.CharField(),
                    'record_type': drf_serializers.CharField(),
                    'total':       drf_serializers.DecimalField(max_digits=14, decimal_places=2),
                    'count':       drf_serializers.IntegerField(),
                },
                many=True,
            ),
        },
    )
    def get(self, request):
        return Response(services.get_category_totals())


class RecentTransactionsView(APIView):
    """
    GET /api/dashboard/recent/
    Most recent N transactions. Default 10, max 50.
    Returns limited fields for Viewer, full fields for Analyst+.
    Not cached — cheap query, always fresh.
    Accessible by Viewer+.
    """
    permission_classes = [IsAuthenticated, IsViewerOrAbove]

    @extend_schema(
        tags=['Dashboard'],
        summary='Recent transactions',
        description='Last N financial transactions. Returns limited data for VIEWER, full data for ANALYST/ADMIN.',
        parameters=[
            OpenApiParameter(
                name='count', type=int, location=OpenApiParameter.QUERY,
                description='Number of recent transactions to return (default 10, max 50)',
                required=False,
            ),
        ],
    )
    def get(self, request):
        from .serializers import RecentRecordLimitedSerializer, RecentRecordFullSerializer
        count = request.query_params.get('count', 10)
        try:
            count = min(int(count), 50)
        except (ValueError, TypeError):
            count = 10
        records = services.get_recent_transactions(count=count)
        
        if request.user.role == 'VIEWER':
            serializer = RecentRecordLimitedSerializer(records, many=True)
        else:
            serializer = RecentRecordFullSerializer(records, many=True)
            
        return Response({'transactions': serializer.data})


class RevenuBreakdownView(APIView):
    """
    GET /api/dashboard/revenue-breakdown/
    Income categories with % of total revenue.
    Accessible by Viewer+.
    """
    permission_classes = [IsAuthenticated, IsViewerOrAbove]

    @extend_schema(
        tags=['Dashboard'],
        summary='Revenue breakdown',
        description=(
            'Income categories as a percentage of total revenue. '
            'Useful for understanding which revenue streams dominate. '
            'Powered by pandas on Redis-cached ORM data.'
        ),
        responses={
            200: inline_serializer(
                name='RevenueBreakdownRow',
                fields={
                    'category':            drf_serializers.CharField(),
                    'total':               drf_serializers.DecimalField(max_digits=14, decimal_places=2),
                    'count':               drf_serializers.IntegerField(),
                    'pct_of_total_income': drf_serializers.FloatField(),
                },
                many=True,
            ),
        },
    )
    def get(self, request):
        category_rows = services.get_category_totals()
        return Response(analytics.compute_revenue_breakdown(category_rows))


class CostCenterBreakdownView(APIView):
    """
    GET /api/dashboard/cost-center-breakdown/
    Expense categories rolled up into executive cost centres.
    Accessible by Analyst+.
    """
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]

    @extend_schema(
        tags=['Dashboard'],
        summary='Cost-centre breakdown',
        description=(
            'Expense categories grouped into executive cost centres '
            '(People, Technology, Operations, Growth, Culture, Compliance, Other) '
            'with each centre\'s % share of total expenses. '
            'Powered by pandas on Redis-cached ORM data.'
        ),
        responses={
            200: inline_serializer(
                name='CostCenterRow',
                fields={
                    'cost_center':          drf_serializers.CharField(),
                    'total':                drf_serializers.DecimalField(max_digits=14, decimal_places=2),
                    'count':                drf_serializers.IntegerField(),
                    'pct_of_total_expense': drf_serializers.FloatField(),
                },
                many=True,
            ),
        },
    )
    def get(self, request):
        category_rows = services.get_category_totals()
        return Response(analytics.compute_cost_center_breakdown(category_rows))


class PeopleCostRatioView(APIView):
    """
    GET /api/dashboard/people-cost-ratio/
    People costs (Salaries, Contractors, Benefits, Recruitment) as % of total expenses.
    A standard board / investor metric.
    Accessible by Analyst+.
    """
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]

    @extend_schema(
        tags=['Dashboard'],
        summary='People cost ratio',
        description=(
            'People costs (Salaries + Contractor Fees + Employee Benefits + Recruitment) '
            'as a percentage of total expenses. Standard board and investor metric.'
        ),
        responses={
            200: inline_serializer(
                name='PeopleCostRatio',
                fields={
                    'people_cost_total':    drf_serializers.DecimalField(max_digits=14, decimal_places=2),
                    'total_expense':        drf_serializers.DecimalField(max_digits=14, decimal_places=2),
                    'people_cost_ratio_pct': drf_serializers.FloatField(),
                    'breakdown':            drf_serializers.DictField(),
                },
            ),
        },
    )
    def get(self, request):
        category_rows = services.get_category_totals()
        return Response(analytics.compute_people_cost_ratio(category_rows))


# ===========================================================================
# Analyst+ endpoints (ANALYST and ADMIN roles only)
# ===========================================================================

class MonthlyTrendsView(APIView):
    """
    GET /api/dashboard/monthly-trends/
    Month-wise income vs expense. Each row includes month_label ("YYYY-MM").
    Accessible by Analyst+. Result is Redis-cached.
    """
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]

    @extend_schema(
        tags=['Dashboard'],
        summary='Monthly trends',
        description=(
            'Month-wise income vs expense totals. '
            'Each entry includes `month_label` (e.g. "2025-03") for direct display. '
            'Requires Analyst or Admin role. Redis-cached.'
        ),
        responses={
            200: inline_serializer(
                name='MonthlyTrend',
                fields={
                    'month':        drf_serializers.DateField(),
                    'month_label':  drf_serializers.CharField(
                        help_text='Pre-formatted "YYYY-MM" string for display.'),
                    'record_type':  drf_serializers.CharField(),
                    'total':        drf_serializers.DecimalField(max_digits=14, decimal_places=2),
                    'count':        drf_serializers.IntegerField(),
                },
                many=True,
            ),
        },
    )
    def get(self, request):
        return Response(services.get_monthly_trends())


class BurnRateView(APIView):
    """
    GET /api/dashboard/burn-rate/
    Rolling 3-month average monthly expenses (burn rate).
    Accessible by Viewer+.
    """
    permission_classes = [IsAuthenticated, IsViewerOrAbove]

    @extend_schema(
        tags=['Dashboard'],
        summary='Burn rate',
        description=(
            'Current month expenses and rolling 3-month average burn rate. '
            'Includes a month-by-month trend table.'
        ),
        responses={
            200: inline_serializer(
                name='BurnRate',
                fields={
                    'current_month_expense': drf_serializers.DecimalField(max_digits=14, decimal_places=2),
                    'rolling_3m_avg_burn':   drf_serializers.DecimalField(max_digits=14, decimal_places=2),
                    'months_analysed':       drf_serializers.IntegerField(),
                    'trend':                 drf_serializers.ListField(),
                },
            ),
        },
    )
    def get(self, request):
        monthly_rows = services.get_monthly_trends()
        return Response(analytics.compute_burn_rate(monthly_rows))


class RunwayView(APIView):
    """
    GET /api/dashboard/runway/
    Estimated months of runway (net_balance / avg monthly burn).
    Accessible by Viewer+.
    """
    permission_classes = [IsAuthenticated, IsViewerOrAbove]

    @extend_schema(
        tags=['Dashboard'],
        summary='Runway estimate',
        description=(
            'Estimates months of runway remaining based on net balance '
            'divided by the rolling 3-month average burn rate. '
            'Status: healthy (>=12m), warning (6-12m), critical (<6m).'
        ),
        responses={
            200: inline_serializer(
                name='Runway',
                fields={
                    'net_balance':              drf_serializers.DecimalField(max_digits=14, decimal_places=2),
                    'avg_monthly_burn':         drf_serializers.DecimalField(max_digits=14, decimal_places=2),
                    'estimated_runway_months':  drf_serializers.FloatField(),
                    'runway_status':            drf_serializers.CharField(),
                },
            ),
        },
    )
    def get(self, request):
        summary      = services.get_summary()
        monthly_rows = services.get_monthly_trends()
        return Response(analytics.compute_runway(summary, monthly_rows))


class MoMChangeView(APIView):
    """
    GET /api/dashboard/mom-change/
    Month-over-month % change in expenses per cost centre.
    Accessible by Analyst+.
    """
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]

    @extend_schema(
        tags=['Dashboard'],
        summary='Month-over-month change',
        description=(
            'Month-over-month percentage change in spending per cost centre. '
            'Positive = more spend than previous month. '
            'First month per group shows null (no prior period to compare). '
            'Requires Analyst or Admin role.'
        ),
        responses={
            200: inline_serializer(
                name='MoMChange',
                fields={
                    'month_label':    drf_serializers.CharField(),
                    'cost_center':    drf_serializers.CharField(),
                    'total':          drf_serializers.DecimalField(max_digits=14, decimal_places=2),
                    'mom_change_pct': drf_serializers.FloatField(allow_null=True),
                },
                many=True,
            ),
        },
    )
    def get(self, request):
        monthly_rows = services.get_monthly_trends()
        return Response(analytics.compute_mom_change(monthly_rows))
