from django.conf import settings
import structlog
from datetime import datetime
from mongo_connection import get_db

logger = structlog.get_logger()

class AuditTrailMiddleware:
    """
    Enhanced audit logging middleware that captures:
    - User actions (login, logout, CRUD operations)
    - API endpoint access
    - IP address and user agent
    - Response status and time taken
    - Permission check results (Success/Fail)
    - Authentication status
    - Sensitive data masking
    - Non-JSON 403/401 HTML translation to structured JSON
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = datetime.now()
        ip = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
        path = request.path
        method = request.method
        
        # Process request (runs views, which performs DRF JWT auth)
        response = self.get_response(request)
        
        # Get user info AFTER response is processed (so request.user is authenticated)
        user_id = None
        username = "Anonymous"
        role = "anonymous"
        is_authenticated = False
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = str(request.user._id) if hasattr(request.user, '_id') else str(request.user.id)
            username = request.user.username
            role = getattr(request.user, 'role', 'unknown')
            is_authenticated = True
        
        # Calculate duration
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Determine permission check result (successful codes: 200, 201, 202, 204, etc.)
        if response.status_code in [200, 201, 202, 204]:
            permission_check_result = "Success"
        else:
            permission_check_result = "Fail"

        # Intercept ALL 403 Forbidden or 401 Unauthorized responses
        if response.status_code in [401, 403]:
            # Defaults
            code = "permission_denied"
            error_title = "Permission Denied"
            cause = "Access denied by platform security policy."
            required_permission = "Authorized Role"
            recommended_action = "Please log in with a user account that has the required permission."
            
            # Check if there is existing JSON content we can parse
            content_type = response.headers.get('Content-Type', '')
            if content_type.startswith('application/json'):
                try:
                    import json
                    original_data = json.loads(response.content.decode('utf-8'))
                    if isinstance(original_data, dict):
                        original_msg = original_data.get('message') or original_data.get('error') or original_data.get('detail') or ""
                        if original_msg:
                            cause = original_msg
                except Exception:
                    pass
            else:
                # Parse HTML content (such as CSRF check failures)
                content_sample = b""
                if hasattr(response, 'content'):
                    content_sample = response.content.lower()
                if b'csrf' in content_sample or b'cross-site' in content_sample:
                    code = "csrf_error"
                    error_title = "CSRF Error"
                    cause = "Cross-Site Request Forgery verification token is missing or invalid."
                    required_permission = "Valid CSRF Token"
                    recommended_action = "Refresh the browser page and submit the request again to establish a valid security token."

            # Re-map dynamically based on status code and message contents
            if response.status_code == 403 and code != "csrf_error":
                msg_lower = str(cause).lower()
                if "admin" in msg_lower:
                    code = "admin_role_required"
                    error_title = "Admin Role Required"
                    cause = "This endpoint is restricted to Administrator accounts."
                    required_permission = "Admin Role"
                    recommended_action = "Re-authenticate using an Administrator account to access this configuration."
                elif "investigator" in msg_lower:
                    code = "investigator_role_required"
                    error_title = "Investigator Role Required"
                    cause = "This operation requires Investigator credentials."
                    required_permission = "Investigator Role"
                    recommended_action = "Re-authenticate using an Investigator or Admin account to run this action."
                elif "analyst" in msg_lower:
                    code = "security_analyst_role_required"
                    error_title = "Security Analyst Role Required"
                    cause = "This operation requires Security Analyst credentials."
                    required_permission = "Security Analyst Role"
                    recommended_action = "Re-authenticate using a Security Analyst account."
                elif role == 'analyst':
                    code = "permission_denied"
                    error_title = "Permission Denied"
                    cause = f"Security Analyst role is Read-Only. You do not have permission to modify data on {method} {path}."
                    required_permission = "Investigator or Admin Role"
                    recommended_action = "Ask an Investigator or Administrator to perform this write operation."
                else:
                    code = "permission_denied"
                    error_title = "Permission Denied"
                    cause = f"Your current role ({role}) does not have permission to perform this action on {method} {path}."
                    required_permission = "Authorized Role"
                    recommended_action = "Contact your platform administrator to check or upgrade your role privileges."

            elif response.status_code == 401:
                msg_lower = str(cause).lower()
                if "expire" in msg_lower:
                    code = "session_expired"
                    error_title = "Session Expired"
                    cause = "Your active JSON Web Token (JWT) session has expired."
                    required_permission = "Active JWT Session"
                    recommended_action = "Please log in again to establish a new authenticated session."
                else:
                    code = "authentication_required"
                    error_title = "Authentication Required"
                    cause = "Authentication credentials (JWT) are missing or invalid."
                    required_permission = "Valid Authorization Header"
                    recommended_action = "Please log in and ensure your browser includes the Authorization Bearer header."

            from django.http import JsonResponse
            response = JsonResponse({
                "error": error_title,
                "message": f"{error_title}: {cause}",
                "code": code,
                "status_code": response.status_code,
                "cause": cause,
                "required_permission": required_permission,
                "recommended_action": recommended_action
            }, status=response.status_code)
        
        # Log entry compilation
        response_log = {
            'timestamp': start_time,
            'ip': ip,
            'user_agent': user_agent[:500],  # Truncate
            'method': method,
            'path': path,
            'user_id': user_id,
            'username': username,
            'role': role,
            'is_authenticated': is_authenticated,
            'permission_check_result': permission_check_result,
            'status_code': response.status_code,
            'duration_ms': round(duration_ms, 2),
            'event_type': 'api_access'
        }
        
        # Avoid accessing response.content on StreamingHttpResponse to prevent connection errors
        if getattr(response, 'streaming', False):
            response_size = 0
        else:
            try:
                response_size = len(response.content) if hasattr(response, 'content') else 0
            except Exception:
                response_size = 0

        response_log['response_size'] = response_size
        
        # Enhanced logging for sensitive actions
        sensitive_paths = ['/login/', '/register/', '/token/', '/oauth/']
        if any(sensitive in path for sensitive in sensitive_paths):
            response_log['sensitive_action'] = True
        
        logger.info('Audit response', **response_log)
        
        # Store audit log in MongoDB for persistence
        self.save_audit_log(response_log)
        
        return response
    
    def get_client_ip(self, request):
        """Get real client IP behind proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip
    
    def _mask_sensitive_data(self, data):
        """Recursively mask sensitive fields in dictionaries or strings."""
        if isinstance(data, dict):
            masked = {}
            sensitive_keys = ['password', 'token', 'secret', 'api_key', 'authorization',
                              'cookie', 'access', 'refresh', 'client_secret', 'apikey',
                              'anthropic_api_key', 'google_oauth_client_id']
            for key, value in data.items():
                if any(s in key.lower() for s in sensitive_keys):
                    masked[key] = '***REDACTED***'
                else:
                    masked[key] = self._mask_sensitive_data(value)
            return masked
        elif isinstance(data, list):
            return [self._mask_sensitive_data(item) for item in data]
        elif isinstance(data, str):
            # Mask potential JWT tokens or long secrets in strings
            if len(data) > 40 and (data.startswith('eyJ') or data.startswith('Bearer ')):
                return '***REDACTED_TOKEN***'
            return data
        return data

    def save_audit_log(self, log_data):
        """Save audit log to MongoDB with sensitive data masking or skip if unavailable."""
        try:
            # Deep-mask all potentially sensitive nested data
            log_data = self._mask_sensitive_data(log_data)

            from mongo_connection import get_audit_logs_collection
            audit_collection = get_audit_logs_collection()
            if audit_collection is None:
                return
            audit_collection.insert_one(log_data)
        except Exception as e:
            logger.error('Failed to save audit log', error=str(e))


