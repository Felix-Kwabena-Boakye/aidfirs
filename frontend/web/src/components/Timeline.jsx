import React, { useState, useEffect, useCallback } from 'react';
import { timelineAPI, casesAPI } from '../api';
import {
  Clock, Download, RefreshCw, Filter, Shield, HardDrive,
  FileCheck, Hash, FileDown, PackageOpen, Eye, FileText,
  AlertCircle, CheckSquare, ChevronDown, RotateCcw
} from 'lucide-react';
import { toast } from 'sonner';

const EVENT_TYPES = [
  'RECOVERY_STARTED', 'FILE_RECOVERED', 'HASH_VERIFIED', 'FILE_DOWNLOADED',
  'IMAGE_CREATED', 'CASE_EXPORTED', 'FILE_PREVIEWED', 'REPORT_GENERATED',
  'HASH_CREATED', 'FILE_ANALYZED', 'RECOVERY_COMPLETED', 'RECOVERY_FAILED'
];

const EVENT_CONFIG = {
  RECOVERY_STARTED:   { color: 'bg-blue-500',    textColor: 'text-blue-400',    icon: HardDrive,   label: 'Recovery Started' },
  FILE_RECOVERED:     { color: 'bg-green-500',   textColor: 'text-green-400',   icon: FileCheck,   label: 'File Recovered' },
  HASH_VERIFIED:      { color: 'bg-purple-500',  textColor: 'text-purple-400',  icon: Hash,        label: 'Hash Verified' },
  FILE_DOWNLOADED:    { color: 'bg-teal-500',    textColor: 'text-teal-400',    icon: FileDown,    label: 'File Downloaded' },
  IMAGE_CREATED:      { color: 'bg-orange-500',  textColor: 'text-orange-400',  icon: HardDrive,   label: 'Image Created' },
  CASE_EXPORTED:      { color: 'bg-indigo-500',  textColor: 'text-indigo-400',  icon: PackageOpen, label: 'Case Exported' },
  FILE_PREVIEWED:     { color: 'bg-yellow-500',  textColor: 'text-yellow-400',  icon: Eye,         label: 'File Previewed' },
  REPORT_GENERATED:   { color: 'bg-pink-500',    textColor: 'text-pink-400',    icon: FileText,    label: 'Report Generated' },
  HASH_CREATED:       { color: 'bg-violet-500',  textColor: 'text-violet-400',  icon: Shield,      label: 'Hash Created' },
  RECOVERY_COMPLETED: { color: 'bg-emerald-500', textColor: 'text-emerald-400', icon: CheckSquare, label: 'Recovery Completed' },
  RECOVERY_FAILED:    { color: 'bg-red-500',     textColor: 'text-red-400',     icon: AlertCircle, label: 'Recovery Failed' },
  default:            { color: 'bg-gray-500',    textColor: 'text-gray-400',    icon: Clock,       label: 'Event' },
};

function getEventCfg(type) {
  return EVENT_CONFIG[type] || EVENT_CONFIG.default;
}

function relativeTime(ts) {
  if (!ts) return '';
  const now = new Date();
  const then = new Date(ts);
  const diff = Math.floor((now - then) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function TimelineEventItem({ event }) {
  const cfg = getEventCfg(event.event_type);
  const Icon = cfg.icon;
  return (
    <div className="flex gap-4 group">
      {/* Dot and line */}
      <div className="flex flex-col items-center">
        <div className={`w-9 h-9 rounded-full ${cfg.color} flex items-center justify-center flex-shrink-0 shadow-lg`}>
          <Icon className="w-4 h-4 text-white" />
        </div>
        <div className="flex-1 w-0.5 bg-gray-700 mt-1" />
      </div>
      {/* Content */}
      <div className="pb-6 flex-1">
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 shadow group-hover:border-gray-600 transition-colors">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
            <span className={`text-xs font-bold uppercase tracking-wider ${cfg.textColor}`}>
              {cfg.label}
            </span>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span title={event.timestamp ? new Date(event.timestamp).toLocaleString() : ''}>
                {relativeTime(event.timestamp)}
              </span>
              <span>·</span>
              <span>{event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : ''}</span>
            </div>
          </div>
          <p className="text-sm text-gray-200 mb-2">{event.description}</p>
          <div className="flex flex-wrap gap-3 text-xs">
            {event.actor && (
              <span className="text-gray-400">
                <span className="text-gray-600">Actor:</span> {event.actor}
              </span>
            )}
            {event.device_id && (
              <span className="text-gray-400">
                <span className="text-gray-600">Device:</span>
                <span className="font-mono ml-1">{event.device_id.slice(0, 12)}…</span>
              </span>
            )}
            {event.evidence_id && (
              <span className="text-gray-400">
                <span className="text-gray-600">Evidence:</span>
                <span className="font-mono ml-1">{event.evidence_id.slice(0, 12)}…</span>
              </span>
            )}
          </div>
          {event.metadata && Object.keys(event.metadata).length > 0 && (
            <details className="mt-2">
              <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-300">Metadata</summary>
              <pre className="mt-1 text-xs text-gray-400 bg-gray-900/60 rounded p-2 overflow-x-auto">
                {JSON.stringify(event.metadata, null, 2)}
              </pre>
            </details>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Timeline() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState('');
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(false);

  useEffect(() => {
    casesAPI.getCases().then(r => {
      const list = r.data || [];
      setCases(list);
      const cached = localStorage.getItem('current_case_id');
      if (cached && list.some(c => c._id === cached)) {
        setSelectedCase(cached);
      } else if (list.length > 0) {
        setSelectedCase(list[0]._id);
      }
    }).catch(() => {});
  }, []);

  const fetchEvents = useCallback(async (quiet = false) => {
    if (!selectedCase) return;
    if (!quiet) setLoading(true);
    try {
      const params = {};
      if (filterType) params.event_type = filterType;
      const res = await timelineAPI.getTimeline(selectedCase, params);
      const list = res.data?.events || [];
      // Sort newest first for display
      setEvents([...list].reverse());
    } catch {
      if (!quiet) toast.error('Failed to load timeline.');
    } finally {
      if (!quiet) setLoading(false);
    }
  }, [selectedCase, filterType]);

  useEffect(() => { fetchEvents(); }, [fetchEvents]);

  useEffect(() => {
    if (!autoRefresh) return;
    const timer = setInterval(() => fetchEvents(true), 10000);
    return () => clearInterval(timer);
  }, [autoRefresh, fetchEvents]);

  const handleExport = async () => {
    if (!selectedCase) return;
    try {
      const res = await timelineAPI.exportTimeline(selectedCase);
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `AIDFIRS_Timeline_${selectedCase}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Timeline exported as CSV.');
    } catch {
      toast.error('Failed to export timeline.');
    }
  };

  const caseName = cases.find(c => c._id === selectedCase);

  return (
    <div className="p-6 min-h-screen bg-gray-900 text-white">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Clock className="w-7 h-7 text-blue-500" />
              Forensic Timeline
            </h1>
            <p className="text-gray-400 text-sm mt-1">
              Chronological record of all forensic events for a case.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setAutoRefresh(v => !v)}
              title={autoRefresh ? 'Disable auto-refresh' : 'Enable auto-refresh'}
              className={`p-2 border rounded-lg text-sm transition-colors ${autoRefresh ? 'bg-blue-700 border-blue-500 text-white' : 'bg-gray-800 border-gray-700 text-gray-300'}`}
            >
              <RotateCcw className={`w-4 h-4 ${autoRefresh ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={() => fetchEvents()}
              disabled={loading}
              className="p-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-gray-300 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={handleExport}
              disabled={!selectedCase}
              className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-sm font-medium text-gray-300 transition-colors disabled:opacity-50"
            >
              <Download className="w-4 h-4" />
              Export CSV
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 mb-6">
          <select
            value={selectedCase}
            onChange={e => { setSelectedCase(e.target.value); localStorage.setItem('current_case_id', e.target.value); }}
            className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg p-2.5 focus:ring-blue-500 focus:border-blue-500 min-w-[220px]"
          >
            <option value="">— Select Case —</option>
            {cases.map(c => (
              <option key={c._id} value={c._id}>{c.case_number} — {c.title}</option>
            ))}
          </select>
          <select
            value={filterType}
            onChange={e => setFilterType(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg p-2.5 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">All Event Types</option>
            {EVENT_TYPES.map(t => (
              <option key={t} value={t}>{getEventCfg(t).label}</option>
            ))}
          </select>
        </div>

        {/* Stats row */}
        {events.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            {[
              { label: 'Total Events', value: events.length },
              { label: 'Files Recovered', value: events.filter(e => e.event_type === 'FILE_RECOVERED').length },
              { label: 'Downloads', value: events.filter(e => e.event_type === 'FILE_DOWNLOADED').length },
              { label: 'Verifications', value: events.filter(e => e.event_type === 'HASH_VERIFIED').length },
            ].map(stat => (
              <div key={stat.label} className="bg-gray-800 border border-gray-700 rounded-xl p-4 text-center">
                <p className="text-2xl font-bold text-white">{stat.value}</p>
                <p className="text-xs text-gray-400 mt-0.5">{stat.label}</p>
              </div>
            ))}
          </div>
        )}

        {/* Timeline */}
        {!selectedCase ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <Clock className="w-14 h-14 text-gray-600 mb-3" />
            <p className="text-gray-400">Select a case to view its forensic timeline.</p>
          </div>
        ) : loading ? (
          <div className="flex flex-col items-center justify-center h-64 gap-3">
            <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
            <p className="text-gray-400 text-sm">Loading timeline events…</p>
          </div>
        ) : events.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <Clock className="w-14 h-14 text-gray-600 mb-3" />
            <h2 className="text-lg font-semibold text-gray-300">No Timeline Events</h2>
            <p className="text-gray-500 text-sm mt-1">
              No forensic events recorded for this case yet.
              {filterType && ' Try clearing the event type filter.'}
            </p>
          </div>
        ) : (
          <div className="relative">
            {events.map((ev, i) => (
              <TimelineEventItem key={ev.id || ev._id || i} event={ev} />
            ))}
            {/* Terminal dot */}
            <div className="flex gap-4">
              <div className="flex flex-col items-center">
                <div className="w-9 h-9 rounded-full bg-gray-700 flex items-center justify-center">
                  <div className="w-3 h-3 rounded-full bg-gray-500" />
                </div>
              </div>
              <div className="pb-6 flex-1 flex items-center">
                <p className="text-xs text-gray-500 italic">
                  Showing {events.length} event{events.length !== 1 ? 's' : ''} for case{caseName ? ` "${caseName.case_number}"` : ''}.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
