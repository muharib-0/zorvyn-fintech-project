"""
Custom exception handler for consistent API error responses.

All errors follow this shape:
{
    "error": true,
    "message": "string",
    "details": {}
}
"""
from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    NotFound,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns consistent JSON error responses.
    """
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        custom_response = {
            'error': True,
            'message': _get_error_message(exc),
            'details': _get_error_details(exc, response),
        }
        response.data = custom_response

    return response


def _get_error_message(exc):
    """Extract a clean error message from the exception."""
    if isinstance(exc, ValidationError):
        return 'Validation error.'
    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        return 'Authentication failed.'
    if isinstance(exc, PermissionDenied):
        return 'You do not have permission to perform this action.'
    if isinstance(exc, NotFound):
        return 'Resource not found.'

    # Fallback
    if hasattr(exc, 'detail'):
        if isinstance(exc.detail, str):
            return exc.detail
        return 'An error occurred.'
    return 'An unexpected error occurred.'


def _get_error_details(exc, response):
    """Extract structured error details."""
    if isinstance(exc, ValidationError):
        # Return field-level errors
        if isinstance(exc.detail, dict):
            return exc.detail
        if isinstance(exc.detail, list):
            return {'non_field_errors': exc.detail}
    return {}
