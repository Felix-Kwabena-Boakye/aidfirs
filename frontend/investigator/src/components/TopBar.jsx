import React from "react";
import { useState, useEffect } from 'react'
import { Bell, User, ChevronDown, Search } from 'lucide-react'
import { Menu } from '@headlessui/react'
import { casesAPI } from '../api'

const notifications = [
  { id: 1, message: 'New evidence uploaded to Case #1234', time: '5 min ago' },
  { id: 2, message: 'AI analysis completed for Evidence EV-5678', time: '1 hour ago' },
  { id: 3, message: 'System maintenance scheduled for tonight', time: '2 hours ago' },
]

export default function TopBar() {
  const [cases, setCases] = useState([])
  const [selectedCaseId, setSelectedCaseId] = useState('')

  useEffect(() => {
    const fetchCases = async () => {
      try {
        const response = await casesAPI.getCases()
        const fetchedCases = response.data || []
        setCases(fetchedCases)

        // Initialize from localStorage or first case
        const savedCaseId = localStorage.getItem('current_case_id')
        if (savedCaseId && fetchedCases.some(c => c._id === savedCaseId)) {
          setSelectedCaseId(savedCaseId)
        } else if (fetchedCases.length > 0) {
          const firstId = fetchedCases[0]._id
          setSelectedCaseId(firstId)
          localStorage.setItem('current_case_id', firstId)
        }
      } catch (err) {
        console.error('Failed to fetch cases:', err)
      }
    }
    fetchCases()
  }, [])

  const handleCaseChange = (e) => {
    const newId = e.target.value
    setSelectedCaseId(newId)
    localStorage.setItem('current_case_id', newId)
    // Dispatch event to notify other components (like Devices)
    window.dispatchEvent(new Event('storage'))
  }

  return (
    <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
      <div className="flex items-center justify-between">
        {/* Search */}
        <div className="flex-1 max-w-md">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="Search cases, evidence, or analysis..."
              className="w-full pl-10 pr-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Case Selector */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <span className="text-gray-300 text-sm">Current Case:</span>
            <select
              value={selectedCaseId}
              onChange={handleCaseChange}
              className="bg-gray-700 border border-gray-600 rounded px-3 py-1 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {cases.length === 0 && <option value="">No Cases Available</option>}
              {cases.map(c => (
                <option key={c._id} value={c._id}>
                  {c.case_number} - {c.title}
                </option>
              ))}
            </select>
          </div>
          {/* ... existing notifications and user menu ... */}

          {/* Notifications */}
          <Menu as="div" className="relative">
            <Menu.Button className="relative p-2 text-gray-400 hover:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 rounded">
              <Bell size={20} />
              <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                3
              </span>
            </Menu.Button>
            <Menu.Items className="absolute right-0 mt-2 w-80 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-50">
              <div className="p-4 border-b border-gray-700">
                <h3 className="text-white font-medium">Notifications</h3>
              </div>
              <div className="max-h-64 overflow-y-auto">
                {notifications.map((notification) => (
                  <Menu.Item key={notification.id}>
                    {({ active }) => (
                      <div className={`p-4 border-b border-gray-700 last:border-b-0 ${active ? 'bg-gray-700' : ''}`}>
                        <p className="text-white text-sm">{notification.message}</p>
                        <p className="text-gray-400 text-xs mt-1">{notification.time}</p>
                      </div>
                    )}
                  </Menu.Item>
                ))}
              </div>
            </Menu.Items>
          </Menu>

          {/* User Menu */}
          <Menu as="div" className="relative">
            <Menu.Button className="flex items-center space-x-2 p-2 text-gray-300 hover:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 rounded">
              <User size={20} />
              <span className="text-sm">
                {(() => {
                  try {
                    const user = JSON.parse(localStorage.getItem('user') || '{}');
                    const role = user.role || 'investigator';
                    if (role === 'admin') return 'Administrator';
                    return role.charAt(0).toUpperCase() + role.slice(1);
                  } catch (e) {
                    return 'Investigator';
                  }
                })()}
              </span>
              <ChevronDown size={16} />
            </Menu.Button>
            <Menu.Items className="absolute right-0 mt-2 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-50">
              <Menu.Item>
                {({ active }) => (
                  <button className={`w-full text-left px-4 py-2 text-sm ${active ? 'bg-gray-700' : 'text-gray-300'} hover:text-white`}>
                    Profile Settings
                  </button>
                )}
              </Menu.Item>
              <Menu.Item>
                {({ active }) => (
                  <button className={`w-full text-left px-4 py-2 text-sm ${active ? 'bg-gray-700' : 'text-gray-300'} hover:text-white`}>
                    Preferences
                  </button>
                )}
              </Menu.Item>
              <Menu.Item>
                {({ active }) => (
                  <button className={`w-full text-left px-4 py-2 text-sm ${active ? 'bg-gray-700' : 'text-gray-300'} hover:text-white`}>
                    Logout
                  </button>
                )}
              </Menu.Item>
            </Menu.Items>
          </Menu>
        </div>
      </div>
    </header>
  )
}
