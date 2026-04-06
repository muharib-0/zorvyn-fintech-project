"""
Financial Records URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FinancialRecordViewSet

router = DefaultRouter()
router.register('', FinancialRecordViewSet, basename='records')

urlpatterns = [
    path('', include(router.urls)),
]
