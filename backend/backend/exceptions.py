import logging
from rest_framework.views import exception_handler
from rest_framework.exceptions import PermissionDenied, NotAuthenticated
from datetime import datetime, timezone

logger = logging.getLogger("django.request")

def custom_exception_handler(exc, context):
    """
    Custom exception handler for Django REST Framework.
    Logs details of PermissionDenied and NotAuthenticated exceptions,
    saves audit entries, and returns detailed, user-friendly JSON messages.
    """
    # Call REST framework's default exception handler first to get the standard response.
    response = exception_handler(exc, context)
    
    # Get request metadata
    request = context.get('request')
    path = request.path if request else 'Unknown'
    method = request.method if request else 'Unknown'
    
    # Resolve user details
    user_id = None
    username = "Anonymous"
    role = "anonymous"
    is_authenticated = False
    
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        # Mongo models store primary key as _id
        user_id = str(request.user._id) if hasattr(request.user, '_id') else str(request.user.id)
        username = request.user.username
        role = getattr(request.user, 'role', 'unknown')
        is_authenticated = True

    exc_class = exc.__class__.__name__

    if response is not None:
        # Determine specific error code and user-facing message
        code = "permission_denied"
        message = str(response.data.get('detail', 'Permission denied.'))
        
        if isinstance(exc, NotAuthenticated):
            code = "authentication_failed"
            if "expire" in message.lower():
                code = "session_expired"
                message = "Session Expired: Your token has expired. Please log in again."
            else:
                message = "Authentication Failed: Credentials were not provided or are invalid."
        elif isinstance(exc, PermissionDenied):
            code = "permission_denied"
            if is_authenticated:
                if role == 'analyst':
                    message = f"Permission Denied: Security Analyst role is Read-Only. You do not have permission to modify data on {method} {path}."
                else:
                    message = f"Permission Denied: Your role ({role}) is not authorized for this operation on {method} {path}."
            else:
                message = "Permission Denied: You must be logged in with an authorized role to perform this action."

        # Re-format DRF response to include detailed structured error information
        response.data = {
            "error": "Forbidden" if response.status_code == 403 else "Unauthorized",
            "message": message,
            "code": code,
            "status_code": response.status_code
        }

        # Log detailed warning to Python logger
        logger.warning(
            f"Access Forbidden: path={path} method={method} user_id={user_id} username={username} "
            f"role={role} is_authenticated={is_authenticated} exception={exc_class} code={code} message={message}"
        )

        # Persistence: save to AuditLog collection
        try:
            from accounts.models import AuditLog
            AuditLog.log(
                user_id=user_id,
                username=username,
                action=f"Access Denied ({code})",
                resource_type="API Endpoint",
                resource_id=path,
                details={
                    "method": method,
                    "role": role,
                    "authenticated": is_authenticated,
                    "exception": exc_class,
                    "message": message
                }
            )
        except Exception as e:
            logger.error(f"AuditLog failed to record access exception: {str(e)}")

    return response
