import React, { useState, useEffect, useCallback } from 'react'
import { devicesAPI } from '../api'
import { Activity, RefreshCw, FolderOpen, Clock, AlertCircle, PlusCircle, Edit, Trash2, Eye } from 'lucide-react'
import { toast } from 'sonner'

export default function FileMonitor() {
  const [events, setEvents] = useState([])
  const [watchDir, setWatchDir] = useState('')
  const [polling, setPolling] = useState(true)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)

  const fetchLogs = useCallback(async (showToast = false) => {
    try {
      if (showToast) setLoading(true)
      const response = await devicesAPI.getInotifyLogs()
      setEvents(response.data.events || [])
      setWatchDir(response.data.watch_dir || '')
      setLastUpdated(new Date())
      if (showToast) {
        toast.success('File monitor logs updated successfully.')
      }
    } catch (err) {
      console.error(err)
      if (showToast) {
        toast.error('Failed to fetch file monitor logs.')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchLogs()
  }, [fetchLogs])

  useEffect(() => {
    if (!polling) return
    const interval = setInterval(() => {
      fetchLogs(false)
    }, 3000)
    return () => clearInterval(interval)
  }, [polling, fetchLogs])

  const getEventBadge = (type) => {
    switch (type) {
      case 'IN_CREATE':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-green-950/60 text-green-400 border border-green-700/60">
            <PlusCircle className="w-3.5 h-3.5" />
            CREATE
          </span>
        )
      case 'IN_MODIFY':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-950/60 text-amber-400 border border-amber-700/60">
            <Edit className="w-3.5 h-3.5" />
            MODIFY
          </span>
        )
      case 'IN_DELETE':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-950/60 text-red-400 border border-red-700/60">
            <Trash2 className="w-3.5 h-3.5" />
            DELETE
          </span>
        )
      default:
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-950/60 text-blue-400 border border-blue-700/60">
            <Activity className="w-3.5 h-3.5" />
            EVENT
          </span>
        )
    }
  }

  const formatTimestamp = (isoString) => {
    try {
      const d = new Date(isoString)
      return d.toLocaleTimeString() + ' ' + d.toLocaleDateString()
    } catch (_) {
      return isoString
    }
  }

  // Calculate stats
  const createCount = events.filter(e => e.event_type === 'IN_CREATE').length
  const modifyCount = events.filter(e => e.event_type === 'IN_MODIFY').length
  const deleteCount = events.filter(e => e.event_type === 'IN_DELETE').length

  return (
    <div className="p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Eye className="w-8 h-8 text-blue-400" />
              Live File System Monitor
            </h1>
            <p className="text-gray-400 text-sm mt-1 flex items-center gap-1.5">
              <FolderOpen className="w-4 h-4 text-purple-400 flex-shrink-0" />
              Watching directory: <code className="text-purple-300 font-mono text-xs bg-purple-950/30 px-2 py-0.5 rounded border border-purple-800/50">{watchDir || 'backend/storage'}</code>
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-gray-800 border border-gray-700 px-3 py-1.5 rounded-lg">
              <input
                type="checkbox"
                id="polling-toggle"
                checked={polling}
                onChange={(e) => setPolling(e.target.checked)}
                className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2 accent-blue-500"
              />
              <label htmlFor="polling-toggle" className="text-sm text-gray-300 cursor-pointer select-none">
                Auto-Refresh (3s)
              </label>
            </div>
            <button
              onClick={() => fetchLogs(true)}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors disabled:opacity-50 font-semibold"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Live indicator & Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-800/60 backdrop-blur border border-gray-700 rounded-xl p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-400">MONITOR STATUS</span>
              <span className="relative flex h-2.5 w-2.5">
                {polling && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>}
                <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${polling ? 'bg-green-500' : 'bg-amber-500'}`}></span>
              </span>
            </div>
            <div className="mt-3">
              <div className="text-xl font-bold text-white">{polling ? 'ACTIVE' : 'PAUSED'}</div>
              {lastUpdated && (
                <div className="text-[10px] text-gray-500 mt-1 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  Checked: {lastUpdated.toLocaleTimeString()}
                </div>
              )}
            </div>
          </div>

          <div className="bg-gray-800/60 backdrop-blur border border-gray-700 rounded-xl p-4 flex flex-col justify-between">
            <span className="text-xs font-semibold text-green-400">CREATIONS</span>
            <div className="mt-3">
              <div className="text-2xl font-bold text-white">{createCount}</div>
              <p className="text-[10px] text-gray-500 mt-1">Files carved or recovered</p>
            </div>
          </div>

          <div className="bg-gray-800/60 backdrop-blur border border-gray-700 rounded-xl p-4 flex flex-col justify-between">
            <span className="text-xs font-semibold text-amber-400">MODIFICATIONS</span>
            <div className="mt-3">
              <div className="text-2xl font-bold text-white">{modifyCount}</div>
              <p className="text-[10px] text-gray-500 mt-1">Files modified in storage</p>
            </div>
          </div>

          <div className="bg-gray-800/60 backdrop-blur border border-gray-700 rounded-xl p-4 flex flex-col justify-between">
            <span className="text-xs font-semibold text-red-400">DELETIONS</span>
            <div className="mt-3">
              <div className="text-2xl font-bold text-white">{deleteCount}</div>
              <p className="text-[10px] text-gray-500 mt-1">Carves or temp logs cleared</p>
            </div>
          </div>
        </div>

        {/* Live Log Feed */}
        <div className="bg-gray-850 border border-gray-700/80 rounded-2xl overflow-hidden shadow-2xl backdrop-blur-md">
          <div className="bg-gray-800/90 border-b border-gray-700 px-6 py-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-blue-400" />
              Security Audit Event Feed
            </h2>
            <span className="text-xs bg-gray-700 text-gray-300 font-mono px-2.5 py-1 rounded-md border border-gray-600">
              Total Logged: {events.length}
            </span>
          </div>

          {loading && events.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <RefreshCw className="w-10 h-10 text-blue-500 animate-spin" />
              <p className="text-gray-400 text-sm animate-pulse">Scanning filesystem updates...</p>
            </div>
          ) : events.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 px-6 text-center border-t border-gray-800">
              <AlertCircle className="w-16 h-16 text-gray-600 mb-4" />
              <h3 className="text-lg font-semibold text-gray-300 mb-1">No Real-time Events Logged</h3>
              <p className="text-gray-500 text-sm max-w-md">
                Filesystem changes in the target directory (e.g. file carvings, recoveries, downloads) will generate standard `inotify` alerts here in real-time.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-800 overflow-y-auto max-h-[500px] scrollbar-thin scrollbar-thumb-gray-700">
              {events.map((event, index) => (
                <div
                  key={`${event.timestamp}-${index}`}
                  className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-gray-800/30 transition-colors"
                >
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 mt-0.5">
                      {getEventBadge(event.event_type)}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-gray-200 font-mono break-all">{event.path}</p>
                      <p className="text-xs text-gray-400 mt-1">{event.message}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-gray-500 font-mono sm:self-center">
                    <Clock className="w-3.5 h-3.5 text-gray-500" />
                    <span>{formatTimestamp(event.timestamp)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
