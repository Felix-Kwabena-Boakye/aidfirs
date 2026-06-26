import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import api, { evidenceAPI, casesAPI } from '../api'
import { Usb, RefreshCw, Wifi, WifiOff, HardDrive, Database, Hash, Cpu, Play } from 'lucide-react'
import { toast } from 'sonner'

export default function Devices() {
  const [devices, setDevices] = useState([])
  const [scanning, setScanning] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastRefresh, setLastRefresh] = useState(null)
  const navigate = useNavigate()

  const fetchDevices = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.get('/devices/')
      setDevices(response.data.devices || [])
      setScanning(response.data.scanning || false)
      setLastRefresh(new Date())
    } catch (err) {
      toast.error('Failed to fetch devices. Ensure the backend server is running.')
    } finally {
      setLoading(false)
    }
  }, [])

  const startScanning = async () => {
    try {
      await api.post('/devices/scan/')
      setScanning(true)
    } catch (err) {
      toast.error('Failed to start scanning')
    }
  }

  const stopScanning = async () => {

    try {
      await api.delete('/devices/scan/')
      setScanning(false)
    } catch (err) {
      toast.error('Failed to stop scanning')
    }
  }

  const handleExamine = async (device) => {
    if (loading) return
    setLoading(true)
    try {
      // 1. Automatically create a new "AI-Powered" case for this device
      const timestamp = new Date().toLocaleDateString()
      const deviceLabel = device.model || device.volume_name || 'Storage Device'
      const caseData = {
        case_number: `AI-FOR-${Math.floor(Math.random() * 1000000)}`,
        title: `Forensic Examination: ${deviceLabel}`,
        description: `Comprehensive AI-driven forensic acquisition and analysis of ${deviceLabel} (Serial: ${device.serial_number || 'Unknown'}). 
          Initiated on ${timestamp} using automated FTK Imaging and TSK Metadata Recovery.`,
        priority: 'high',
        case_type: 'Digital Forensics'
      }

      const caseResponse = await casesAPI.createCase(caseData)

      const newCaseId = caseResponse.data._id

      // 2. Add device as evidence to the new case
      const evidenceData = {
        case_id: newCaseId,
        evidence_type: 'disk_image',
        file_name: `${deviceLabel}_Forensic_Image`,
        file_path: `${device.drive_letter}:\\`,
        file_size: Math.round(device.size_gb * 1024 * 1024 * 1024),
        description: `Source Device: ${device.model}\nSerial: ${device.serial_number}\nInterface: USB / ${device.drive_letter}:`,
        status: 'collected'
      }

      const evidenceResponse = await evidenceAPI.uploadEvidence(evidenceData)

      const newEvidenceId = evidenceResponse.data._id

      // 3. Set as current case and notify application
      localStorage.setItem('current_case_id', newCaseId)
      window.dispatchEvent(new Event('storage'))

      // 4. Redirect to evidence page with "auto_ingest" to trigger the full chain
      navigate(`/evidence?auto_ingest=${newEvidenceId}`)
    } catch (err) {
      toast.error('Failed to start examination: ' + (err.response?.data?.error || err.message))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDevices()
  }, [fetchDevices])

  // Auto-refresh every 3 s while scanning is active
  useEffect(() => {
    if (!scanning) return
    const interval = setInterval(fetchDevices, 3000)
    return () => clearInterval(interval)
  }, [scanning, fetchDevices])

  const getDeviceIcon = (driveType = '') => {
    if (driveType.toLowerCase().includes('hard'))
      return <HardDrive className="w-8 h-8 text-purple-400" />
    return <Usb className="w-8 h-8 text-blue-400" />
  }

  const getBadgeColor = (driveType = '') => {
    if (driveType.toLowerCase().includes('hard'))
      return 'bg-purple-900/50 text-purple-300 border border-purple-700'
    return 'bg-blue-900/50 text-blue-300 border border-blue-700'
  }

  const formatSize = (gb) => {
    if (!gb || gb === 0) return 'Unknown size'
    if (gb >= 1000) return `${(gb / 1024).toFixed(1)} TB`
    if (gb < 1) return `${Math.round(gb * 1024)} MB`
    return `${gb} GB`
  }

  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Usb className="w-8 h-8 text-blue-400" />
              Connected Devices
            </h1>
            {lastRefresh && (
              <p className="text-gray-500 text-xs mt-1">
                Last updated: {lastRefresh.toLocaleTimeString()}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={fetchDevices}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            {scanning ? (
              <button
                onClick={stopScanning}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg transition-colors"
              >
                <WifiOff className="w-4 h-4" />
                Stop Auto-Scan
              </button>
            ) : (
              <button
                onClick={startScanning}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg transition-colors"
              >
                <Wifi className="w-4 h-4" />
                Auto-Scan
              </button>
            )}
          </div>
        </div>

        {/* Scanning banner */}
        {scanning && (
          <div className="mb-4 p-3 bg-blue-900/40 border border-blue-700 rounded-lg">
            <p className="text-blue-200 text-sm flex items-center gap-2">
              <Wifi className="w-4 h-4 animate-pulse" />
              Auto-scan active — device list refreshes every 3 seconds
            </p>
          </div>
        )}

        {/* Error */}
        {/* Error handled by toast */}

        {/* Loading spinner */}
        {loading && devices.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="w-8 h-8 text-gray-400 animate-spin" />
          </div>
        ) : devices.length === 0 ? (
          /* Empty state */
          <div className="bg-gray-800 rounded-xl p-10 text-center border border-gray-700">
            <Usb className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-300 mb-2">No USB Devices Detected</h2>
            <p className="text-gray-500 text-sm max-w-sm mx-auto">
              Plug in a USB drive or pendrive — it will appear here automatically.
              Use <strong>Auto-Scan</strong> for continuous monitoring.
            </p>
          </div>
        ) : (
          /* Device cards */
          <div className="grid gap-4">
            {devices.map((device, index) => (
              <div
                key={`${device.drive_letter}-${index}`}
                className="bg-gray-800 rounded-xl border border-gray-700 hover:border-blue-700/50 transition-all duration-200 overflow-hidden"
              >
                {/* Card header */}
                <div className="flex items-center gap-4 p-4">
                  <div className="p-3 bg-gray-700/60 rounded-lg flex-shrink-0">
                    {getDeviceIcon(device.drive_type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-semibold text-white truncate">
                      {device.volume_name || device.model || 'USB Drive'}
                    </h3>
                    {device.model && device.model !== device.volume_name && (
                      <p className="text-gray-400 text-sm truncate">{device.model}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => handleExamine(device)}
                      className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg transition-colors"
                    >
                      <Play className="w-3 h-3 fill-current" />
                      Examine
                    </button>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium flex-shrink-0 ${getBadgeColor(device.drive_type)}`}>
                      {device.drive_type}
                    </span>
                  </div>
                </div>

                {/* Card metadata grid ... existing grid ... */}

                {/* Card metadata grid */}
                <div className="border-t border-gray-700/50 px-4 py-3 grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="flex items-center gap-2">
                    <HardDrive className="w-4 h-4 text-gray-500 flex-shrink-0" />
                    <div>
                      <p className="text-xs text-gray-500">Drive</p>
                      <p className="text-sm text-white font-mono font-semibold">
                        {device.drive_letter ? `${device.drive_letter}:` : '—'}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Database className="w-4 h-4 text-gray-500 flex-shrink-0" />
                    <div>
                      <p className="text-xs text-gray-500">Size</p>
                      <p className="text-sm text-white">{formatSize(device.size_gb)}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-gray-500 flex-shrink-0" />
                    <div>
                      <p className="text-xs text-gray-500">Filesystem</p>
                      <p className="text-sm text-white">{device.filesystem || '—'}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Hash className="w-4 h-4 text-gray-500 flex-shrink-0" />
                    <div>
                      <p className="text-xs text-gray-500">Serial</p>
                      <p className="text-sm text-white font-mono truncate" title={device.serial_number}>
                        {device.serial_number ? device.serial_number.substring(0, 12) : '—'}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className="mt-6 text-center text-gray-600 text-sm">
          {devices.length > 0
            ? `${devices.length} USB device${devices.length !== 1 ? 's' : ''} connected`
            : 'No devices connected'}
        </div>
      </div>
    </div>
  )
}
