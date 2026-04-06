"""
Dashboard URL configuration.
"""
from django.urls import path
from .views import (
    SummaryView,
    CategoryTotalsView,
    MonthlyTrendsView,
    RecentTransactionsView,
    RevenuBreakdownView,
    CostCenterBreakdownView,
    PeopleCostRatioView,
    BurnRateView,
    RunwayView,
    MoMChangeView,
)

urlpatterns = [
    # Viewer+ ---------------------------------------------------------------
    path('summary/',               SummaryView.as_view(),           name='dashboard-summary'),
    path('category-totals/',       CategoryTotalsView.as_view(),    name='dashboard-category-totals'),
    path('recent/',                RecentTransactionsView.as_view(), name='dashboard-recent'),
    path('revenue-breakdown/',     RevenuBreakdownView.as_view(),   name='dashboard-revenue-breakdown'),
    path('cost-center-breakdown/', CostCenterBreakdownView.as_view(), name='dashboard-cost-center-breakdown'),
    path('people-cost-ratio/',     PeopleCostRatioView.as_view(),   name='dashboard-people-cost-ratio'),
    # Analyst+ --------------------------------------------------------------
    path('monthly-trends/',        MonthlyTrendsView.as_view(),     name='dashboard-monthly-trends'),
    path('burn-rate/',             BurnRateView.as_view(),          name='dashboard-burn-rate'),
    path('runway/',                RunwayView.as_view(),            name='dashboard-runway'),
    path('mom-change/',            MoMChangeView.as_view(),         name='dashboard-mom-change'),
]
