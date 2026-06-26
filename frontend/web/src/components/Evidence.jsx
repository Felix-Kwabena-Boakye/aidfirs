import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { evidenceAPI, casesAPI, devicesAPI } from '../api';
import { 
  Shield, 
  AlertTriangle, 
  Cpu, 
  Database, 
  Search, 
  Folder, 
  CheckCircle, 
  RefreshCw, 
  FileText, 
  Layers, 
  Download, 
  Trash2, 
  Check, 
  Server, 
  HelpCircle,
  Clock,
  HardDrive,
  FileCheck,
  ChevronRight,
  ExternalLink
} from 'lucide-react';
import { toast } from 'sonner';

export default function Evidence() {
  const [evidence, setEvidence] = useState([]);
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [searchParams] = useSearchParams();

  // Recovery Pipeline state
  const [isRecovering, setIsRecovering] = useState(false);
  const [recoveringEvidenceId, setRecoveringEvidenceId] = useState(null);
  const [recoveryProgress, setRecoveryProgress] = useState(null);
  const [recoveryData, setRecoveryData] = useState(null);
  
  // Selected files for restoration
  const [selectedRecoveredFiles, setSelectedRecoveredFiles] = useState([]);
  const [restorationDest, setRestorationDest] = useState('download_local');
  const [isRestoring, setIsRestoring] = useState(false);
  const [restorationStatus, setRestorationStatus] = useState(null);
  
  // Active selected file details for metadata inspection
  const [selectedFileDetails, setSelectedFileDetails] = useState(null);
  
  // Integrity & AI prediction states
  const [integrityResults, setIntegrityResults] = useState({});
  const [verifyingIds, setVerifyingIds] = useState(new Set());

  // Devices & Diagnostics states
  const [detectedDevices, setDetectedDevices] = useState([]);
  const [loadingDevices, setLoadingDevices] = useState(false);
  const [customPathOverride, setCustomPathOverride] = useState(false);
  const [diagnosticsResult, setDiagnosticsResult] = useState(null);
  const [runningDiagnostics, setRunningDiagnostics] = useState(false);

  const [formData, setFormData] = useState({
    case_id: localStorage.getItem('current_case_id') || '',
    evidence_type: 'disk_image',
    file_name: '',
    description: ''
  });

  useEffect(() => {
    fetchEvidence();
    fetchCases();
    fetchDevices();
  }, []);

  const fetchDevices = async () => {
    setLoadingDevices(true);
    try {
      const response = await devicesAPI.getDevices();
      setDetectedDevices(response.data.devices || []);
    } catch (err) {
      console.error('Failed to fetch devices:', err);
    } finally {
      setLoadingDevices(false);
    }
  };

  const runDiagnosticsForPath = async (path) => {
    if (!path) {
      setDiagnosticsResult(null);
      return;
    }
    setRunningDiagnostics(true);
    setDiagnosticsResult(null);
    try {
      const response = await devicesAPI.runDiagnostics({ device_path: path });
      setDiagnosticsResult(response.data);
    } catch (err) {
      toast.error('Diagnostics failed: ' + (err.response?.data?.error || err.message));
      setDiagnosticsResult({
        success: false,
        error: err.response?.data?.error || err.message,
        checks: {
          docker_environment: { status: 'failed', label: 'Docker Environment Check', message: 'Unable to verify Docker status' },
          drive_existence: { status: 'failed', label: 'Drive Existence Check', message: 'Path inaccessible' },
          read_permissions: { status: 'failed', label: 'Read Permission Check', message: 'Access denied' },
          forensic_tools: { status: 'failed', label: 'Forensic Tools Check', message: 'Tools unavailable' }
        },
        logs: ['Failed to run diagnostics api call.'],
        recommended_action: 'Please ensure backend server is running and accessible.'
      });
    } finally {
      setRunningDiagnostics(false);
    }
  };

  const fetchEvidence = async () => {
    setLoading(true);
    try {
      const response = await evidenceAPI.getEvidence();
      setEvidence(response.data);
    } catch (err) {
      setError('Failed to fetch evidence: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const fetchCases = async () => {
    try {
      const response = await casesAPI.getCases();
      setCases(response.data);
    } catch (err) {
      console.error('Failed to fetch cases:', err);
    }
  };

  const handleVerifyIntegrity = async (id) => {
    setVerifyingIds(prev => {
      const next = new Set(prev);
      next.add(id);
      return next;
    });
    try {
      const response = await evidenceAPI.verifyIntegrity(id);
      setIntegrityResults(prev => ({
        ...prev,
        [id]: response.data
      }));
      if (response.data.status.includes('Verified')) {
        toast.success(`Integrity verified successfully for evidence file!`);
      } else {
        toast.error(`Warning: Evidence file integrity mismatch detected!`);
      }
    } catch (err) {
      toast.error('Failed to verify evidence integrity: ' + (err.response?.data?.error || err.message));
    } finally {
      setVerifyingIds(prev => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  const handleRecoverAndAnalyze = async (id) => {
    setIsRecovering(true);
    setRecoveringEvidenceId(id);
    setSelectedFileDetails(null);
    setRecoveryProgress({
      evidence_id: id,
      currentStep: 'connection',
      steps: {
        connection: { status: 'pending', label: 'Device Connected' },
        scan: { status: 'idle', label: 'Device Scan Completed' },
        deleted_detection: { status: 'idle', label: 'Deleted Files Detected' },
        metadata_extraction: { status: 'idle', label: 'Metadata Extraction Completed' },
        recovery_engine: { status: 'idle', label: 'Recovery Engine Running' },
        filesystem_analysis: { status: 'idle', label: 'Filesystem Analysis Completed' },
        timeline_reconstruction: { status: 'idle', label: 'Timeline Reconstruction Completed' },
        ai_investigation: { status: 'idle', label: 'AI Investigation Completed' },
        report_generation: { status: 'idle', label: 'Report Generated' }
      }
    });
    setError(null);
    setRecoveryData(null);
    setSelectedRecoveredFiles([]);

    try {
      const response = await fetch(`http://127.0.0.1:8000/api/evidence/${id}/recover-and-analyze/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (line.trim().startsWith('data: ')) {
            try {
              const event = JSON.parse(line.trim().substring(6));
              
              if (event.status === 'processing') {
                const { step } = event;
                setRecoveryProgress(prev => {
                  if (!prev) return null;
                  const updatedSteps = { ...prev.steps };
                  
                  const stepKeys = Object.keys(updatedSteps);
                  const currentIdx = stepKeys.indexOf(step);
                  
                  stepKeys.forEach((k, idx) => {
                    if (idx < currentIdx) {
                      updatedSteps[k] = { status: 'completed', label: updatedSteps[k].label };
                    } else if (idx === currentIdx) {
                      updatedSteps[k] = { status: 'pending', label: updatedSteps[k].label };
                    }
                  });
                  
                  return {
                    ...prev,
                    currentStep: step,
                    steps: updatedSteps
                  };
                });
              } else if (event.status === 'completed') {
                setRecoveryProgress(prev => {
                  if (!prev) return null;
                  const updatedSteps = { ...prev.steps };
                  Object.keys(updatedSteps).forEach(k => {
                    updatedSteps[k] = { status: 'completed', label: updatedSteps[k].label };
                  });
                  return {
                    ...prev,
                    currentStep: 'report_generation',
                    steps: updatedSteps
                  };
                });
                
                setRecoveryData({
                  recovered_files: event.recovered_files,
                  ai_analysis: event.ai_analysis,
                  evidence_id: id
                });
                setIsRecovering(false);
                setRecoveringEvidenceId(null);
                toast.success('Investigation and recovery pipeline completed successfully!');
              } else if (event.status === 'failed') {
                setError(`Forensic Analysis Failed: ${event.error}`);
                setIsRecovering(false);
                setRecoveringEvidenceId(null);
              }
            } catch (err) {
              console.error('Failed to parse stream event:', err);
            }
          }
        }
      }
    } catch (err) {
      setError(`Connection Error: ${err.message}`);
      setIsRecovering(false);
      setRecoveringEvidenceId(null);
    }
  };

  const handleRestoreSelectedFiles = async (evidenceId) => {
    if (selectedRecoveredFiles.length === 0) {
      toast.error('No files selected for restoration.');
      return;
    }
    
    setIsRestoring(true);
    setRestorationStatus({
      status: 'pending',
      message: `Restoring ${selectedRecoveredFiles.length} files to target destination...`
    });
    
    try {
      const payload = {
        files: selectedRecoveredFiles,
        destination: restorationDest
      };
      const response = await evidenceAPI.restoreFiles(evidenceId, payload);
      
      if (response.data.success) {
        setRestorationStatus({
          status: 'completed',
          message: `Successfully restored ${response.data.restored_count} files to ${restorationDest.replace('_', ' ')}!`
        });
        toast.success(`Successfully restored files!`);
        setSelectedRecoveredFiles([]);
      } else {
        setRestorationStatus({
          status: 'failed',
          message: `Completed with errors: ${response.data.errors.join(', ')}`
        });
        toast.error(`Restoration completed with errors.`);
      }
    } catch (err) {
      const errMsg = err.response?.data?.error || err.message;
      setRestorationStatus({
        status: 'failed',
        message: `Restoration error: ${errMsg}`
      });
      toast.error(`Restoration failed: ${errMsg}`);
    } finally {
      setIsRestoring(false);
    }
  };

  const toggleForm = () => {
    setShowForm(!showForm);
    setError(null);
    setDiagnosticsResult(null);
    setCustomPathOverride(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (diagnosticsResult && !diagnosticsResult.success) {
      toast.error('Cannot register evidence: Diagnostics failed for this device path. Please resolve issues first.');
      return;
    }
    setLoading(true);
    try {
      await evidenceAPI.uploadEvidence(formData);
      toast.success('Evidence registered successfully!');
      fetchEvidence();
      setShowForm(false);
      setFormData({
        case_id: localStorage.getItem('current_case_id') || '',
        evidence_type: 'disk_image',
        file_name: '',
        description: ''
      });
      setDiagnosticsResult(null);
    } catch (err) {
      setError('Failed to add evidence: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteEvidence = async (id) => {
    if (!window.confirm('Are you sure you want to delete this evidence? This is recorded in the chain of custody.')) {
      return;
    }
    try {
      await evidenceAPI.deleteEvidence(id);
      toast.success('Evidence successfully archived and removed.');
      fetchEvidence();
    } catch (err) {
      toast.error('Failed to delete evidence: ' + (err.response?.data?.error || err.message));
    }
  };

  const handleDownloadReport = async (id, fileName) => {
    try {
      const response = await evidenceAPI.downloadReport(id);
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Forensic_Report_${fileName.replace(/\.[^/.]+$/, "")}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Forensic PDF report downloaded successfully.');
    } catch (err) {
      toast.error('Failed to download report: ' + (err.message));
    }
  };

  const handleToggleSelectFile = (file) => {
    setSelectedRecoveredFiles(prev => {
      const index = prev.findIndex(item => item.id === file.id);
      if (index > -1) {
        return prev.filter(item => item.id !== file.id);
      } else {
        return [...prev, file];
      }
    });
  };

  const handleSelectAllFiles = (files) => {
    if (selectedRecoveredFiles.length === files.length) {
      setSelectedRecoveredFiles([]);
    } else {
      setSelectedRecoveredFiles([...files]);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'disk_image': return '💾';
      case 'file': return '📄';
      case 'memory_dump': return '🧠';
      case 'network_capture': return '🌐';
      case 'log_file': return '📝';
      default: return '📁';
    }
  };

  return (
    <div className="p-6 bg-slate-950 text-slate-100 min-h-screen font-sans antialiased select-none">
      {/* Top SOC Dashboard Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs uppercase tracking-widest mb-1">
            <Cpu size={14} className="animate-pulse" />
            <span>AIDFIRS // SECURITY OPERATIONS CENTER</span>
          </div>
          <h1 className="text-3xl font-extrabold text-slate-50 tracking-tight">Evidence Investigation Panel</h1>
        </div>
        <button
          onClick={toggleForm}
          className="bg-slate-900 hover:bg-slate-800 border border-slate-700/60 hover:border-slate-600 text-slate-100 px-5 py-2.5 rounded-lg transition-all text-sm font-semibold shadow-md flex items-center gap-2"
        >
          {showForm ? 'Cancel Operation' : 'Add New Evidence'}
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg mb-6 flex justify-between items-center text-sm font-mono">
          <div className="flex items-center gap-2">
            <AlertTriangle size={16} />
            <span>[ERROR] {error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-200 font-bold">&times;</button>
        </div>
      )}

      {/* New Evidence Input Form */}
      {showForm && (
        <div className="bg-slate-900/65 backdrop-blur-xl rounded-xl border border-slate-800/80 p-6 mb-8 shadow-2xl animate-in fade-in slide-in-from-top-4 duration-300">
          <h2 className="text-xl font-bold text-slate-100 mb-6 flex items-center gap-2">
            <Server size={18} className="text-cyan-400" />
            <span>Register HDD or USB Drive Evidence</span>
          </h2>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-slate-300 text-xs font-bold font-mono uppercase tracking-wider mb-2">
                  Associate Case
                </label>
                <select
                  value={formData.case_id}
                  onChange={(e) => setFormData({ ...formData, case_id: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 text-slate-200 px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/80 transition-all font-sans"
                  required
                >
                  <option value="">Select Target Case</option>
                  {cases.map((c) => (
                    <option key={c._id} value={c._id}>
                      {c.case_number} - {c.title}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-300 text-xs font-bold font-mono uppercase tracking-wider mb-2">
                  Evidence Drive Type
                </label>
                <select
                  value={formData.evidence_type}
                  onChange={(e) => setFormData({ ...formData, evidence_type: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 text-slate-200 px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/80 transition-all font-sans"
                >
                  <option value="disk_image">Forensic Disk Image (Raw/E01)</option>
                  <option value="file">Logical Drive / Removable Partition</option>
                </select>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="block text-slate-300 text-xs font-bold font-mono uppercase tracking-wider">
                  Evidence Drive / Device Path
                </label>
                <div className="flex items-center gap-4">
                  <button
                    type="button"
                    onClick={fetchDevices}
                    className="flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 font-mono font-semibold transition-colors focus:outline-none"
                    disabled={loadingDevices}
                  >
                    <RefreshCw size={12} className={loadingDevices ? 'animate-spin' : ''} />
                    <span>Scan Devices</span>
                  </button>
                  <label className="flex items-center gap-1.5 cursor-pointer text-xs font-semibold text-slate-400 hover:text-slate-300 select-none">
                    <input
                      type="checkbox"
                      checked={customPathOverride}
                      onChange={(e) => {
                        setCustomPathOverride(e.target.checked);
                        setFormData({ ...formData, file_name: '' });
                        setDiagnosticsResult(null);
                      }}
                      className="rounded border-slate-800 text-cyan-500 focus:ring-cyan-500/20 bg-slate-950 cursor-pointer"
                    />
                    <span>Custom Path Override</span>
                  </label>
                </div>
              </div>

              {customPathOverride ? (
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={formData.file_name}
                    onChange={(e) => {
                      setFormData({ ...formData, file_name: e.target.value });
                    }}
                    className="flex-1 bg-slate-950 border border-slate-800 text-slate-200 px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/80 transition-all font-mono text-sm"
                    placeholder="e.g. D:\ or /dev/sdb or /mnt/d"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => runDiagnosticsForPath(formData.file_name)}
                    disabled={runningDiagnostics || !formData.file_name}
                    className="bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700/60 hover:border-slate-600 px-4 py-3 rounded-lg text-xs font-semibold font-mono transition-all flex items-center gap-1.5 disabled:opacity-50"
                  >
                    {runningDiagnostics ? <RefreshCw size={12} className="animate-spin" /> : <Search size={12} />}
                    <span>Diagnose</span>
                  </button>
                </div>
              ) : (
                <select
                  value={formData.file_name}
                  onChange={(e) => {
                    const val = e.target.value;
                    setFormData({ ...formData, file_name: val });
                    runDiagnosticsForPath(val);
                  }}
                  className="w-full bg-slate-950 border border-slate-800 text-slate-200 px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/80 transition-all font-sans text-sm"
                  required
                >
                  <option value="">Select Connected Device Drive</option>
                  {detectedDevices.map((device) => (
                    <option key={device.drive_letter} value={device.drive_letter}>
                      {device.drive_letter} — {device.volume_name || 'Unnamed Volume'} ({device.drive_type}) — {device.size_gb} GB
                    </option>
                  ))}
                  {detectedDevices.length === 0 && !loadingDevices && (
                    <option value="" disabled>No active HDD or USB drives detected. Try clicking "Scan Devices" or use Custom Path Override.</option>
                  )}
                </select>
              )}
            </div>

            {/* Device Diagnostics Panel */}
            {(runningDiagnostics || diagnosticsResult) && (
              <div className="bg-slate-950/80 border border-slate-850 p-5 rounded-lg space-y-4 shadow-inner">
                <div className="flex justify-between items-center border-b border-slate-850 pb-2">
                  <div className="flex items-center gap-2">
                    <Shield size={16} className="text-cyan-400" />
                    <span className="text-xs font-mono font-bold tracking-wider text-slate-300 uppercase">Device Diagnostic Report</span>
                  </div>
                  {runningDiagnostics && (
                    <span className="text-[10px] font-mono text-cyan-400 animate-pulse flex items-center gap-1">
                      <RefreshCw size={10} className="animate-spin" />
                      <span>Diagnosing...</span>
                    </span>
                  )}
                  {diagnosticsResult && !runningDiagnostics && (
                    <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                      diagnosticsResult.success 
                        ? 'bg-green-500/10 text-green-400 border-green-500/20' 
                        : 'bg-red-500/10 text-red-400 border-red-500/20'
                    }`}>
                      {diagnosticsResult.success ? 'PASSED' : 'FAILED'}
                    </span>
                  )}
                </div>

                {diagnosticsResult && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    {Object.entries(diagnosticsResult.checks).map(([key, check]) => (
                      <div key={key} className="flex flex-col p-2.5 bg-slate-900/60 rounded border border-slate-800/60">
                        <div className="flex justify-between items-center mb-1">
                          <span className="font-semibold text-slate-300">{check.label}</span>
                          <span className={`px-2 py-0.5 rounded text-[9px] font-bold font-mono uppercase tracking-wider ${
                            check.status === 'success' 
                              ? 'bg-green-500/10 text-green-400 border-green-500/20' 
                              : check.status === 'warning' 
                              ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' 
                              : 'bg-red-500/10 text-red-400 border-red-500/20'
                          }`}>
                            {check.status}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-400 mt-1 leading-normal font-mono">{check.message}</p>
                      </div>
                    ))}
                  </div>
                )}

                {diagnosticsResult && diagnosticsResult.recommended_action && (
                  <div className="p-3 bg-cyan-950/20 border border-cyan-850 rounded text-xs leading-relaxed text-cyan-300 font-mono">
                    <span className="font-bold text-cyan-400">RECOMMENDED ACTION:</span> {diagnosticsResult.recommended_action}
                  </div>
                )}

                {/* Log terminal console */}
                {diagnosticsResult && diagnosticsResult.logs && diagnosticsResult.logs.length > 0 && (
                  <div className="space-y-1">
                    <span className="text-[10px] text-slate-500 font-mono uppercase font-bold tracking-wider">Diagnostic Console Logs</span>
                    <div className="bg-slate-950 border border-slate-850 p-3 rounded font-mono text-[10px] leading-relaxed text-emerald-450 h-28 overflow-y-auto space-y-1 scrollbar-thin font-semibold">
                      {diagnosticsResult.logs.map((log, index) => (
                        <div key={index} className="flex gap-1">
                          <span className="text-slate-650 select-none">[{index + 1}]</span>
                          <span className={log.includes('Error') ? 'text-red-450' : log.includes('Warning') ? 'text-yellow-450' : 'text-slate-355'}>{log}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            <div>
              <label className="block text-slate-300 text-xs font-bold font-mono uppercase tracking-wider mb-2">
                Chain of Custody Notes / Scope Details
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 text-slate-200 px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/80 transition-all text-sm h-28"
                placeholder="Specify the physical source of the evidence, HDD/USB serial number, and collector details..."
              />
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={loading || runningDiagnostics || (diagnosticsResult && !diagnosticsResult.success)}
                className="bg-cyan-500 hover:bg-cyan-600 text-slate-950 font-bold px-6 py-3 rounded-lg transition-all shadow-md shadow-cyan-500/10 text-sm disabled:opacity-50"
              >
                {loading ? 'Registering...' : 'Register Evidence Source'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Main Grid View */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Side: Registered Evidence Items */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-slate-900/60 backdrop-blur-xl rounded-xl border border-slate-800/80 p-5 shadow-2xl">
            <div className="flex items-center gap-2 border-b border-slate-800 pb-4 mb-4">
              <Database size={16} className="text-cyan-400" />
              <h2 className="text-lg font-bold text-slate-100">Evidence Library</h2>
            </div>
            
            {loading && !showForm ? (
              <div className="p-8 text-center text-slate-500 font-mono text-sm flex items-center justify-center gap-2">
                <RefreshCw size={14} className="animate-spin text-cyan-400" />
                <span>Scanning digital forensic workspace...</span>
              </div>
            ) : evidence.length === 0 ? (
              <div className="p-8 text-center text-slate-500 font-mono text-xs">
                No active evidence registry detected.
              </div>
            ) : (
              <div className="space-y-4">
                {evidence.map((item) => (
                  <div 
                    key={item._id} 
                    className={`p-4 rounded-lg border transition-all cursor-pointer ${
                      recoveringEvidenceId === item._id || (recoveryData && recoveryData.evidence_id === item._id)
                        ? 'bg-slate-950/80 border-cyan-500/50 shadow-md shadow-cyan-500/5'
                        : 'bg-slate-950/50 border-slate-800/80 hover:border-slate-700'
                    }`}
                    onClick={() => {
                      if (!isRecovering) {
                        setRecoveringEvidenceId(item._id);
                      }
                    }}
                  >
                    <div className="flex justify-between items-start gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">{getTypeIcon(item.evidence_type)}</span>
                        <div>
                          <h3 className="font-semibold text-slate-200 text-sm truncate max-w-[150px]">{item.file_name}</h3>
                          <span className="text-[10px] font-mono text-slate-500 block uppercase tracking-wider">
                            {item.evidence_type.replace('_', ' ')}
                          </span>
                        </div>
                      </div>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        item.status === 'analyzed' 
                          ? 'bg-green-500/10 text-green-400 border border-green-500/20' 
                          : 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20'
                      }`}>
                        {item.status}
                      </span>
                    </div>

                    {item.description && (
                      <p className="text-xs text-slate-400 line-clamp-2 mb-3 bg-slate-900/30 p-2 rounded border border-slate-800/20">
                        {item.description}
                      </p>
                    )}

                    <div className="flex flex-wrap gap-2 text-[10px] font-mono text-slate-500 mb-4">
                      <div><span className="text-slate-400">Size:</span> {formatFileSize(item.file_size)}</div>
                      {item.hash_sha256 && (
                        <div className="w-full text-slate-400 overflow-hidden text-ellipsis whitespace-nowrap">
                          <span>SHA256:</span> <span className="text-[9px] bg-slate-900 px-1 py-0.5 rounded text-cyan-500/80">{item.hash_sha256}</span>
                        </div>
                      )}
                    </div>

                    <div className="flex flex-col gap-2 pt-2 border-t border-slate-800/60">
                      {/* Unified button */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRecoverAndAnalyze(item._id);
                        }}
                        disabled={isRecovering}
                        className="w-full bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-700 hover:to-cyan-600 text-slate-950 font-bold py-2 px-3 rounded text-xs transition-all shadow-md shadow-cyan-500/10 flex items-center justify-center gap-1 border border-cyan-400/20 disabled:opacity-50"
                      >
                        <Search size={12} />
                        <span>Recover & Analyze Evidence</span>
                      </button>

                      {/* Secondary Integrity Verifier */}
                      <div className="flex justify-between items-center gap-2 mt-1">
                        {integrityResults[item._id] ? (
                          <span className={`text-[10px] font-mono font-bold flex items-center gap-1 ${
                            integrityResults[item._id].status.includes('Verified') ? 'text-green-400' : 'text-red-400'
                          }`}>
                            <Shield size={10} />
                            <span>{integrityResults[item._id].status}</span>
                          </span>
                        ) : (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleVerifyIntegrity(item._id);
                            }}
                            disabled={verifyingIds.has(item._id)}
                            className="text-[10px] font-mono font-semibold text-slate-400 hover:text-cyan-400 transition-colors flex items-center gap-1"
                          >
                            <Shield size={10} />
                            <span>{verifyingIds.has(item._id) ? 'Verifying...' : 'Verify Cryptographic Integrity'}</span>
                          </button>
                        )}

                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDownloadReport(item._id, item.file_name);
                          }}
                          className="text-[10px] font-mono text-slate-400 hover:text-cyan-400 flex items-center gap-1 ml-auto"
                        >
                          <Download size={10} />
                          <span>PDF Report</span>
                        </button>
                        
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteEvidence(item._id);
                          }}
                          className="text-[10px] font-mono text-red-500 hover:text-red-400 flex items-center"
                        >
                          <Trash2 size={10} />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Side: Active Recovery, Progress Tracker, and Workspace */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Recovery Progress Checkmarks Panel */}
          {recoveryProgress && (
            <div className="bg-slate-900/60 backdrop-blur-xl rounded-xl border border-slate-800/80 p-6 shadow-2xl animate-in fade-in duration-300">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
                <div className="flex items-center gap-2">
                  <Cpu size={16} className="text-cyan-400 animate-spin" />
                  <h2 className="text-lg font-bold text-slate-100">Forensic Recovery Progress</h2>
                </div>
                <span className="text-[10px] font-mono bg-slate-950 text-cyan-400 px-2 py-0.5 rounded border border-cyan-500/20">
                  PIPELINE SCANNING
                </span>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(recoveryProgress.steps).map(([key, step]) => (
                  <div key={key} className="flex items-center gap-3 p-3 bg-slate-950/60 rounded-lg border border-slate-900">
                    <div className="flex-shrink-0">
                      {step.status === 'completed' ? (
                        <div className="h-5 w-5 bg-green-500/10 rounded-full border border-green-500/30 flex items-center justify-center">
                          <Check size={12} className="text-green-400" />
                        </div>
                      ) : step.status === 'pending' ? (
                        <div className="h-5 w-5 bg-cyan-500/10 rounded-full border border-cyan-500/30 flex items-center justify-center animate-spin">
                          <RefreshCw size={10} className="text-cyan-400" />
                        </div>
                      ) : (
                        <div className="h-5 w-5 bg-slate-800/50 rounded-full border border-slate-800 flex items-center justify-center">
                          <div className="h-1.5 w-1.5 bg-slate-600 rounded-full" />
                        </div>
                      )}
                    </div>
                    <span className={`text-xs font-mono tracking-wide ${
                      step.status === 'completed' 
                        ? 'text-slate-300 font-semibold' 
                        : step.status === 'pending' 
                        ? 'text-cyan-400 font-bold animate-pulse' 
                        : 'text-slate-500'
                    }`}>
                      {step.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recovered Files Table Workspace */}
          {recoveryData && (
            <div className="bg-slate-900/60 backdrop-blur-xl rounded-xl border border-slate-800/80 p-6 shadow-2xl animate-in fade-in duration-300">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-4 mb-6">
                <div>
                  <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                    <Folder size={18} className="text-cyan-400" />
                    <span>Recovered Files Workspace</span>
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Checkboxes select items. Use the restoration controller below to write selected items to targets.
                  </p>
                </div>
                <div className="flex items-center gap-2 text-xs font-mono bg-slate-950 border border-slate-800 px-3 py-1.5 rounded-lg">
                  <span className="text-slate-500">Total Found:</span>
                  <span className="text-cyan-400 font-bold">{recoveryData.recovered_files?.length || 0}</span>
                </div>
              </div>

              {/* Table / List Workspace */}
              <div className="overflow-x-auto border border-slate-800/80 rounded-lg max-h-96 overflow-y-auto mb-6 bg-slate-950/40">
                <table className="min-w-full divide-y divide-slate-800/80">
                  <thead className="bg-slate-900/80 font-mono text-[10px] text-slate-400 uppercase tracking-wider">
                    <tr>
                      <th scope="col" className="w-12 px-4 py-3 text-left">
                        <input
                          type="checkbox"
                          checked={selectedRecoveredFiles.length === recoveryData.recovered_files.length}
                          onChange={() => handleSelectAllFiles(recoveryData.recovered_files)}
                          className="rounded border-slate-800 text-cyan-500 focus:ring-cyan-500/20 bg-slate-950"
                        />
                      </th>
                      <th scope="col" className="px-4 py-3 text-left">File Name</th>
                      <th scope="col" className="px-4 py-3 text-left">Type</th>
                      <th scope="col" className="px-4 py-3 text-left">Original Location</th>
                      <th scope="col" className="px-4 py-3 text-left">Size</th>
                      <th scope="col" className="px-4 py-3 text-left">Confidence</th>
                      <th scope="col" className="w-16 px-4 py-3 text-center">Inspect</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-900 text-xs font-sans text-slate-300">
                    {recoveryData.recovered_files.map((file) => (
                      <tr 
                        key={file.id} 
                        className={`hover:bg-slate-900/40 transition-colors ${
                          selectedRecoveredFiles.some(f => f.id === file.id) ? 'bg-cyan-500/5' : ''
                        }`}
                      >
                        <td className="px-4 py-3 whitespace-nowrap">
                          <input
                            type="checkbox"
                            checked={selectedRecoveredFiles.some(f => f.id === file.id)}
                            onChange={() => handleToggleSelectFile(file)}
                            className="rounded border-slate-800 text-cyan-500 focus:ring-cyan-500/20 bg-slate-950 cursor-pointer"
                          />
                        </td>
                        <td className="px-4 py-3 font-semibold text-slate-200 truncate max-w-[150px]">{file.file_name}</td>
                        <td className="px-4 py-3 font-mono text-[10px] text-slate-400">{file.file_type}</td>
                        <td className="px-4 py-3 font-mono text-[10px] text-slate-500 max-w-[200px] truncate">{file.original_location}</td>
                        <td className="px-4 py-3 whitespace-nowrap">{formatFileSize(file.file_size)}</td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${
                            file.recovery_confidence.includes('High') 
                              ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                              : 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20'
                          }`}>
                            {file.recovery_confidence}
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-center">
                          <button
                            onClick={() => setSelectedFileDetails(file)}
                            className="p-1 text-slate-400 hover:text-cyan-400 transition-colors"
                          >
                            <ChevronRight size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Restore Selected Files Controls */}
              <div className="bg-slate-950/80 border border-slate-800/80 p-5 rounded-lg flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div className="space-y-1">
                  <span className="text-xs font-mono text-cyan-400 font-bold tracking-wide uppercase">Restoration Controller</span>
                  <div className="text-sm font-semibold text-slate-200">
                    {selectedRecoveredFiles.length} file(s) selected
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
                  <select
                    value={restorationDest}
                    onChange={(e) => setRestorationDest(e.target.value)}
                    className="bg-slate-900 border border-slate-800 text-slate-200 px-3 py-2 rounded text-xs focus:outline-none focus:ring-1 focus:ring-cyan-500/40"
                  >
                    <option value="original_device">Restore to Original Device</option>
                    <option value="usb_drive">Restore to Connected USB</option>
                    <option value="download_local">Download Locally (Direct HTTP)</option>
                    <option value="export_location">Export to Secure Forensic folder</option>
                  </select>

                  <button
                    onClick={() => handleRestoreSelectedFiles(recoveryData.evidence_id)}
                    disabled={isRestoring || selectedRecoveredFiles.length === 0}
                    className="bg-cyan-500 hover:bg-cyan-600 disabled:bg-slate-800 disabled:border-slate-700/60 disabled:text-slate-500 border border-cyan-400/20 text-slate-950 font-bold px-4 py-2 rounded text-xs transition-all flex items-center gap-1.5 shadow-md shadow-cyan-500/5"
                  >
                    <FileCheck size={14} />
                    <span>Restore Selected Files</span>
                  </button>
                </div>
              </div>

              {/* Restoring progress notice */}
              {restorationStatus && (
                <div className={`mt-4 p-4 border rounded-lg text-xs font-mono flex items-center gap-2 ${
                  restorationStatus.status === 'completed'
                    ? 'bg-green-500/10 border-green-500/20 text-green-400'
                    : restorationStatus.status === 'failed'
                    ? 'bg-red-500/10 border-red-500/20 text-red-400'
                    : 'bg-cyan-500/10 border-cyan-500/20 text-cyan-400 animate-pulse'
                }`}>
                  {restorationStatus.status === 'pending' && <RefreshCw size={14} className="animate-spin" />}
                  <span>{restorationStatus.message}</span>
                </div>
              )}
            </div>
          )}

          {/* Real Metadata Inspection Panel */}
          {selectedFileDetails && (
            <div className="bg-slate-900/60 backdrop-blur-xl rounded-xl border border-slate-800/80 p-6 shadow-2xl animate-in fade-in duration-300">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
                <div className="flex items-center gap-2">
                  <FileText size={18} className="text-cyan-400" />
                  <h3 className="text-base font-bold text-slate-100">Metadata Analyzer: {selectedFileDetails.file_name}</h3>
                </div>
                <button
                  onClick={() => setSelectedFileDetails(null)}
                  className="text-slate-500 hover:text-slate-300 font-bold text-sm"
                >
                  Close
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono bg-slate-950/80 border border-slate-800/60 p-4 rounded-lg">
                <div className="space-y-2">
                  <div><span className="text-slate-500">File Name:</span> <span className="text-slate-300">{selectedFileDetails.metadata.file_name || 'N/A'}</span></div>
                  <div><span className="text-slate-500">Extension:</span> <span className="text-slate-300">{selectedFileDetails.metadata.extension || 'N/A'}</span></div>
                  <div><span className="text-slate-500">File Size:</span> <span className="text-slate-300">{formatFileSize(selectedFileDetails.metadata.file_size)} ({selectedFileDetails.metadata.file_size} bytes)</span></div>
                  <div><span className="text-slate-500">File Owner:</span> <span className="text-slate-300">{selectedFileDetails.metadata.file_owner || 'N/A'}</span></div>
                </div>
                <div className="space-y-2">
                  <div><span className="text-slate-500">Date Created:</span> <span className="text-slate-300">{selectedFileDetails.metadata.created_date || 'N/A'}</span></div>
                  <div><span className="text-slate-500">Date Modified:</span> <span className="text-slate-300">{selectedFileDetails.metadata.modified_date || 'N/A'}</span></div>
                  <div><span className="text-slate-500">Date Accessed:</span> <span className="text-slate-300">{selectedFileDetails.metadata.accessed_date || 'N/A'}</span></div>
                </div>

                {/* Optional ExifTool Real Coordinates, Device, and Camera metadata */}
                {(selectedFileDetails.metadata.gps_coordinates || 
                  selectedFileDetails.metadata.camera_information || 
                  selectedFileDetails.metadata.device_information) && (
                  <div className="col-span-2 pt-3 border-t border-slate-850 mt-2 space-y-2">
                    <span className="text-[10px] text-cyan-400 uppercase tracking-widest font-bold block mb-1">Extended Exif Metadata</span>
                    {selectedFileDetails.metadata.gps_coordinates && (
                      <div><span className="text-slate-500">GPS Coordinates:</span> <span className="text-slate-200">{selectedFileDetails.metadata.gps_coordinates}</span></div>
                    )}
                    {selectedFileDetails.metadata.camera_information && (
                      <div><span className="text-slate-500">Camera Information:</span> <span className="text-slate-200">{selectedFileDetails.metadata.camera_information}</span></div>
                    )}
                    {selectedFileDetails.metadata.device_information && (
                      <div><span className="text-slate-500">Device Information:</span> <span className="text-slate-200">{selectedFileDetails.metadata.device_information}</span></div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* AI Forensic Analysis Report Container */}
          {recoveryData && recoveryData.ai_analysis && (
            <div className="bg-slate-900/60 backdrop-blur-xl rounded-xl border border-slate-800/80 p-6 shadow-2xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
                <div className="flex items-center gap-2">
                  <Cpu size={18} className="text-cyan-400" />
                  <h3 className="text-base font-bold text-slate-100">FIE-LLM Investigative Report</h3>
                </div>
                <span className="text-[10px] font-mono text-slate-500">CLAUDE-3-5-SONNET</span>
              </div>
              <pre className="text-xs font-mono text-cyan-400 bg-slate-950 p-4 rounded-lg overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-[350px]">
                {recoveryData.ai_analysis.report || recoveryData.ai_analysis.response || JSON.stringify(recoveryData.ai_analysis, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
