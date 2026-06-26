import React, { useState, useEffect } from 'react';
import { auditLogsAPI } from '../api';
import { 
  Shield, Clock, User, FileText, Search, RefreshCw, 
  ChevronRight, Database, AlertCircle, Eye, HardDrive, Filter, X
} from 'lucide-react';
import { toast } from 'sonner';

export default function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAction, setSelectedAction] = useState('ALL');
  const [limit, setLimit] = useState(100);
  const [selectedLog, setSelectedLog] = useState(null);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const response = await auditLogsAPI.getAuditLogs(limit);
      setLogs(response.data?.logs || []);
    } catch (err) {
      toast.error('Failed to load audit logs: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [limit]);

  // Extract unique actions for filter dropdown
  const uniqueActions = ['ALL', ...new Set(logs.map(log => log.action))];

  // Filter logs based on search query and action
  const filteredLogs = logs.filter(log => {
    const matchesSearch = 
      (log.username || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (log.action || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (log.resource_type || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (log.details || '').toLowerCase().includes(searchQuery.toLowerCase());
      
    const matchesAction = selectedAction === 'ALL' || log.action === selectedAction;

    return matchesSearch && matchesAction;
  });

  const getActionBadgeColor = (action) => {
    const act = (action || '').toLowerCase();
    if (act.includes('login') || act.includes('auth')) return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    if (act.includes('delete') || act.includes('deactivate') || act.includes('fail')) return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
    if (act.includes('create') || act.includes('upload') || act.includes('add')) return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    if (act.includes('carve') || act.includes('scan') || act.includes('tsk')) return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
    return 'bg-gray-500/10 text-gray-400 border-gray-500/20';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-black text-white italic tracking-tighter uppercase">
            Security <span className="text-blue-500">Audit</span> Logs
          </h1>
          <p className="text-gray-400 mt-1">Real-time activity ledger for compliance and forensic accountability.</p>
        </div>
        <button 
          onClick={fetchLogs} 
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-xl border border-gray-700 transition-all focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          <span>Sync Logs</span>
        </button>
      </header>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
          <div className="flex justify-between items-center">
            <div>
              <p className="text-xs font-mono uppercase tracking-wider text-gray-500">Total Entries</p>
              <h3 className="text-2xl font-bold mt-1 text-white">{logs.length}</h3>
            </div>
            <Database className="w-8 h-8 text-blue-400" />
          </div>
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
          <div className="flex justify-between items-center">
            <div>
              <p className="text-xs font-mono uppercase tracking-wider text-gray-500">Unique Users</p>
              <h3 className="text-2xl font-bold mt-1 text-emerald-400">
                {new Set(logs.map(l => l.username)).size}
              </h3>
            </div>
            <User className="w-8 h-8 text-emerald-400" />
          </div>
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
          <div className="flex justify-between items-center">
            <div>
              <p className="text-xs font-mono uppercase tracking-wider text-gray-500">Filtered Events</p>
              <h3 className="text-2xl font-bold mt-1 text-yellow-400">{filteredLogs.length}</h3>
            </div>
            <Filter className="w-8 h-8 text-yellow-400" />
          </div>
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
          <div className="flex justify-between items-center">
            <div>
              <p className="text-xs font-mono uppercase tracking-wider text-gray-500">Alert Actions</p>
              <h3 className="text-2xl font-bold mt-1 text-rose-500">
                {logs.filter(l => {
                  const act = (l.action || '').toLowerCase();
                  return act.includes('delete') || act.includes('deactivate') || act.includes('fail');
                }).length}
              </h3>
            </div>
            <AlertCircle className="w-8 h-8 text-rose-500" />
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 flex flex-col md:flex-row gap-4 items-center">
        {/* Search Input */}
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3.5 top-1/2 transform -translate-y-1/2 text-gray-500" size={16} />
          <input
            type="text"
            placeholder="Search by investigator, action, details..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-gray-900 border border-gray-700 rounded-xl text-xs text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Action Type Filter */}
        <div className="w-full md:w-56">
          <select
            value={selectedAction}
            onChange={(e) => setSelectedAction(e.target.value)}
            className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-xl text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {uniqueActions.map(act => (
              <option key={act} value={act}>{act === 'ALL' ? 'Filter by Action: All' : act}</option>
            ))}
          </select>
        </div>

        {/* Row Limit Selector */}
        <div className="w-full md:w-36">
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-xl text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value={50}>Limit: 50</option>
            <option value={100}>Limit: 100</option>
            <option value={200}>Limit: 200</option>
            <option value={500}>Limit: 500</option>
          </select>
        </div>
      </div>

      {/* Logs Table */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto max-h-[500px] custom-scrollbar">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="bg-gray-900 border-b border-gray-700 text-gray-400 text-[10px] font-mono uppercase tracking-wider">
                <th className="px-6 py-4">Timestamp</th>
                <th className="px-6 py-4">Investigator</th>
                <th className="px-6 py-4">Action</th>
                <th className="px-6 py-4">Resource</th>
                <th className="px-6 py-4">IP Address</th>
                <th className="px-6 py-4 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700 text-xs">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-10 text-center text-gray-500 font-mono">
                    <RefreshCw className="animate-spin inline-block mr-2 text-blue-500" size={16} />
                    Syncing activity logs...
                  </td>
                </tr>
              ) : filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-10 text-center text-gray-500 font-mono">
                    No matching audit records identified.
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => (
                  <tr key={log._id} className="hover:bg-gray-700/20 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-gray-400 font-mono text-[11px]">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-white">
                      {log.username || 'System'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded border text-[10px] font-mono ${getActionBadgeColor(log.action)}`}>
                        {log.action}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-300 font-mono text-[11px]">
                      {log.resource_type ? `${log.resource_type} (${log.resource_id || 'N/A'})` : 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-400 font-mono">
                      {log.ip_address || '127.0.0.1'}
                    </td>
                    <td className="px-6 py-4 text-right whitespace-nowrap">
                      <button
                        onClick={() => setSelectedLog(log)}
                        className="px-3 py-1.5 bg-gray-900 border border-gray-700 hover:border-gray-600 rounded-lg text-cyan-400 hover:text-cyan-300 font-medium transition-all flex items-center gap-1.5 ml-auto"
                      >
                        <Eye size={12} />
                        <span>Inspect</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Inspect Log Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-70 backdrop-blur-sm p-4">
          <div className="bg-gray-800 border border-gray-700 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="px-6 py-4 bg-gray-900 border-b border-gray-700 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <Shield className="text-rose-500" size={20} />
                <h3 className="font-bold text-white uppercase font-mono text-sm tracking-wider">Log Inspection Metadata</h3>
              </div>
              <button 
                onClick={() => setSelectedLog(null)}
                className="p-1.5 text-gray-400 hover:text-white rounded-lg hover:bg-gray-700 transition-all"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Content */}
            <div className="px-6 py-4 flex-1 overflow-y-auto space-y-4">
              <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                <div className="p-3 bg-gray-900 border border-gray-700 rounded-xl">
                  <p className="text-gray-500 uppercase text-[9px] mb-1">Timestamp</p>
                  <p className="text-white text-[11px]">{selectedLog.timestamp ? new Date(selectedLog.timestamp).toLocaleString() : 'N/A'}</p>
                </div>
                <div className="p-3 bg-gray-900 border border-gray-700 rounded-xl">
                  <p className="text-gray-500 uppercase text-[9px] mb-1">IP Address</p>
                  <p className="text-white text-[11px]">{selectedLog.ip_address || '127.0.0.1'}</p>
                </div>
                <div className="p-3 bg-gray-900 border border-gray-700 rounded-xl">
                  <p className="text-gray-500 uppercase text-[9px] mb-1">Investigator Name</p>
                  <p className="text-emerald-400 font-bold">{selectedLog.username || 'System'}</p>
                </div>
                <div className="p-3 bg-gray-900 border border-gray-700 rounded-xl">
                  <p className="text-gray-500 uppercase text-[9px] mb-1">Investigator ID</p>
                  <p className="text-white text-[11px]">{selectedLog.user_id || 'System'}</p>
                </div>
              </div>

              <div className="p-4 bg-gray-900 border border-gray-700 rounded-xl space-y-2">
                <div className="flex justify-between items-center text-[10px] uppercase font-mono text-gray-500 border-b border-gray-800 pb-1.5">
                  <span>Logged Action</span>
                  <span className={`px-2 py-0.5 rounded border text-[9px] ${getActionBadgeColor(selectedLog.action)}`}>
                    {selectedLog.action}
                  </span>
                </div>
                
                <div className="text-xs space-y-1">
                  <p className="text-gray-400 font-mono"><strong className="text-white font-semibold">Resource:</strong> {selectedLog.resource_type ? `${selectedLog.resource_type} [ID: ${selectedLog.resource_id || 'N/A'}]` : 'N/A'}</p>
                  <p className="text-gray-400 mt-2 leading-relaxed"><strong className="text-white font-semibold">Details:</strong> {selectedLog.details || 'No additional parameters logged.'}</p>
                </div>
              </div>

              {/* Raw JSON viewer */}
              <div className="space-y-1.5">
                <p className="text-[10px] uppercase font-mono text-gray-500">Immutable JSON Audit Record</p>
                <pre className="p-4 bg-gray-950 border border-gray-700 rounded-xl text-[10px] font-mono text-cyan-400 overflow-x-auto select-all shadow-inner">
                  {JSON.stringify(selectedLog, null, 2)}
                </pre>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 bg-gray-900 border-t border-gray-700 flex justify-end">
              <button 
                onClick={() => setSelectedLog(null)}
                className="px-4 py-2 bg-gray-850 hover:bg-gray-700 border border-gray-700 text-white rounded-xl text-xs font-semibold transition-all"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
