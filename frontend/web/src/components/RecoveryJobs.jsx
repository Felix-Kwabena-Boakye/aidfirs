import React, { useState, useEffect, useCallback } from 'react';
import { recoveryAPI, casesAPI, devicesAPI } from '../api';
import {
  Cpu, RefreshCw, Plus, ChevronDown, ChevronRight, Clock,
  CheckCircle, XCircle, AlertCircle, Loader, FileSearch,
  X, Play, Activity
} from 'lucide-react';
import { toast } from 'sonner';

const STATUS_CONFIG = {
  PENDING:         { color: 'bg-gray-600 text-gray-200',     icon: Clock,        label: 'Pending' },
  RUNNING:         { color: 'bg-yellow-600/80 text-yellow-100', icon: Loader,    label: 'Running', pulse: true },
  SCANNING:        { color: 'bg-blue-600/80 text-blue-100',   icon: FileSearch,  label: 'Scanning', pulse: true },
  FILE_CARVING:    { color: 'bg-purple-600/80 text-purple-100', icon: Activity,  label: 'Carving', pulse: true },
  COMPLETED:       { color: 'bg-green-600/80 text-green-100', icon: CheckCircle, label: 'Completed' },
  FAILED:          { color: 'bg-red-600/80 text-red-100',     icon: XCircle,     label: 'Failed' },
  DEVICE_DETECTION:{ color: 'bg-cyan-600/80 text-cyan-100',   icon: Cpu,         label: 'Detecting Device', pulse: true },
  DISK_IMAGING:    { color: 'bg-orange-600/80 text-orange-100', icon: Activity,  label: 'Imaging Disk', pulse: true },
  UPLOADING_METADATA: { color: 'bg-indigo-600/80 text-indigo-100', icon: Loader, label: 'Uploading', pulse: true },
};

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG['PENDING'];
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${cfg.color}`}>
      <Icon className={`w-3 h-3 ${cfg.pulse ? 'animate-spin' : ''}`} />
      {cfg.label}
    </span>
  );
}

function ProgressBar({ value }) {
  const pct = Math.min(100, Math.max(0, value || 0));
  return (
    <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
      <div
        className="h-full rounded-full bg-gradient-to-r from-blue-500 to-cyan-400 transition-all duration-500"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function formatDuration(start, end) {
  if (!start) return '—';
  const s = new Date(start);
  const e = end ? new Date(end) : new Date();
  const secs = Math.floor((e - s) / 1000);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ${secs % 60}s`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m`;
}

function JobRow({ job, onRefresh }) {
  const [expanded, setExpanded] = useState(false);
  const inProgress = !['COMPLETED', 'FAILED', 'PENDING'].includes(job.status);

  return (
    <>
      <tr
        className="hover:bg-gray-700/30 transition-colors cursor-pointer"
        onClick={() => setExpanded(e => !e)}
      >
        <td className="py-3 px-4">
          {expanded ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
        </td>
        <td className="py-3 px-4 font-mono text-xs text-gray-300">{String(job.id || job._id).slice(0, 8)}…</td>
        <td className="py-3 px-4 text-sm text-gray-200 truncate max-w-[140px]">{job.case_id?.slice(0, 8)}…</td>
        <td className="py-3 px-4 font-mono text-xs text-gray-400">{job.device_id?.slice(0, 8)}…</td>
        <td className="py-3 px-4">
          <span className="px-2 py-0.5 bg-gray-700 text-gray-300 text-xs rounded">{job.recovery_type}</span>
        </td>
        <td className="py-3 px-4"><StatusBadge status={job.status} /></td>
        <td className="py-3 px-4 text-sm text-gray-300">{job.stage || '—'}</td>
        <td className="py-3 px-4 min-w-[120px]">
          <div className="flex items-center gap-2">
            <ProgressBar value={job.progress} />
            <span className="text-xs text-gray-400 w-8 text-right">{job.progress}%</span>
          </div>
        </td>
        <td className="py-3 px-4 text-sm text-blue-300 font-semibold">{job.files_found}</td>
        <td className="py-3 px-4 text-xs text-gray-400">
          {job.start_time ? new Date(job.start_time).toLocaleString() : '—'}
        </td>
        <td className="py-3 px-4 text-xs text-gray-400">
          {formatDuration(job.start_time, job.completion_time)}
          {inProgress && <span className="ml-1 text-yellow-400 animate-pulse">●</span>}
        </td>
      </tr>
      {expanded && (
        <tr className="bg-gray-850">
          <td colSpan={11} className="px-6 py-4 border-t border-gray-700/40">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Full Job ID</p>
                <p className="font-mono text-gray-300 text-xs break-all">{job.id || job._id}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Case ID</p>
                <p className="font-mono text-gray-300 text-xs break-all">{job.case_id}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Device ID</p>
                <p className="font-mono text-gray-300 text-xs break-all">{job.device_id}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Completion Time</p>
                <p className="text-gray-300 text-xs">{job.completion_time ? new Date(job.completion_time).toLocaleString() : 'In Progress'}</p>
              </div>
              {job.error_message && (
                <div className="col-span-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Error</p>
                  <p className="text-red-400 text-xs bg-red-900/20 border border-red-800/40 rounded p-2">{job.error_message}</p>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function RecoveryJobs() {
  const [jobs, setJobs] = useState([]);
  const [cases, setCases] = useState([]);
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterStatus, setFilterStatus] = useState('');
  const [filterCase, setFilterCase] = useState('');
  const [showNewModal, setShowNewModal] = useState(false);
  const [newJob, setNewJob] = useState({ case_id: '', device_id: '', recovery_type: 'full' });
  const [submitting, setSubmitting] = useState(false);

  const fetchJobs = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const params = {};
      if (filterStatus) params.status = filterStatus;
      if (filterCase) params.case_id = filterCase;
      const res = await recoveryAPI.getJobs(params);
      setJobs(res.data.jobs || []);
    } catch {
      if (!quiet) toast.error('Failed to load recovery jobs.');
    } finally {
      if (!quiet) setLoading(false);
    }
  }, [filterStatus, filterCase]);

  useEffect(() => {
    casesAPI.getCases().then(r => setCases(r.data || [])).catch(() => {});
    devicesAPI.getDevices().then(r => setDevices(r.data?.devices || r.data || [])).catch(() => {});
  }, []);

  useEffect(() => { fetchJobs(); }, [fetchJobs]);

  // Auto-refresh if any job is in progress
  useEffect(() => {
    const hasActive = jobs.some(j => !['COMPLETED', 'FAILED'].includes(j.status));
    if (!hasActive) return;
    const timer = setInterval(() => fetchJobs(true), 5000);
    return () => clearInterval(timer);
  }, [jobs, fetchJobs]);

  const handleStartJob = async (e) => {
    e.preventDefault();
    if (!newJob.case_id || !newJob.device_id) {
      toast.error('Please select a case and device.');
      return;
    }
    setSubmitting(true);
    try {
      await recoveryAPI.startRecovery(newJob);
      toast.success('Recovery job created successfully!');
      setShowNewModal(false);
      setNewJob({ case_id: '', device_id: '', recovery_type: 'full' });
      fetchJobs();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to start recovery job.');
    } finally {
      setSubmitting(false);
    }
  };

  const activeJobs = jobs.filter(j => !['COMPLETED', 'FAILED'].includes(j.status)).length;

  return (
    <div className="p-6 min-h-screen bg-gray-900 text-white">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Cpu className="w-7 h-7 text-blue-500" />
              Recovery Jobs
            </h1>
            <p className="text-gray-400 text-sm mt-1">
              Manage and monitor forensic data recovery operations.
              {activeJobs > 0 && (
                <span className="ml-2 text-yellow-400 animate-pulse font-medium">
                  {activeJobs} active job{activeJobs > 1 ? 's' : ''}
                </span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchJobs()}
              disabled={loading}
              className="p-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-gray-300 transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={() => setShowNewModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-semibold transition-colors"
            >
              <Plus className="w-4 h-4" />
              New Recovery Job
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 mb-5">
          <select
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg p-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">All Statuses</option>
            {['PENDING', 'RUNNING', 'SCANNING', 'FILE_CARVING', 'COMPLETED', 'FAILED'].map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <select
            value={filterCase}
            onChange={e => setFilterCase(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg p-2 focus:ring-blue-500 focus:border-blue-500 min-w-[180px]"
          >
            <option value="">All Cases</option>
            {cases.map(c => (
              <option key={c._id} value={c._id}>{c.case_number} — {c.title}</option>
            ))}
          </select>
        </div>

        {/* Table */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden shadow-xl">
          {loading && jobs.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 gap-3">
              <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
              <p className="text-gray-400 text-sm">Loading recovery jobs…</p>
            </div>
          ) : jobs.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 gap-3 text-center p-8">
              <Cpu className="w-14 h-14 text-gray-600" />
              <h2 className="text-lg font-semibold text-gray-300">No Recovery Jobs Found</h2>
              <p className="text-gray-500 text-sm max-w-md">
                No forensic recovery jobs exist yet. Create a new job to begin data recovery from a connected device.
              </p>
              <button
                onClick={() => setShowNewModal(true)}
                className="mt-2 flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-semibold transition-colors"
              >
                <Plus className="w-4 h-4" /> Start First Recovery Job
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="bg-gray-900 border-b border-gray-700 text-gray-400 text-xs font-semibold uppercase tracking-wider">
                    <th className="py-3 px-4 w-8" />
                    <th className="py-3 px-4">Job ID</th>
                    <th className="py-3 px-4">Case</th>
                    <th className="py-3 px-4">Device</th>
                    <th className="py-3 px-4">Type</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Stage</th>
                    <th className="py-3 px-4 min-w-[150px]">Progress</th>
                    <th className="py-3 px-4">Files</th>
                    <th className="py-3 px-4">Started</th>
                    <th className="py-3 px-4">Duration</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700/50">
                  {jobs.map(job => (
                    <JobRow key={job.id || job._id} job={job} onRefresh={fetchJobs} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* New Job Modal */}
        {showNewModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            <div className="bg-gray-800 border border-gray-700 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
              <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
                <h3 className="text-lg font-bold flex items-center gap-2">
                  <Play className="w-5 h-5 text-blue-400" />
                  New Recovery Job
                </h3>
                <button onClick={() => setShowNewModal(false)} className="text-gray-400 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <form onSubmit={handleStartJob} className="p-6 space-y-4">
                <div>
                  <label className="block text-xs text-gray-400 uppercase tracking-wider mb-1.5">Case *</label>
                  <select
                    value={newJob.case_id}
                    onChange={e => setNewJob(j => ({ ...j, case_id: e.target.value }))}
                    required
                    className="w-full bg-gray-900 border border-gray-600 text-white text-sm rounded-lg p-2.5 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">— Select Case —</option>
                    {cases.map(c => (
                      <option key={c._id} value={c._id}>{c.case_number} — {c.title}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 uppercase tracking-wider mb-1.5">Target Device *</label>
                  <select
                    value={newJob.device_id}
                    onChange={e => setNewJob(j => ({ ...j, device_id: e.target.value }))}
                    required
                    className="w-full bg-gray-900 border border-gray-600 text-white text-sm rounded-lg p-2.5 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">— Select Device —</option>
                    {devices.map(d => (
                      <option key={d._id || d.device_id} value={d._id || d.device_id}>
                        {d.device_name || d.model || 'Unknown Device'} ({d.drive_letter || d.device_id?.slice(0, 8)})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 uppercase tracking-wider mb-1.5">Recovery Type</label>
                  <select
                    value={newJob.recovery_type}
                    onChange={e => setNewJob(j => ({ ...j, recovery_type: e.target.value }))}
                    className="w-full bg-gray-900 border border-gray-600 text-white text-sm rounded-lg p-2.5 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="full">Full Recovery (Carving + Recycle Bin)</option>
                    <option value="quick">Quick Scan (Recycle Bin Only)</option>
                    <option value="imaging">Disk Imaging Only (RAW DD)</option>
                  </select>
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowNewModal(false)}
                    className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-5 py-2 text-sm bg-blue-600 hover:bg-blue-500 rounded-lg font-semibold transition-colors flex items-center gap-2 disabled:opacity-60"
                  >
                    {submitting ? <Loader className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                    {submitting ? 'Starting…' : 'Start Recovery'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
