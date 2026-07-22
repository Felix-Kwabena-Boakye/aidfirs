import React from "react";
import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, FolderOpen, FileText, BarChart3, FileBarChart,
  Settings, Usb, Users, Shield, Bot, Menu, X, Zap, Cpu, Eye,
  Lock, Clock, Hash, Download, PackageOpen, Link2
} from 'lucide-react'

// Get user role from localStorage
const getUserRole = () => {
  try {
    const userStr = localStorage.getItem('user')
    if (userStr) {
      const user = JSON.parse(userStr)
      return user.role || 'analyst'
    }
  } catch (e) {
    console.error('Error getting user role:', e)
  }
  return 'analyst'
}

// Menu items with role requirements
const allMenuItems = [
  { name: 'Dashboard', icon: LayoutDashboard, path: '/dashboard', roles: ['admin', 'investigator', 'analyst'] },
  { name: 'Devices', icon: Usb, path: '/devices', roles: ['admin', 'investigator'] },
  { name: 'File Monitor', icon: Eye, path: '/file-monitor', roles: ['admin', 'investigator'] },
  { name: 'Cases', icon: FolderOpen, path: '/cases', roles: ['admin', 'investigator', 'analyst'] },
  { name: 'Evidence', icon: FileText, path: '/evidence', roles: ['admin', 'investigator', 'analyst'] },
  { name: 'Recovered Files', icon: FolderOpen, path: '/recovered-files', roles: ['admin', 'investigator', 'analyst'] },
  { name: 'Recovery Jobs', icon: Cpu, path: '/recovery-jobs', roles: ['admin', 'investigator', 'analyst'] },
  { name: 'Timeline', icon: Clock, path: '/timeline', roles: ['admin', 'investigator', 'analyst'] },
  { name: 'Hash Verification', icon: Hash, path: '/hash-verification', roles: ['admin', 'investigator', 'analyst'] },
  { name: 'Chain of Custody', icon: Link2, path: '/chain-of-custody', roles: ['admin', 'investigator', 'analyst'] },
  { name: 'Downloads', icon: Download, path: '/downloads', roles: ['admin', 'investigator', 'analyst'] },
  { name: 'Evidence Preview', icon: Eye, path: '/evidence-preview', roles: ['admin', 'investigator', 'analyst'] },
  { name: 'Analysis', icon: BarChart3, path: '/analysis', roles: ['admin', 'investigator', 'analyst'] },
  { name: 'Reports', icon: FileBarChart, path: '/reports', roles: ['admin', 'investigator', 'analyst'] },
  { name: 'Users', icon: Users, path: '/users', roles: ['admin'] },
  { name: 'Audit Logs', icon: Shield, path: '/audit-logs', roles: ['admin'] },
  { name: 'Permissions Audit', icon: Lock, path: '/permissions-audit', roles: ['admin'] },
  { name: 'Settings', icon: Settings, path: '/settings', roles: ['admin'] },
]

export default function Sidebar() {
  const [isMobileOpen, setIsMobileOpen] = useState(false)
  const [userRole, setUserRole] = useState('analyst')
  const location = useLocation()

  useEffect(() => {
    // Get user role on mount and when user changes
    const role = getUserRole()
    setUserRole(role)

    // Listen for storage changes (e.g., login/logout)
    const handleStorageChange = () => {
      setUserRole(getUserRole())
    }
    window.addEventListener('storage', handleStorageChange)

    // Also check periodically for changes
    const interval = setInterval(() => {
      setUserRole(getUserRole())
    }, 1000)

    return () => {
      window.removeEventListener('storage', handleStorageChange)
      clearInterval(interval)
    }
  }, [])

  // Close mobile sidebar on route change
  useEffect(() => {
    setIsMobileOpen(false)
  }, [location.pathname])

  // Filter menu items based on user role
  const menuItems = allMenuItems.filter(item => item.roles.includes(userRole))

  // Get role display name
  const getRoleDisplayName = (role) => {
    switch (role) {
      case 'admin': return 'Administrator'
      case 'investigator': return 'Investigator'
      case 'analyst': return 'Analyst'
      default: return 'User'
    }
  }

  return (
    <>
      {/* Menu button - always visible */}
      <button
        className="fixed top-4 left-4 z-50 p-2 bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-700 transition-colors"
        onClick={() => setIsMobileOpen(!isMobileOpen)}
        aria-label="Toggle menu"
      >
        {isMobileOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {/* Overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-30"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar drawer */}
      <aside className={`fixed inset-y-0 left-0 z-40 w-64 bg-gray-800 border-r border-gray-700 transition-transform duration-300 ease-in-out ${isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}>
        <div className="flex flex-col h-full pt-16">
          <div className="px-4 py-4 border-b border-gray-700 flex flex-col items-center">
            <img src="/logo.png" alt="Cloud Z AI Operating System" className="h-16 w-auto object-contain mb-2" />
            <p className="text-xs text-gray-400">{getRoleDisplayName(userRole)}</p>
          </div>
          <nav className="flex-1 px-4 py-4 space-y-1 overflow-y-auto">
            {menuItems.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.path
              return (
                <Link
                  key={item.name}
                  to={item.path}
                  className={`flex items-center space-x-3 px-3 py-2.5 rounded-lg transition-colors ${isActive ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700'
                    }`}
                  onClick={() => setIsMobileOpen(false)}
                >
                  <Icon size={20} />
                  <span className="text-sm">{item.name}</span>
                </Link>
              )
            })}
          </nav>
        </div>
      </aside>
    </>
  )
}
