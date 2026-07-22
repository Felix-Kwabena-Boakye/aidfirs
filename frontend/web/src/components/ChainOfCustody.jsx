import React, { useState, useEffect, useCallback } from 'react';
import { casesAPI, chainOfCustodyAPI, reportsAPI } from '../api';
import {
  Shield, Download, RefreshCw, Copy, CheckCircle,
  AlertTriangle, FileText, Activity, Lock
} from 'lucide-react';
import { toast } from 'sonner';

const ACTION_CONFIG = {
  RECOVERY_STARTED:  { color: 'bg-blue-900/60 text-blue-300 border-blue-700/40',   dot: 'bg-blue-500'   },
  FILE_RECOVERED:    { color: 'bg-green-900/60 text-green-300 border-green-700/40', dot: 'bg-green-500'  },
  HASH_CREATED:      { color: 'bg-purple-900/60 text-purple-300 border-purple-700/40', dot: 'bg-purple-500' },
  HASH_VERIFIED:     { color: 'bg-violet-900/60 text-violet-300 border-violet-700/40', dot: 'bg-violet-500' },
  FILE_DOWNLOADED:   { color: 'bg-teal-900/60 text-teal-300 border-teal-700/40',   dot: 'bg-teal-500'   },
  IMAGE_CREATED:     { color: 'bg-orange-900/60 text-orange-300 border-orange-700/40', dot: 'bg-orange-500' },
  FILE_ANALYZED:     { color: 'bg-yellow-900/60 text-yellow-300 border-yellow-700/40', dot: 'bg-yellow-500' },
  REPORT_GENERATED:  { color: 'bg-pink-900/60 text-pink-300 border-pink-700/40',   dot: 'bg-pink-500'   },
  CASE_EXPORTED:     { color: 'bg-indigo-900/60 text-indigo-300 border-indigo-700/40', dot: 'bg-indigo-500' },
  default:           { color: 'bg-gray-800 text-gray-300 border-gray-700',          dot: 'bg-gray-500'   },
};

function getActionCfg(action) {
  return ACTION_CONFIG[action] || ACTION_CONFIG.default;
}

function truncateHash(hash, len = 16) {
  if (!hash) return '—';
  return hash.length > len ? hash.slice(0, len) + '…' : hash;
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  if (!text) return null;
  return (
    <button
      onClick={handleCopy}
      className="ml-1 p-0.5 text-gray-500 hover:text-gray-300 transition-colors"
      title="Copy full hash"
    >
      {copied ? <CheckCircle className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
    </button>
  );
}

export default function ChainOfCustody() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState('');
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterAction, setFilterAction] = useState('');
  const [exportingPdf, setExportingPdf] = useState(false);

  useEffect(() => {
    casesAPI.getCases().then(r => {
      const list = r.data || [];
      setCases(list);
      const cached = localStorage.getItem('current_case_id');
      if (cached && list.some(c => c._id === cached)) setSelectedCase(cached);
      else if (list.length > 0) setSelectedCase(list[0]._id);
    }).catch(() => {});
  }, []);

  const fetchEntries = useCallback(async () => {
    if (!selectedCase) return;
    setLoading(true);
    try {
      const res = await casesAPI.getChainOfCustody(selectedCase);
      setEntries(res.data?.chain_of_custody || res.data || []);
    } catch {
      toast.error('Failed to load chain of custody.');
    } finally {
      setLoading(false);
    }
  }, [selectedCase]);

  useEffect(() => { fetchEntries(); }, [fetchEntries]);

  const handleExportCsv = async () => {
    if (!selectedCase) return;
    try {
      const res = await chainOfCustodyAPI.exportCoC(selectedCase);
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `AIDFIRS_ChainOfCustody_${selectedCase}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Chain of Custody exported as CSV.');
    } catch {
      toast.error('Failed to export CSV.');
    }
  };

  const handleExportPdf = async () => {
    if (!selectedCase) return;
    setExportingPdf(true);
    try {
      const res = await reportsAPI.generateReport({
        case_id: selectedCase,
        format: 'pdf',
        report_type: 'chain_of_custody',
      });
      const reportId = res.data?.report?._id || res.data?.report?.id;
      toast.success(`Report generation started. ID: ${String(reportId).slice(0, 8)}… Check Reports page.`);
    } catch {
      toast.error('Failed to generate PDF report.');
    } finally {
      setExportingPdf(false);
    }
  };

  const filtered = filterAction
    ? entries.filter(e => (e.action || '').includes(filterAction))
    : entries;

  // Compute summary stats
  const uniqueActors = new Set(entries.map(e => e.performed_by).filter(Boolean)).size;
  const hashChanges = entries.filter(e => e.hash_before || e.hash_after).length;
  const verifiedTransfers = entries.filter(e => e.hash_before && e.hash_after && e.hash_before === e.hash_after).length;

  return (
    <div className="p-6 min-h-screen bg-gray-900 text-white">
      <div className="max-w-7xl mx-auto">
        {/* Legal admissibility banner */}
        <div className="flex items-center gap-3 bg-amber-900/20 border border-amber-700/40 rounded-xl px-5 py-3 mb-5">
          <Lock className="w-5 h-5 text-amber-400 flex-shrink-0" />
          <p className="text-amber-300 text-sm font-semibold">
            IMMUTABLE RECORD — This chain of custody log is cryptographically anchored and court-admissible.
          </p>
        </div>

        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Shield className="w-7 h-7 text-blue-500" />
              Chain of Custody
            </h1>
            <p className="text-gray-400 text-sm mt-1">Immutable forensic audit trail for evidence handling.</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchEntries()}
              disabled={loading}
              className="p-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-gray-300 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={handleExportCsv}
              disabled={!selectedCase}
              className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-sm text-gray-300 transition-colors disabled:opacity-50"
            >
              <Download className="w-4 h-4" /> CSV
            </button>
            <button
              onClick={handleExportPdf}
              disabled={!selectedCase || exportingPdf}
              className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50"
            >
              <FileText className="w-4 h-4" /> {exportingPdf ? 'Generating…' : 'Export PDF'}
            </button>
          </div>
        </div>

        {/* Case selector + filter */}
        <div className="flex flex-wrap gap-3 mb-5">
          <select
            value={selectedCase}
            onChange={e => { setSelectedCase(e.target.value); localStorage.setItem('current_case_id', e.target.value); }}
            className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg p-2.5 min-w-[220px]"
          >
            <option value="">— Select Case —</option>
            {cases.map(c => <option key={c._id} value={c._id}>{c.case_number} — {c.title}</option>)}
          </select>
          <select
            value={filterAction}
            onChange={e => setFilterAction(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg p-2.5"
          >
            <option value="">All Actions</option>
            {Object.keys(ACTION_CONFIG).filter(k => k !== 'default').map(a => (
              <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>

        {/* Summary cards */}
        {entries.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
            {[
              { icon: Activity,    label: 'Total Events',       value: entries.length },
              { icon: Shield,      label: 'Verified Transfers', value: verifiedTransfers },
              { icon: AlertTriangle, label: 'Hash Changes',     value: hashChanges },
              { icon: CheckCircle, label: 'Unique Actors',      value: uniqueActors },
            ].map(s => {
              const Icon = s.icon;
              return (
                <div key={s.label} className="bg-gray-800 border border-gray-700 rounded-xl p-4 flex items-center gap-3">
                  <Icon className="w-8 h-8 text-blue-400 flex-shrink-0" />
                  <div>
                    <p className="text-xl font-bold">{s.value}</p>
                    <p className="text-xs text-gray-400">{s.label}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Table */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden shadow-xl">
          {loading ? (
            <div className="flex justify-center items-center h-52">
              <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
            </div>
          ) : !selectedCase ? (
            <div className="flex flex-col items-center justify-center h-52 text-gray-500">
              <Shield className="w-12 h-12 mb-2" />
              <p>Select a case to view the chain of custody.</p>
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-52 text-gray-500">
              <Shield className="w-12 h-12 mb-2" />
              <p>No chain of custody entries found.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="bg-gray-900 border-b border-gray-700 text-xs text-gray-400 uppercase tracking-wider">
                    <th className="py-3 px-4">Timestamp</th>
                    <th className="py-3 px-4">Action</th>
                    <th className="py-3 px-4">Performed By</th>
                    <th className="py-3 px-4">Evidence ID</th>
                    <th className="py-3 px-4">Notes</th>
                    <th className="py-3 px-4">Hash Before</th>
                    <th className="py-3 px-4">Hash After</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700/40">
                  {filtered.map((entry, i) => {
                    const cfg = getActionCfg(entry.action);
                    return (
                      <tr key={i} className="hover:bg-gray-700/20 transition-colors">
                        <td className="py-3 px-4 text-xs text-gray-400 whitespace-nowrap">
                          {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : '—'}
                        </td>
                        <td className="py-3 px-4">
                          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full border ${cfg.color}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
                            {entry.action?.replace(/_/g, ' ') || '—'}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-sm text-gray-200">{entry.performed_by || '—'}</td>
                        <td className="py-3 px-4 font-mono text-xs text-gray-400">
                          {entry.evidence_id ? (
                            <span title={entry.evidence_id}>{String(entry.evidence_id).slice(0, 12)}…</span>
                          ) : '—'}
                        </td>
                        <td className="py-3 px-4 text-xs text-gray-400 max-w-[200px]">
                          <span title={entry.notes}>{entry.notes ? entry.notes.slice(0, 80) + (entry.notes.length > 80 ? '…' : '') : '—'}</span>
                        </td>
                        <td className="py-3 px-4 font-mono text-xs text-gray-500 whitespace-nowrap">
                          {truncateHash(entry.hash_before)}
                          <CopyButton text={entry.hash_before} />
                        </td>
                        <td className="py-3 px-4 font-mono text-xs text-gray-400 whitespace-nowrap">
                          {truncateHash(entry.hash_after)}
                          <CopyButton text={entry.hash_after} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
        <p className="text-xs text-gray-600 mt-3 text-right">
          {filtered.length} of {entries.length} entries displayed
        </p>
      </div>
    </div>
  );
}
