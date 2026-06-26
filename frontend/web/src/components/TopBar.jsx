import React from "react";
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, User, ChevronDown, Search, LogOut, Shield, AlertTriangle, FileQuestion, X, FolderOpen, FileCode, Cpu } from 'lucide-react'
import { Menu } from '@headlessui/react'
import { casesAPI } from '../api'
import { toast } from 'sonner'

const notifications = [
  { id: 1, message: 'New evidence uploaded to Case #1234', time: '5 min ago' },
  { id: 2, message: 'AI analysis completed for Evidence EV-5678', time: '1 hour ago' },
  { id: 3, message: 'System maintenance scheduled for tonight', time: '2 hours ago' },
]

export default function TopBar() {
  const [cases, setCases] = useState([])
  const [selectedCaseId, setSelectedCaseId] = useState('')
  const [user, setUser] = useState(null)
  const navigate = useNavigate()

  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState(null)
  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [showResults, setShowResults] = useState(false)

  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    const query = searchQuery.trim();
    if (!query) return;

    console.log("[SEARCH] Search button clicked or form submitted");
    console.log(`[SEARCH] Search query received: "${query}"`);
    
    setIsSearching(true);
    setSearchError('');
    setSearchResults(null);
    setShowResults(true);

    const requestUrl = `http://127.0.0.1:8000/api/cases/search/?q=${encodeURIComponent(query)}`;
    console.log(`[SEARCH] API request URL: ${requestUrl}`);
    console.log(`[SEARCH] Request payload: None (GET request)`);

    try {
      const response = await casesAPI.globalSearch(query);
      console.log(`[SEARCH] Response status: ${response.status} ${response.statusText}`);
      console.log("[SEARCH] Response body:", response.data);
      
      setSearchResults(response.data);
    } catch (err) {
      console.error("[SEARCH] Search query execution failed:", err);
      const errStatus = err.response?.status || 'Network Error';
      const errBody = err.response?.data || err.message;
      console.log(`[SEARCH] Response status: ${errStatus}`);
      console.log("[SEARCH] Response body:", errBody);

      let cleanMsg = "An error occurred while running search. Please check the logs.";
      if (err.response?.data?.message) {
        cleanMsg = err.response.data.message;
      } else if (err.message) {
        cleanMsg = err.message;
      }
      setSearchError(cleanMsg);
      toast.error(cleanMsg);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSelectResult = (caseId, path) => {
    console.log(`[SEARCH] Selecting result - Navigating to case ${caseId} at route ${path}`);
    localStorage.setItem('current_case_id', caseId);
    window.dispatchEvent(new Event('storage'));
    setShowResults(false);
    navigate(path);
    window.location.reload();
  };


  useEffect(() => {
    // Get user info
    try {
      const userStr = localStorage.getItem('user')
      if (userStr) {
        setUser(JSON.parse(userStr))
      }
    } catch (e) {
      console.error('Error parsing user:', e)
    }

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

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    localStorage.removeItem('current_case_id')
    toast.success('Logged out successfully')
    navigate('/')
    window.location.reload()
  }

  const getRoleDisplayName = (role) => {
    switch (role) {
      case 'admin': return 'Administrator'
      case 'investigator': return 'Investigator'
      case 'analyst': return 'Analyst'
      default: return 'User'
    }
  }

  const getRoleColor = (role) => {
    switch (role) {
      case 'admin': return 'text-red-400'
      case 'investigator': return 'text-blue-400'
      case 'analyst': return 'text-green-400'
      default: return 'text-gray-400'
    }
  }

  return (
    <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
      <div className="flex items-center justify-between">
        {/* Search */}
        <div className="flex-1 max-w-md pl-12">
          <form onSubmit={handleSearch} className="relative">
            <input
              type="text"
              placeholder="Search cases, evidence, or analysis..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-4 pr-10 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <button
              type="submit"
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white transition-colors duration-200"
            >
              <Search size={18} />
            </button>
          </form>
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
              <Shield size={18} className={user ? getRoleColor(user.role) : 'text-gray-400'} />
              <span className="text-sm">
                {user ? `${user.first_name || user.username} (${getRoleDisplayName(user.role)})` : 'User'}
              </span>
              <ChevronDown size={16} />
            </Menu.Button>
            <Menu.Items className="absolute right-0 mt-2 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-50">
              <div className="px-4 py-2 border-b border-gray-700">
                <p className="text-white text-sm font-medium">{user?.username || 'User'}</p>
                <p className={`text-xs ${user ? getRoleColor(user.role) : 'text-gray-400'}`}>
                  {user ? getRoleDisplayName(user.role) : 'Unknown'}
                </p>
              </div>
              <Menu.Item>
                {({ active }) => (
                  <button
                    onClick={() => navigate('/dashboard')}
                    className={`w-full text-left px-4 py-2 text-sm ${active ? 'bg-gray-700' : 'text-gray-300'} hover:text-white`}
                  >
                    Dashboard
                  </button>
                )}
              </Menu.Item>
              <Menu.Item>
                {({ active }) => (
                  <button
                    onClick={handleLogout}
                    className={`w-full text-left px-4 py-2 text-sm flex items-center gap-2 ${active ? 'bg-gray-700' : 'text-red-400'} hover:text-red-300`}
                  >
                    <LogOut size={16} />
                    Logout
                  </button>
                )}
              </Menu.Item>
            </Menu.Items>
          </Menu>
        </div>
      </div>
      {/* Search Results Modal */}
      {showResults && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-[9999] flex items-center justify-center p-4">
          <div className="bg-gray-800/95 border border-gray-700 rounded-xl max-w-4xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-700 flex justify-between items-center bg-gray-900/50">
              <div className="flex items-center gap-2">
                <Search className="text-blue-400" size={20} />
                <h3 className="text-lg font-semibold text-white">Forensic Search Results</h3>
                <span className="text-xs bg-gray-700 text-gray-300 font-mono px-2 py-0.5 rounded">
                  Query: {searchQuery}
                </span>
              </div>
              <button
                onClick={() => {
                  setShowResults(false);
                  setSearchResults(null);
                  setSearchError('');
                }}
                className="p-1 text-gray-400 hover:text-white rounded-lg hover:bg-gray-700/50 transition-all duration-200"
              >
                <X size={20} />
              </button>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {isSearching && (
                <div className="flex flex-col items-center justify-center py-20 space-y-4">
                  <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
                  <p className="text-gray-400 text-sm animate-pulse">Running global query across case collections...</p>
                </div>
              )}

              {searchError && (
                <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-5 flex items-start gap-3">
                  <AlertTriangle className="text-red-400 shrink-0 mt-0.5" size={20} />
                  <div>
                    <h4 className="text-red-400 font-semibold text-sm">Search Operation Failed</h4>
                    <p className="text-red-300/80 text-xs mt-1 leading-relaxed">{searchError}</p>
                  </div>
                </div>
              )}

              {!isSearching && !searchError && searchResults && (
                <>
                  {/* Empty state check */}
                  {searchResults.cases.length === 0 &&
                  searchResults.evidence.length === 0 &&
                  searchResults.analysis_results.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-16 space-y-4 text-center">
                      <div className="p-4 bg-gray-700/30 rounded-full border border-gray-600/30">
                        <FileQuestion className="text-gray-400" size={40} />
                      </div>
                      <div>
                        <h4 className="text-white font-semibold text-base">No Matching Entries Found</h4>
                        <p className="text-gray-400 text-sm mt-1 max-w-md leading-relaxed">
                          Your query did not return any matching cases, evidence files, or analytical findings. Please refine your query terms.
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {/* Cases */}
                      {searchResults.cases.length > 0 && (
                        <div className="space-y-3">
                          <h4 className="text-sm font-semibold text-blue-400 uppercase tracking-wider flex items-center gap-1.5 border-b border-gray-700 pb-2">
                            <FolderOpen size={16} />
                            Cases ({searchResults.cases.length})
                          </h4>
                          <div className="grid gap-3 grid-cols-1 md:grid-cols-2">
                            {searchResults.cases.map((c) => (
                              <div
                                key={c._id}
                                onClick={() => handleSelectResult(c._id, '/cases')}
                                className="p-4 bg-gray-700/30 hover:bg-gray-700/60 border border-gray-700 hover:border-blue-500/50 rounded-lg cursor-pointer transition-all duration-200 group"
                              >
                                <div className="flex justify-between items-start">
                                  <span className="text-xs font-mono text-blue-400 font-semibold group-hover:text-blue-300">
                                    {c.case_number}
                                  </span>
                                  <span className={`text-[10px] uppercase px-1.5 py-0.5 rounded font-mono ${
                                    c.status === 'closed' ? 'bg-red-950/40 text-red-400 border border-red-900/30' : 'bg-green-950/40 text-green-400 border border-green-900/30'
                                  }`}>
                                    {c.status}
                                  </span>
                                </div>
                                <h5 className="text-white font-medium text-sm mt-1.5 group-hover:text-blue-300">
                                  {c.title}
                                </h5>
                                <p className="text-gray-400 text-xs mt-1 line-clamp-2">
                                  {c.description}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Evidence */}
                      {searchResults.evidence.length > 0 && (
                        <div className="space-y-3">
                          <h4 className="text-sm font-semibold text-blue-400 uppercase tracking-wider flex items-center gap-1.5 border-b border-gray-700 pb-2">
                            <FileCode size={16} />
                            Evidence Files ({searchResults.evidence.length})
                          </h4>
                          <div className="grid gap-3 grid-cols-1 md:grid-cols-2">
                            {searchResults.evidence.map((e) => (
                              <div
                                key={e._id}
                                onClick={() => handleSelectResult(e.case_id, '/evidence')}
                                className="p-4 bg-gray-700/30 hover:bg-gray-700/60 border border-gray-700 hover:border-blue-500/50 rounded-lg cursor-pointer transition-all duration-200 group"
                              >
                                <div className="flex justify-between items-start">
                                  <span className="text-xs font-mono text-gray-400 truncate max-w-[200px]">
                                    {e.evidence_type.toUpperCase()}
                                  </span>
                                  <span className="text-[10px] text-gray-500 font-mono">
                                    {(e.file_size / 1024 / 1024).toFixed(2)} MB
                                  </span>
                                </div>
                                <h5 className="text-white font-medium text-sm mt-1.5 truncate group-hover:text-blue-300">
                                  {e.file_name}
                                </h5>
                                <p className="text-gray-400 text-xs mt-1 line-clamp-1 italic">
                                  {e.file_path}
                                </p>
                                <p className="text-gray-400 text-xs mt-1 line-clamp-1">
                                  {e.description || 'No description provided.'}
                                </p>
                                {e.hash_sha256 && (
                                  <div className="mt-2 text-[10px] font-mono text-gray-500 truncate">
                                    SHA256: {e.hash_sha256}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Analysis Results */}
                      {searchResults.analysis_results.length > 0 && (
                        <div className="space-y-3">
                          <h4 className="text-sm font-semibold text-blue-400 uppercase tracking-wider flex items-center gap-1.5 border-b border-gray-700 pb-2">
                            <Cpu size={16} />
                            Forensic Findings ({searchResults.analysis_results.length})
                          </h4>
                          <div className="grid gap-3 grid-cols-1">
                            {searchResults.analysis_results.map((ar) => (
                              <div
                                key={ar._id}
                                onClick={() => handleSelectResult(ar.case_id, '/analysis')}
                                className="p-4 bg-gray-700/30 hover:bg-gray-700/60 border border-gray-700 hover:border-blue-500/50 rounded-lg cursor-pointer transition-all duration-200 group"
                              >
                                <div className="flex justify-between items-start">
                                  <span className="text-xs font-mono text-blue-400 uppercase">
                                    {ar.analysis_type} Analysis
                                  </span>
                                  <span className={`text-[10px] uppercase px-1.5 py-0.5 rounded font-mono ${
                                    ar.severity === 'critical' || ar.severity === 'high'
                                      ? 'bg-red-950/40 text-red-400 border border-red-900/30'
                                      : ar.severity === 'medium'
                                      ? 'bg-orange-950/40 text-orange-400 border border-orange-900/30'
                                      : 'bg-blue-950/40 text-blue-400 border border-blue-900/30'
                                  }`}>
                                    {ar.severity}
                                  </span>
                                </div>
                                <h5 className="text-white font-medium text-sm mt-1.5 group-hover:text-blue-300">
                                  Findings: {ar.findings?.summary || ar.findings?.headline || 'Detailed findings parsed.'}
                                </h5>
                                {ar.summaries?.length > 0 && (
                                  <div className="mt-2 text-xs text-gray-400">
                                    <ul className="list-disc list-inside space-y-0.5">
                                      {ar.summaries.slice(0, 2).map((s, idx) => (
                                        <li key={idx} className="truncate">{s}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-3 border-t border-gray-700 bg-gray-900/30 flex justify-end">
              <button
                onClick={() => {
                  setShowResults(false);
                  setSearchResults(null);
                  setSearchError('');
                }}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium rounded-lg transition-colors duration-200"
              >
                Close Window
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  )
}

