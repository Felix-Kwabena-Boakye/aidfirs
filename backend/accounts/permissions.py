"""
Custom permissions for role-based access control
"""
from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'admin'
        )


class IsInvestigator(permissions.BasePermission):
    """
    Allows access to investigator and admin users.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['admin', 'investigator']
        )


class IsAnalystOrAbove(permissions.BasePermission):
    """
    Allows access to analyst, investigator, and admin users.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['admin', 'investigator', 'analyst']
        )


class CanManageUsers(permissions.BasePermission):
    """
    Only admins can create users with any role.
    Investigators and analysts cannot create other users.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Only admins can create users
        if request.method == 'POST':
            return request.user.role == 'admin'
        
        return True
    
    def has_object_permission(self, request, view, obj):
        # Admins can do anything
        if request.user.role == 'admin':
            return True
        
        # Users can only update their own profile (except role)
        if request.method in ['PUT', 'PATCH']:
            return obj._id == request.user._id
        
        return False


class CanManageCases(permissions.BasePermission):
    """
    Investigators and admins can create/manage cases.
    Analysts can only view cases.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # List and view allowed for all authenticated users
        if request.method in ['GET']:
            return True
        
        # Create, update, delete only for investigators and admins
        return request.user.role in ['admin', 'investigator']


class CanManageEvidence(permissions.BasePermission):
    """
    Investigators and admins can upload/manage evidence.
    Analysts can only view evidence.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # List and view allowed for all authenticated users
        if request.method in ['GET']:
            return True
        
        # Create, update, delete only for investigators and admins
        return request.user.role in ['admin', 'investigator']


class CanRunAnalysis(permissions.BasePermission):
    """
    Investigators and admins can run AI analysis.
    Analysts can view analysis results.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # View allowed for all
        if request.method in ['GET']:
            return True
        
        # Create/run analysis only for investigators and admins
        return request.user.role in ['admin', 'investigator']


class CanManageSystem(permissions.BasePermission):
    """
    Only admins can manage system settings, AI models, and view audit logs.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Only admins can access system management endpoints
        return request.user.role == 'admin'
