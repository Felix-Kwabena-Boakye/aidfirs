from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.conf import settings

import os
import jwt
import requests as req_lib

from .serializers import UserSerializer, UserLoginSerializer
from .models import User, AuditLog
from .services import UserService
from .permissions import IsAdmin


# =========================
# STANDARD ERROR RESPONSE
# =========================
def error(msg, code=400):
    return Response({"success": False, "error": msg}, status=code)


# =========================
# REGISTER
# =========================
class RegisterView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
    def create(self, request, *args, **kwargs):
        data = request.data.copy()

        is_admin = request.user.is_authenticated and request.user.role == "admin"

        if not UserService.validate_registration(data, is_admin=is_admin):
            return error("Invalid registration data or unauthorized role")

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        user_data = serializer.validated_data

        user = UserService.create_user(
            username=user_data["username"],
            email=user_data["email"],
            password=user_data.get("password", "default123"),
            role=user_data.get("role", "analyst"),
            first_name=user_data.get("first_name", ""),
            last_name=user_data.get("last_name", ""),
            is_active=is_admin
        )

        message = (
            "User created successfully"
            if is_admin
            else "Registration submitted. Awaiting admin approval."
        )

        return Response({
            "success": True,
            "message": message,
            "user": UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)


# =========================
# LOGIN
# =========================
@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True), name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return error("Username and password required")

        user = UserService.authenticate(username, password)

        if not user:
            return error("Invalid credentials", 401)

        if not user.is_active:
            return error("Account pending approval or deactivated", 403)

        try:
            user.update_last_login()
        except Exception:
            pass

        access, refresh = UserService.generate_tokens(user)

        return Response({
            "success": True,
            "message": "Login successful",
            "access": access,
            "refresh": refresh,
            "user": UserSerializer(user).data
        })


# =========================
# TOKEN REFRESH
# =========================
class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key='ip', rate='20/h', method='POST', block=True))
    def post(self, request):
        refresh_token = request.data.get("refresh", "").strip()

        if not refresh_token:
            return error("Refresh token required")

        try:
            payload = jwt.decode(
                refresh_token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )

            if payload.get("type") != "refresh":
                return error("Invalid token type", 401)

            user = UserService.get_user_by_id(payload.get("user_id"))

            if not user or not user.is_active:
                return error("User not found or inactive", 401)

            access, _ = UserService.generate_tokens(user)

            return Response({"success": True, "access": access})

        except jwt.ExpiredSignatureError:
            return error("Refresh token expired", 401)
        except jwt.InvalidTokenError:
            return error("Invalid refresh token", 401)


# =========================
# CURRENT USER
# =========================
class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "success": True,
            "user": UserSerializer(request.user).data
        })


# =========================
# PROFILE UPDATE
# =========================
class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return request.user

    def update(self, request, *args, **kwargs):
        user = request.user

        # prevent role abuse
        if "role" in request.data and user.role != "admin":
            return error("You cannot change role", 403)

        if "first_name" in request.data:
            user.first_name = request.data["first_name"]

        if "last_name" in request.data:
            user.last_name = request.data["last_name"]

        if "email" in request.data:
            user.email = request.data["email"]

        if "role" in request.data and user.role == "admin":
            allowed_roles = ["admin", "analyst", "investigator"]
            if request.data["role"] in allowed_roles:
                user.role = request.data["role"]

        user.save()

        return Response({
            "success": True,
            "user": UserSerializer(user).data
        })


# =========================
# USERS LIST (ADMIN)
# =========================
class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return User.get_all()


# =========================
# ADMIN CREATE USER
# =========================
class UserCreateView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = UserService.create_user(**serializer.validated_data)

        return Response({
            "success": True,
            "message": "User created successfully",
            "user": UserSerializer(user).data
        }, status=201)


# =========================
# ACTIVATE / DEACTIVATE USER
# =========================
class UserActivateDeactivateView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, user_id):
        action = request.data.get("action", "deactivate")

        user = UserService.get_user_by_id(user_id)

        if not user:
            return error("User not found", 404)

        if user._id == request.user._id:
            return error("Cannot modify your own account")

        user.is_active = (action == "activate")
        user.save()

        return Response({
            "success": True,
            "message": f"User {action}d successfully",
            "user": UserSerializer(user).data
        })


# =========================
# CHANGE PASSWORD
# =========================
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        current = request.data.get("current_password")
        new = request.data.get("new_password")
        confirm = request.data.get("confirm_password")

        if not all([current, new, confirm]):
            return error("All password fields required")

        if new != confirm:
            return error("Passwords do not match")

        if not User.verify_password(current, request.user.password_hash):
            return error("Incorrect current password")

        request.user.password_hash = User.hash_password(new)
        request.user.save()

        AuditLog.log(
            user_id=str(request.user._id),
            username=request.user.username,
            action="change_password",
            resource_type="user",
            resource_id=str(request.user._id),
            details={"message": "Password changed"}
        )

        return Response({
            "success": True,
            "message": "Password updated successfully"
        })


# =========================
# AI SETTINGS (SAFE VERSION)
# =========================
class AISettingsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
        configured = bool(api_key and "your_" not in api_key)

        return Response({
            "success": True,
            "claude_enabled": request.session.get("claude_enabled", False),
            "claude_model": request.session.get("claude_model", "claude-3-haiku-20240307"),
            "claude_configured": configured
        })

    def post(self, request):
        claude_enabled = request.data.get("claude_enabled")
        claude_model = request.data.get("claude_model")
        api_key = request.data.get("api_key")

        if claude_enabled is not None:
            request.session["claude_enabled"] = claude_enabled

        if claude_model is not None:
            request.session["claude_model"] = claude_model

        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key
            settings.ANTHROPIC_API_KEY = api_key

        return Response({
            "success": True,
            "message": "AI settings updated"
        })


# =========================
# CURRENT USER
# =========================
class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "success": True,
            "user": UserSerializer(request.user).data
        })


# =========================
# AUDIT LOGS
# =========================
class AuditLogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role == "admin":
            logs = AuditLog.get_all_logs(limit=500)
        else:
            logs = AuditLog.get_logs(user_id=str(request.user._id), limit=100)

        return Response({
            "success": True,
            "logs": logs,
            "count": len(logs)
        })


# =========================
# GOOGLE OAUTH (CLEANED)
# =========================
class GoogleOAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")

        if not token:
            return error("Google token required")

        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests

            client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID")

            info = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                client_id
            )

            email = info["email"]
            name = info.get("name", "")

            user = UserService.get_user_by_email(email)

            if not user:
                user = UserService.create_user(
                    username=email.split("@")[0],
                    email=email,
                    password=None,
                    role="analyst",
                    first_name=name
                )
                user.is_active = False
                user.is_oauth_google = True
                user.save()

            if not user.is_active:
                return error("Account pending approval", 403)

            access, refresh = UserService.generate_tokens(user)

            return Response({
                "success": True,
                "access": access,
                "refresh": refresh,
                "user": UserSerializer(user).data
            })

        except Exception as e:
            return error(str(e), 401)
