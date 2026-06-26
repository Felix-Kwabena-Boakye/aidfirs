import React, { useState, useEffect } from 'react';
import { auditLogsAPI, usersAPI } from '../api';
import { 
  Shield, ShieldAlert, Lock, CheckCircle2, XCircle, Users, RefreshCw, 
  Search, Eye, Globe, Terminal, UserCheck
} from 'lucide-react';
import { toast } from 'sonner';

export default function PermissionsAudit() {
  const [activeTab, setActiveTab] = useState('matrix');
  const [users, setUsers] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLog, setSelectedLog] = useState(null);

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'users') {
        const response = await usersAPI.getUsers();
        setUsers(response.data || []);
      } else if (activeTab === 'denials') {
        const response = await auditLogsAPI.getAuditLogs(500);
        const allLogs = response.data?.logs || [];
        // Filter logs by 403/401 status code or "Access Denied" action type
        const deniedLogs = allLogs.filter(log => 
          log.status_code === 403 || 
          log.status_code === 401 || 
          (log.action && log.action.toLowerCase().includes('denied')) ||
          (log.action && log.action.toLowerCase().includes('fail'))
        );
        setLogs(deniedLogs);
      }
    } catch (err) {
      toast.error('Failed to load audit data: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  // Filter denials logs based on search query
  const filteredLogs = logs.filter(log => {
    return (
      (log.username || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (log.path || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (log.method || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (log.action || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (log.details || '').toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  // Filter users based on search query
  const filteredUsers = users.filter(u => {
    return (
      (u.username || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (u.email || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (u.role || '').toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  // RBAC Permission Grid specification
  const permissionsMatrix = [
    {
      action: 'Register & Upload Evidence',
      description: 'Upload files, specify drive mount paths, and add case sources.',
      admin: true,
      investigator: true,
      analyst: false,
    },
    {
      action: 'Carve & Scan (PhotoRec/TestDisk)',
      description: 'Run forensic file carving, TestDisk logical recovery, and SleuthKit indexing.',
      admin: true,
      investigator: true,
      analyst: false,
    },
    {
      action: 'File Restoration & Export',
      description: 'Restore carved files to original drive, secondary USB, or export to workspace folders.',
      admin: true,
      investigator: true,
      analyst: false,
    },
    {
      action: 'AI Assistant &Timeline Analysis',
      description: 'Engage Claude 3.5 Sonnet to perform metadata parsing and timeline anomaly detection.',
      admin: true,
      investigator: true,
      analyst: false,
    },
    {
      action: 'Report Generation (PDF)',
      description: 'Generate immutable cryptographic forensic reports.',
      admin: true,
      investigator: true,
      analyst: true,
    },
    {
      action: 'View Dashboard & Cases',
      description: 'Read-only access to case timeline, registered evidence details, and recovered files list.',
      admin: true,
      investigator: true,
      analyst: true,
    },
    {
      action: 'User Management',
      description: 'Provision roles, add investigators, activate/deactivate accounts.',
      admin: true,
      investigator: false,
      analyst: false,
    },
    {
      action: 'System Settings & Audit logs',
      description: 'Modify model weights, export full audit trails, configure Google OAuth settings.',
      admin: true,
      investigator: false,
      analyst: false,
    }
  ];

  return (
    <div className="space-y-6 text-slate-100 p-6 bg-slate-950 min-h-screen">
      {/* Page Header */}
      <header className="flex justify-between items-center border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs uppercase tracking-widest mb-1">
            <Shield size={14} className="animate-pulse" />
            <span>AIDFIRS // SECURITY CENTER</span>
          </div>
          <h1 className="text-3xl font-extrabold text-slate-50 tracking-tight">Permissions Audit Panel</h1>
          <p className="text-sm text-slate-400 mt-1">Audit active roles, view RBAC control policies, and analyze access denial anomalies.</p>
        </div>
        <button
          onClick={fetchData}
          disabled={loading && activeTab !== 'matrix'}
          className="bg-slate-900 hover:bg-slate-800 border border-slate-700/60 text-slate-200 px-4 py-2.5 rounded-lg transition-all text-xs font-semibold flex items-center gap-2"
        >
          <RefreshCw size={14} className={loading && activeTab !== 'matrix' ? 'animate-spin' : ''} />
          <span>Sync Registry</span>
        </button>
      </header>

      {/* Tabs Selector */}
      <div className="flex gap-2 p-1 bg-slate-900/60 border border-slate-800 rounded-xl max-w-lg">
        <button
          onClick={() => setActiveTab('matrix')}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold font-mono tracking-wide uppercase transition-all flex items-center justify-center gap-2 ${
            activeTab === 'matrix' 
              ? 'bg-blue-600 text-white shadow-md' 
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Shield size={14} />
          <span>RBAC Matrix</span>
        </button>
        <button
          onClick={() => setActiveTab('denials')}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold font-mono tracking-wide uppercase transition-all flex items-center justify-center gap-2 ${
            activeTab === 'denials' 
              ? 'bg-blue-600 text-white shadow-md' 
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <ShieldAlert size={14} />
          <span>Access Denials</span>
        </button>
        <button
          onClick={() => setActiveTab('users')}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold font-mono tracking-wide uppercase transition-all flex items-center justify-center gap-2 ${
            activeTab === 'users' 
              ? 'bg-blue-600 text-white shadow-md' 
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Users size={14} />
          <span>Active Roles</span>
        </button>
      </div>

      {/* SEARCH BAR (For lists) */}
      {activeTab !== 'matrix' && (
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-500" size={16} />
          <input
            type="text"
            placeholder={activeTab === 'denials' ? "Filter denials by username, method, endpoint..." : "Filter users by username, email, role..."}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 text-slate-200 pl-10 pr-4 py-2.5 rounded-xl focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 font-mono text-xs placeholder-slate-500"
          />
        </div>
      )}

      {/* MATRIX TAB CONTENT */}
      {activeTab === 'matrix' && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-2xl animate-in fade-in duration-300">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="bg-slate-950 border-b border-slate-800 text-[10px] font-mono text-slate-400 uppercase tracking-widest">
                <th className="px-6 py-4">Action / Scope</th>
                <th className="px-6 py-4 text-center">Administrator</th>
                <th className="px-6 py-4 text-center">Investigator</th>
                <th className="px-6 py-4 text-center">Security Analyst</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-xs">
              {permissionsMatrix.map((item, idx) => (
                <tr key={idx} className="hover:bg-slate-900/20 transition-colors">
                  <td className="px-6 py-4">
                    <div className="font-semibold text-slate-200">{item.action}</div>
                    <div className="text-[11px] text-slate-400 mt-1">{item.description}</div>
                  </td>
                  <td className="px-6 py-4 text-center">
                    <div className="flex justify-center">
                      {item.admin ? <CheckCircle2 size={18} className="text-emerald-400" /> : <XCircle size={18} className="text-slate-600" />}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-center">
                    <div className="flex justify-center">
                      {item.investigator ? <CheckCircle2 size={18} className="text-emerald-400" /> : <XCircle size={18} className="text-rose-500" />}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-center">
                    <div className="flex justify-center">
                      {item.analyst ? <CheckCircle2 size={18} className="text-emerald-400" /> : <XCircle size={18} className="text-rose-500" />}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* DENIALS TAB CONTENT */}
      {activeTab === 'denials' && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-2xl animate-in fade-in duration-300">
          <div className="overflow-x-auto max-h-[550px]">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="bg-slate-950 border-b border-slate-800 text-[10px] font-mono text-slate-400 uppercase tracking-widest">
                  <th className="px-6 py-4">Timestamp</th>
                  <th className="px-6 py-4">Subject</th>
                  <th className="px-6 py-4">Resource path</th>
                  <th className="px-6 py-4">Method</th>
                  <th className="px-6 py-4">Anomalous Event</th>
                  <th className="px-6 py-4 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-xs font-mono">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-10 text-center text-slate-500 font-mono">
                      <RefreshCw className="animate-spin inline-block mr-2 text-cyan-400" size={14} />
                      Syncing security exception logs...
                    </td>
                  </tr>
                ) : filteredLogs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-10 text-center text-slate-500">
                      No unauthorized access attempts or 403/401 alerts logged.
                    </td>
                  </tr>
                ) : (
                  filteredLogs.map((log) => (
                    <tr key={log._id} className="hover:bg-rose-500/5 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap text-slate-400 text-[11px]">
                        {log.timestamp ? new Date(log.timestamp).toLocaleString() : 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="font-semibold text-slate-200">{log.username || 'Anonymous'}</div>
                        <div className="text-[10px] text-rose-455 font-bold uppercase mt-0.5">{log.role || 'anonymous'}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-slate-350 text-[11px] truncate max-w-[200px]">
                        {log.path || log.resource_id || 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-cyan-455">
                        {log.method || log.details?.method || 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2 py-0.5 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded font-bold text-[10px]">
                          {log.action || 'Access Denied'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right whitespace-nowrap">
                        <button
                          onClick={() => setSelectedLog(log)}
                          className="px-3 py-1.5 bg-slate-950 hover:bg-slate-900 border border-slate-800 rounded-lg text-cyan-400 hover:text-cyan-300 font-medium transition-all flex items-center gap-1.5 ml-auto text-xs"
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
      )}

      {/* ACTIVE ROLES TAB CONTENT */}
      {activeTab === 'users' && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-2xl animate-in fade-in duration-300">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="bg-slate-950 border-b border-slate-800 text-[10px] font-mono text-slate-400 uppercase tracking-widest">
                <th className="px-6 py-4">Subject</th>
                <th className="px-6 py-4">Email</th>
                <th className="px-6 py-4">Auth Mechanism</th>
                <th className="px-6 py-4">Role Placement</th>
                <th className="px-6 py-4 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-xs">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-10 text-center text-slate-500 font-mono">
                    <RefreshCw className="animate-spin inline-block mr-2 text-cyan-400" size={14} />
                    Syncing user roles...
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-10 text-center text-slate-500">
                    No active user mappings discovered.
                  </td>
                </tr>
              ) : (
                filteredUsers.map((user) => (
                  <tr key={user._id || user.id} className="hover:bg-slate-900/20 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap font-semibold text-slate-200">
                      {user.username}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-slate-400 font-mono text-[11px]">
                      {user.email}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-slate-300 font-mono text-[11px]">
                      {user.google_id ? (
                        <span className="flex items-center gap-1.5 text-cyan-400">
                          <Globe size={12} />
                          <span>Google OAuth2</span>
                        </span>
                      ) : (
                        <span className="flex items-center gap-1.5 text-slate-400">
                          <Lock size={12} />
                          <span>Password Hash / JWT</span>
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-0.5 rounded border text-[10px] font-mono font-bold uppercase tracking-wider ${
                        user.role === 'admin' 
                          ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' 
                          : user.role === 'investigator' 
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                          : 'bg-purple-500/10 text-purple-400 border-purple-500/20'
                      }`}>
                        {user.role}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-center whitespace-nowrap">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        user.is_active 
                          ? 'bg-emerald-500/10 text-emerald-400' 
                          : 'bg-slate-800 text-slate-500'
                      }`}>
                        {user.is_active ? 'ACTIVE' : 'DEACTIVATED'}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* INSPECT LOG MODAL */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-200">
            {/* Header */}
            <div className="px-6 py-4 bg-slate-950 border-b border-slate-800 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <ShieldAlert className="text-rose-500" size={18} />
                <span className="font-bold text-slate-100 uppercase font-mono text-xs tracking-wider">Access Exception Metadata</span>
              </div>
              <button 
                onClick={() => setSelectedLog(null)}
                className="text-slate-400 hover:text-slate-100 font-bold"
              >
                &times;
              </button>
            </div>

            {/* Content */}
            <div className="px-6 py-4 flex-1 overflow-y-auto space-y-4 font-mono text-xs">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-slate-950 border border-slate-850 rounded-xl">
                  <span className="text-[10px] text-slate-500 block mb-1 uppercase">Timestamp</span>
                  <span className="text-slate-300">{selectedLog.timestamp ? new Date(selectedLog.timestamp).toLocaleString() : 'N/A'}</span>
                </div>
                <div className="p-3 bg-slate-950 border border-slate-850 rounded-xl">
                  <span className="text-[10px] text-slate-500 block mb-1 uppercase">Source IP</span>
                  <span className="text-slate-300">{selectedLog.ip || selectedLog.ip_address || '127.0.0.1'}</span>
                </div>
                <div className="p-3 bg-slate-950 border border-slate-850 rounded-xl">
                  <span className="text-[10px] text-slate-500 block mb-1 uppercase">User Subject</span>
                  <span className="text-slate-300 font-semibold">{selectedLog.username || 'Anonymous'}</span>
                </div>
                <div className="p-3 bg-slate-950 border border-slate-850 rounded-xl">
                  <span className="text-[10px] text-slate-500 block mb-1 uppercase">Assigned Role</span>
                  <span className="text-rose-400 font-bold uppercase">{selectedLog.role || 'anonymous'}</span>
                </div>
              </div>

              <div className="p-4 bg-slate-950 border border-slate-850 rounded-xl space-y-3">
                <div>
                  <span className="text-slate-500 text-[10px] uppercase block mb-1">Target Endpoint</span>
                  <span className="text-cyan-400 font-semibold">{selectedLog.method || selectedLog.details?.method || 'GET'} {selectedLog.path || selectedLog.resource_id}</span>
                </div>
                
                <div>
                  <span className="text-slate-500 text-[10px] uppercase block mb-1">Security Diagnostics</span>
                  <p className="text-rose-350 leading-relaxed">{selectedLog.details?.message || selectedLog.message || selectedLog.details || 'Access Forbidden.'}</p>
                </div>
              </div>

              {/* Immutable JSON logs */}
              <div className="space-y-1">
                <span className="text-[10px] text-slate-500 block uppercase">Immutable JSON Logs</span>
                <pre className="p-3.5 bg-black border border-slate-850 rounded-xl text-[10px] text-cyan-400 overflow-x-auto select-all scrollbar-thin">
                  {JSON.stringify(selectedLog, null, 2)}
                </pre>
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 bg-slate-950 border-t border-slate-800 flex justify-end">
              <button 
                onClick={() => setSelectedLog(null)}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-850 border border-slate-800 text-slate-200 rounded-xl text-xs font-semibold transition-all"
              >
                Close Metadata Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
