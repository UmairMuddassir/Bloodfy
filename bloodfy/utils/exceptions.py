"""
Custom exception handling for Bloodfy application.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from django.conf import settings
from rest_framework.exceptions import ValidationError as DRFValidationError
import logging

logger = logging.getLogger('bloodfy')


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns standardized JSON responses.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    # Get request info for logging
    request = context.get('request')
    view = context.get('view')
    
    if response is not None:
        # Standardize the response format
        custom_response_data = {
            'success': False,
            'message': get_error_message(exc),
            'errors': get_error_details(exc, response.data),
            'status_code': response.status_code,
            'timestamp': timezone.now().isoformat(),
        }
        
        # Log the error
        logger.warning(
            f"API Error: {exc.__class__.__name__} - "
            f"Path: {request.path if request else 'N/A'} - "
            f"Status: {response.status_code}"
        )
        
        response.data = custom_response_data
        
    else:
        # Handle unhandled exceptions
        logger.error(
            f"Unhandled Exception: {exc.__class__.__name__} - {str(exc)}",
            exc_info=True
        )
        
        return Response({
            'success': False,
            'message': 'An unexpected error occurred. Please try again later.',
            'errors': {'detail': str(exc) if settings.DEBUG else 'Internal server error'},
            'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR,
            'timestamp': timezone.now().isoformat(),
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return response


def get_error_message(exc):
    """Get a user-friendly error message based on exception type."""
    from rest_framework import exceptions
    
    error_messages = {
        exceptions.AuthenticationFailed: 'Authentication failed. Please check your credentials.',
        exceptions.NotAuthenticated: 'Authentication required. Please log in.',
        exceptions.PermissionDenied: 'You do not have permission to perform this action.',
        exceptions.NotFound: 'The requested resource was not found.',
        exceptions.MethodNotAllowed: 'This method is not allowed for this endpoint.',
        exceptions.Throttled: 'Too many requests. Please try again later.',
        exceptions.ValidationError: 'Invalid data provided. Please check your input.',
        exceptions.ParseError: 'Invalid request format.',
    }
    
    for exc_class, message in error_messages.items():
        if isinstance(exc, exc_class):
            return message
    
    return 'An error occurred while processing your request.'


def get_error_details(exc, response_data):
    """Extract and format error details from the exception."""
    if isinstance(response_data, dict):
        return response_data
    elif isinstance(response_data, list):
        return {'detail': response_data}
    elif isinstance(response_data, str):
        return {'detail': response_data}
    else:
        return {'detail': str(exc)}


class APIError(Exception):
    """Base exception for API errors."""
    
    def __init__(self, message, status_code=status.HTTP_400_BAD_REQUEST, errors=None):
        self.message = message
        self.status_code = status_code
        self.errors = errors or {}
        super().__init__(message)


class NotFoundError(APIError):
    """Exception for resource not found."""
    
    def __init__(self, message="Resource not found"):
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class ValidationError(APIError):
    """Exception for validation errors."""
    
    def __init__(self, message="Validation failed", errors=None):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, errors)


class AuthenticationError(APIError):
    """Exception for authentication errors."""
    
    def __init__(self, message="Authentication failed"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class PermissionError(APIError):
    """Exception for permission errors."""
    
    def __init__(self, message="Permission denied"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class ExternalAPIError(APIError):
    """Exception for external API failures."""
    
    def __init__(self, service_name, message=None):
        msg = message or f"External service '{service_name}' is unavailable"
        super().__init__(msg, status.HTTP_503_SERVICE_UNAVAILABLE)
