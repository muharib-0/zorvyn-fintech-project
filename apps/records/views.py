"""
Financial Records views.
Provides CRUD endpoints with role-based access control.
"""
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from .models import FinancialRecord
from .serializers import FinancialRecordSerializer, FinancialRecordListSerializer
from .filters import FinancialRecordFilter
from . import services
from apps.users.permissions import IsAdmin, IsViewerOrAbove


@extend_schema(tags=['Records'])
@extend_schema_view(
    list=extend_schema(
        summary='List financial records',
        description=(
            'Returns a paginated, filterable list of active financial records. '
            'Supports filtering by `record_type`, `category`, `date_after`, `date_before`. '
            'Use `?search=<term>` to search across `notes` and `category`. '
            'Use `?ordering=<field>` to sort. Accessible by Viewer+.'
        ),
        parameters=[
            OpenApiParameter(
                name='search',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Search term matched against notes and category.',
                required=False,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary='Get financial record',
        description='Returns the full details of a specific financial record by ID. Accessible by Viewer+.',
    ),
    create=extend_schema(
        summary='Create financial record',
        description='Creates a new financial record (income or expense). The creating user is automatically recorded. Admin only.',
    ),
    partial_update=extend_schema(
        summary='Update financial record',
        description='Partially updates a financial record. Admin only.',
    ),
    destroy=extend_schema(
        summary='Soft-delete financial record',
        description='Soft-deletes a record by setting is_deleted=True. The record is preserved in the database for audit purposes. Admin only.',
        responses={200: None},
    ),
)
class FinancialRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for financial records.

    GET    /api/records/        — List records (with filters)     [Viewer+]
    POST   /api/records/        — Create a record                 [Admin only]
    GET    /api/records/{id}/   — Get single record               [Viewer+]
    PATCH  /api/records/{id}/   — Update a record                 [Admin only]
    DELETE /api/records/{id}/   — Soft delete record               [Admin only]

    Search:
        ?search=<term>  — matches against `notes` and `category` (case-insensitive)
    Filter:
        ?record_type=INCOME|EXPENSE
        ?category=SALARY|RENT|...
        ?date_after=YYYY-MM-DD  &  ?date_before=YYYY-MM-DD
    Order:
        ?ordering=date|-date|amount|-amount|category|created_at
    """
    from django_filters.rest_framework import DjangoFilterBackend
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = FinancialRecordFilter
    search_fields = ['notes', 'category']   # ?search= matches these fields
    ordering_fields = ['date', 'amount', 'created_at', 'category']
    ordering = ['-date', '-created_at']

    def get_queryset(self):
        """Only return non-deleted records."""
        return services.get_active_records().select_related('created_by')

    def get_serializer_class(self):
        """Use lighter serializer for list view."""
        if self.action == 'list':
            return FinancialRecordListSerializer
        return FinancialRecordSerializer

    def get_permissions(self):
        """
        Analyst+ can read, Admin only can write.
        """
        if self.action in ('list', 'retrieve'):
            from apps.users.permissions import IsAnalystOrAbove
            return [IsAuthenticated(), IsAnalystOrAbove()]
        from apps.users.permissions import IsAdmin
        return [IsAuthenticated(), IsAdmin()]

    def perform_create(self, serializer):
        """Create record via service to enforce cache invalidation."""
        serializer.instance = services.create_record(
            serializer.validated_data, self.request.user
        )

    def perform_update(self, serializer):
        """Update record via service to enforce cache invalidation."""
        serializer.instance = services.update_record(
            serializer.instance, serializer.validated_data
        )

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete — set is_deleted=True instead of hard deleting.
        """
        record = self.get_object()
        services.soft_delete_record(record)
        return Response(
            {'message': 'Record has been soft-deleted.'},
            status=status.HTTP_200_OK,
        )

