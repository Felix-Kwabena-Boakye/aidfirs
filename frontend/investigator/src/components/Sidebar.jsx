import React from "react";
import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, FolderOpen, FileText, BarChart3, FileBarChart, Settings, Usb, Users, Shield, Bot } from 'lucide-react'

// Get user role from localStorage
const getUserRole = () => {
  try {
    const userStr = localStorage.getItem('user')
    if (userStr) {
      const user = JSON.parse(userStr)
return user.role || 'investigator'
    }
  } catch (e) {
    console.error('Error getting user role:', e)
  }
  return 'analyst'
}

// Menu items with role requirements
const allMenuItems = [
  { name: 'Dashboard', icon: LayoutDashboard, path: '/dashboard', roles: ['admin', 'investigator', 'analyst'] },
  { name: 'AI Assistant', icon: Bot, path: '/ai-assistant', roles: ['admin', 'investigator', 'analyst'] },
  { name: 'Devices', icon: Usb, path: '/devices', roles: ['admin', 'investigator'] },
  { name: 'Cases', icon: FolderOpen, path: '/cases', roles: ['admin', 'investigator', 'analyst'] },
  { name: 'Evidence', icon: FileText, path: '/evidence', roles: ['admin', 'investigator', 'analyst'] },
  { name: 'Analysis', icon: BarChart3, path: '/analysis', roles: ['admin', 'investigator', 'analyst'] },
  { name: 'Reports', icon: FileBarChart, path: '/reports', roles: ['admin', 'investigator', 'analyst'] },

  { name: 'Settings', icon: Settings, path: '/settings', roles: ['admin', 'investigator', 'analyst'] },
]

export default function Sidebar() {
  const [isOpen, setIsOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const [userRole, setUserRole] = useState('analyst')
  const location = useLocation()

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768)
    }
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  useEffect(() => {
    if (isMobile) {
      setIsOpen(false)
    }
  }, [location.pathname, isMobile])

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
      <button
        className="fixed top-4 left-4 z-50 p-2 bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-700 transition-colors"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Toggle menu"
      >
        {isOpen ? (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        ) : (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        )}
      </button>

      <aside className={`bg-gray-800 border-r border-gray-700 w-64 fixed inset-y-0 left-0 z-40 transition-transform duration-300 ease-in-out ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex flex-col h-full pt-16">
          <div className="px-4 py-2 border-b border-gray-700">
            <h2 className="text-lg font-semibold text-white">Menu</h2>
            <p className="text-xs text-gray-400 mt-1">{getRoleDisplayName(userRole)}</p>
          </div>
          <nav className="flex-1 px-4 py-4 space-y-1">
            {menuItems.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.path
              return (
                <Link
                  key={item.name}
                  to={item.path}
                  className={`flex items-center space-x-3 px-3 py-2.5 rounded-lg transition-colors ${isActive ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700'}`}
                  onClick={() => isMobile && setIsOpen(false)}
                >
                  <Icon size={20} />
                  <span>{item.name}</span>
                </Link>
              )
            })}
          </nav>
        </div>
      </aside>

      {isOpen && <div className="fixed inset-0 bg-black bg-opacity-50 z-30" onClick={() => setIsOpen(false)} />}
    </>
  )
}
