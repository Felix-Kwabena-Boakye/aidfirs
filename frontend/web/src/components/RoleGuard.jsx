import React from 'react';
import { Navigate } from 'react-router-dom';
import { toast } from 'sonner';

/**
 * RoleGuard - Active Role-Based Access Control Component
 * 
 * Wraps routes to restrict access based on user roles.
 * 
 * Usage:
 *   <Route path="/users" element={<RoleGuard allowedRoles={['admin']}><Layout /></RoleGuard>}>
 *     <Route index element={<Users />} />
 *   </Route>
 */

const ROLE_HIERARCHY = {
  'admin': 3,
  'investigator': 2,
  'analyst': 1
};

export default function RoleGuard({ children, allowedRoles, requireAuth = true }) {
  const userStr = localStorage.getItem('user');
  const token = localStorage.getItem('access_token');

  // Not authenticated
  if (requireAuth && !token) {
    return <Navigate to="/" replace />;
  }

  // No user data but has token - let through, backend will enforce
  if (!userStr) {
    return children;
  }

  let user;
  try {
    user = JSON.parse(userStr);
  } catch {
    localStorage.removeItem('user');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    return <Navigate to="/" replace />;
  }

  const userRole = user.role || 'analyst';
  const userLevel = ROLE_HIERARCHY[userRole] || 0;

  // Check if user's role is in allowed list
  // Also allow higher roles (e.g., admin can access investigator routes)
  const minRequiredLevel = Math.min(...allowedRoles.map(r => ROLE_HIERARCHY[r] || 999));

  if (userLevel < minRequiredLevel) {
    toast.error(`Access denied. Required role: ${allowedRoles.join(' or ')}`);
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

/**
 * Hook to check if current user has a specific role or higher
 */
export function useRole() {
  const userStr = localStorage.getItem('user');
  let user = null;
  try {
    user = userStr ? JSON.parse(userStr) : null;
  } catch {
    user = null;
  }

  const role = user?.role || 'analyst';
  const level = ROLE_HIERARCHY[role] || 0;

  return {
    role,
    level,
    isAdmin: role === 'admin',
    isInvestigator: level >= ROLE_HIERARCHY['investigator'],
    isAnalyst: level >= ROLE_HIERARCHY['analyst'],
    hasRole: (requiredRole) => level >= (ROLE_HIERARCHY[requiredRole] || 0),
    hasAnyRole: (roles) => roles.some(r => level >= (ROLE_HIERARCHY[r] || 0)),
    user
  };
}

