import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { casesAPI } from '../api';
import {
  Clock, ShieldAlert, FileText, ClipboardList, Shield, Search, Filter,
  User, Calendar, FolderOpen, ArrowLeft, Plus, RefreshCw, Layers, ChevronRight
} from 'lucide-react';
import { toast } from 'sonner';

const Cases = () => {
  const location = useLocation();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);

  // Master-Detail Workspace states
  const [selectedCase, setSelectedCase] = useState(null);
  const [activeTab, setActiveTab] = useState('info'); // 'info', 'coc', 'timeline'
  const [cocRecords, setCocRecords] = useState([]);
  const [timelineEvents, setTimelineEvents] = useState([]);
  const [caseEvidence, setCaseEvidence] = useState([]);
  const [cocLoading, setCocLoading] = useState(false);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  
  // Filtering states for Timeline
  const [searchTimeline, setSearchTimeline] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [eventTypeFilter, setEventTypeFilter] = useState('');

  const [formData, setFormData] = useState({
    case_number: '',
    title: '',
    description: '',
    priority: 'medium',
    case_type: ''
  });

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get('create') === 'true') {
      setShowForm(true);
    }
  }, [location]);

  useEffect(() => {
    fetchCases();
  }, []);

  const fetchCases = async () => {
    setLoading(true);
    try {
      const response = await casesAPI.getCases();
      setCases(response.data);
      // Select the first case by default or restore selection
      if (response.data.length > 0) {
        // If there was a selected case, re-select it to update data
        if (selectedCase) {
          const updated = response.data.find(c => c._id === selectedCase._id);
          if (updated) {
            setSelectedCase(updated);
            fetchCaseDetails(updated._id);
          }
        }
      }
    } catch (err) {
      setError('Failed to load cases');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchCaseDetails = async (caseId) => {
    setEvidenceLoading(true);
    setCocLoading(true);
    setTimelineLoading(true);
    
    try {
      const evidenceRes = await casesAPI.getEvidence(caseId);
      setCaseEvidence(evidenceRes.data);
    } catch (err) {
      console.error('Failed to load evidence', err);
    } finally {
      setEvidenceLoading(false);
    }

    try {
      const cocRes = await casesAPI.getChainOfCustody(caseId);
      setCocRecords(cocRes.data);
    } catch (err) {
      console.error('Failed to load CoC records', err);
    } finally {
      setCocLoading(false);
    }

    try {
      const timelineRes = await casesAPI.getTimeline(caseId, {
        search: searchTimeline,
        severity: severityFilter,
        event_type: eventTypeFilter
      });
      setTimelineEvents(timelineRes.data);
    } catch (err) {
      console.error('Failed to load timeline events', err);
    } finally {
      setTimelineLoading(false);
    }
  };

  // Re-fetch timeline when filters change
  useEffect(() => {
    if (selectedCase) {
      const fetchTimeline = async () => {
        setTimelineLoading(true);
        try {
          const timelineRes = await casesAPI.getTimeline(selectedCase._id, {
            search: searchTimeline,
            severity: severityFilter,
            event_type: eventTypeFilter
          });
          setTimelineEvents(timelineRes.data);
        } catch (err) {
          console.error(err);
        } finally {
          setTimelineLoading(false);
        }
      };
      fetchTimeline();
    }
  }, [searchTimeline, severityFilter, eventTypeFilter, selectedCase]);

  const handleSelectCase = (caseItem) => {
    setSelectedCase(caseItem);
    fetchCaseDetails(caseItem._id);
    setActiveTab('info');
    // Save current case ID in local storage for upload default
    localStorage.setItem('current_case_id', caseItem._id);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await casesAPI.createCase(formData);
      toast.success("Case created successfully!");
      setShowForm(false);
      setFormData({
        case_number: '',
        title: '',
        description: '',
        priority: 'medium',
        case_type: ''
      });
      fetchCases();
      if (res.data) {
        handleSelectCase(res.data);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create case');
      toast.error("Failed to create case.");
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'open':
        return 'bg-emerald-950/30 text-emerald-400 border border-emerald-500/20';
      case 'in_progress':
        return 'bg-blue-950/30 text-blue-400 border border-blue-500/20';
      case 'closed':
        return 'bg-gray-900 text-gray-400 border border-gray-700';
      case 'archived':
        return 'bg-yellow-950/30 text-yellow-400 border border-yellow-500/20';
      default:
        return 'bg-gray-900 text-gray-400 border border-gray-700';
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'critical':
        return 'bg-rose-950/30 text-rose-400 border border-rose-500/30 shadow-[0_0_10px_rgba(244,63,94,0.1)]';
      case 'high':
        return 'bg-orange-950/30 text-orange-400 border border-orange-500/20';
      case 'medium':
        return 'bg-amber-950/30 text-amber-400 border border-amber-500/20';
      case 'low':
        return 'bg-emerald-950/30 text-emerald-400 border border-emerald-500/20';
      default:
        return 'bg-gray-900 text-gray-400 border border-gray-700';
    }
  };

  const getSeverityBadge = (severity) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'bg-red-500/10 text-red-400 border border-red-500/20';
      case 'high':
        return 'bg-orange-500/10 text-orange-400 border border-orange-500/20';
      case 'medium':
        return 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20';
      case 'low':
        return 'bg-blue-500/10 text-blue-400 border border-blue-500/20';
      default:
        return 'bg-gray-500/10 text-gray-400 border border-gray-700';
    }
  };

  return (
    <div className="p-6 max-w-[1600px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <FolderOpen className="text-blue-400 w-7 h-7" /> Forensic Cases
          </h1>
          <p className="text-gray-400 text-xs mt-1">Manage investigation files, chain of custody, and event logs.</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => { fetchCases(); if (selectedCase) fetchCaseDetails(selectedCase._id); }}
            className="p-2.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-xl transition-all border border-gray-700"
            title="Refresh Data"
          >
            <RefreshCw size={16} />
          </button>
          <button
            onClick={() => setShowForm(!showForm)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl transition-all font-semibold flex items-center gap-1.5 shadow-md hover:scale-[1.01]"
          >
            <Plus size={16} /> {showForm ? 'Cancel' : 'New Case'}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-rose-950/20 border border-rose-500/30 text-rose-400 px-4 py-3 rounded-xl text-xs font-mono">
          {error}
        </div>
      )}

      {/* Create Case Form */}
      {showForm && (
        <div className="bg-gray-800/40 backdrop-blur-md border border-gray-700/60 rounded-xl p-6 shadow-xl">
          <h2 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
            <Plus className="text-blue-400" /> Create New Investigation Case
          </h2>
          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-4">
              <div>
                <label className="block text-gray-300 text-xs font-semibold mb-2">
                  Case Number *
                </label>
                <input
                  type="text"
                  value={formData.case_number}
                  onChange={(e) => setFormData({ ...formData, case_number: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-gray-900 border border-gray-700 rounded-xl text-xs text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="e.g., CASE-2026-001"
                  required
                />
              </div>

              <div>
                <label className="block text-gray-300 text-xs font-semibold mb-2">
                  Priority
                </label>
                <select
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-gray-900 border border-gray-700 rounded-xl text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-4">
              <div>
                <label className="block text-gray-300 text-xs font-semibold mb-2">
                  Title *
                </label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-gray-900 border border-gray-700 rounded-xl text-xs text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="e.g., Unauthorized Access USB Recovery"
                  required
                />
              </div>

              <div>
                <label className="block text-gray-300 text-xs font-semibold mb-2">
                  Case Type
                </label>
                <input
                  type="text"
                  value={formData.case_type}
                  onChange={(e) => setFormData({ ...formData, case_type: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-gray-900 border border-gray-700 rounded-xl text-xs text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="e.g., Cybercrime, Corporate Leakage, Malware"
                />
              </div>
            </div>

            <div className="mb-6">
              <label className="block text-gray-300 text-xs font-semibold mb-2">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-3.5 py-2.5 bg-gray-900 border border-gray-700 rounded-xl text-xs text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                rows="3"
                placeholder="Detailed case background, target systems, or suspect details..."
              />
            </div>

            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-4 py-2.5 border border-gray-700 rounded-xl text-xs text-gray-300 hover:bg-gray-800 transition-all font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl text-xs font-semibold transition-all hover:scale-[1.01] disabled:opacity-50"
              >
                {loading ? 'Creating...' : 'Create Case'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Main Grid: Cases List & Details Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Cases List - Left Panel (span 4) */}
        <div className="lg:col-span-4 bg-gray-800/30 backdrop-blur-md border border-gray-700/60 rounded-xl shadow-xl overflow-hidden">
          <div className="p-4 border-b border-gray-700/80 bg-gray-900/40 flex items-center justify-between">
            <h2 className="font-bold text-white text-sm flex items-center gap-2">
              <Layers className="text-blue-400 w-4 h-4" /> Active Investigations
            </h2>
            <span className="text-[10px] bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded-full font-mono font-semibold">
              {cases.length} Total
            </span>
          </div>

          <div className="divide-y divide-gray-700/60 max-h-[700px] overflow-y-auto custom-scrollbar">
            {loading && cases.length === 0 ? (
              <div className="p-12 text-center text-gray-400 text-xs">Loading cases...</div>
            ) : cases.length === 0 ? (
              <div className="p-12 text-center text-gray-400 text-xs">No cases found</div>
            ) : (
              cases.map((caseItem) => (
                <div
                  key={caseItem._id}
                  onClick={() => handleSelectCase(caseItem)}
                  className={`p-4 cursor-pointer transition-all flex justify-between items-start ${
                    selectedCase && selectedCase._id === caseItem._id
                      ? 'bg-blue-500/5 border-l-4 border-blue-500'
                      : 'hover:bg-gray-800/25 border-l-4 border-transparent'
                  }`}
                >
                  <div className="space-y-1.5 flex-1 min-w-0 pr-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-blue-400 font-mono font-semibold">#{caseItem.case_number}</span>
                      <span className="text-gray-600 text-xs">&bull;</span>
                      <span className="text-[10px] text-gray-400 truncate">{caseItem.case_type || 'General'}</span>
                    </div>
                    <h3 className="font-bold text-white text-xs truncate">{caseItem.title}</h3>
                    <p className="text-[10px] text-gray-400 truncate line-clamp-1">{caseItem.description}</p>
                    <div className="flex items-center gap-3 text-[9px] text-gray-500 font-mono mt-2">
                      <span className="flex items-center gap-0.5"><Calendar size={10} /> {new Date(caseItem.created_at).toLocaleDateString()}</span>
                      <span>&bull;</span>
                      <span>Evidence: {caseItem.evidence_ids?.length || 0}</span>
                    </div>
                  </div>
                  <div className="flex flex-col gap-1.5 items-end shrink-0">
                    <span className={`px-2 py-0.5 rounded-full text-[9px] font-mono font-semibold border ${getStatusColor(caseItem.status)}`}>
                      {caseItem.status.replace('_', ' ')}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-[9px] font-mono font-semibold border ${getPriorityColor(caseItem.priority)}`}>
                      {caseItem.priority}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Case detail workspace - Right Panel (span 8) */}
        <div className="lg:col-span-8 space-y-6">
          {selectedCase ? (
            <div className="bg-gray-800/30 backdrop-blur-md border border-gray-700/60 rounded-xl shadow-xl overflow-hidden">
              {/* Workspace Header */}
              <div className="p-6 border-b border-gray-700 bg-gray-900/30 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                    <span className="text-xs bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded border border-blue-500/20 font-mono">
                      #{selectedCase.case_number}
                    </span>
                    <span className={`text-[10px] px-2 py-0.5 rounded border ${getStatusColor(selectedCase.status)}`}>
                      {selectedCase.status}
                    </span>
                    <span className={`text-[10px] px-2 py-0.5 rounded border ${getPriorityColor(selectedCase.priority)}`}>
                      {selectedCase.priority} Priority
                    </span>
                  </div>
                  <h2 className="text-xl font-bold text-white">{selectedCase.title}</h2>
                  <p className="text-xs text-gray-400 mt-1">{selectedCase.description}</p>
                </div>
              </div>

              {/* Workspace Tabs */}
              <div className="border-b border-gray-700/60 bg-gray-900/10 flex px-4">
                <button
                  onClick={() => setActiveTab('info')}
                  className={`px-4 py-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-2 ${
                    activeTab === 'info'
                      ? 'border-blue-500 text-blue-400'
                      : 'border-transparent text-gray-400 hover:text-white'
                  }`}
                >
                  <FileText size={14} /> Case Info & Evidence
                </button>
                <button
                  onClick={() => setActiveTab('coc')}
                  className={`px-4 py-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-2 ${
                    activeTab === 'coc'
                      ? 'border-blue-500 text-blue-400'
                      : 'border-transparent text-gray-400 hover:text-white'
                  }`}
                >
                  <Shield size={14} /> Chain of Custody
                </button>
                <button
                  onClick={() => setActiveTab('timeline')}
                  className={`px-4 py-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-2 ${
                    activeTab === 'timeline'
                      ? 'border-blue-500 text-blue-400'
                      : 'border-transparent text-gray-400 hover:text-white'
                  }`}
                >
                  <Clock size={14} /> Case Timeline
                </button>
              </div>

              {/* Tab Contents */}
              <div className="p-6">
                {/* 1. Case Info & Evidence Tab */}
                {activeTab === 'info' && (
                  <div className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="bg-gray-900/30 border border-gray-700/50 p-4 rounded-xl">
                        <p className="text-[10px] text-gray-400 uppercase tracking-wider font-mono">Case Type</p>
                        <p className="text-sm font-semibold text-white mt-1">{selectedCase.case_type || 'General investigation'}</p>
                      </div>
                      <div className="bg-gray-900/30 border border-gray-700/50 p-4 rounded-xl">
                        <p className="text-[10px] text-gray-400 uppercase tracking-wider font-mono">Created On</p>
                        <p className="text-sm font-semibold text-white mt-1">{new Date(selectedCase.created_at).toLocaleString()}</p>
                      </div>
                      <div className="bg-gray-900/30 border border-gray-700/50 p-4 rounded-xl">
                        <p className="text-[10px] text-gray-400 uppercase tracking-wider font-mono">Assigned Investigator</p>
                        <p className="text-sm font-semibold text-white mt-1 flex items-center gap-1">
                          <User size={13} className="text-blue-400" />
                          {selectedCase.investigator_username || 'Lead Investigator'}
                        </p>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wider font-mono">Associated Evidence Files</h3>
                      {evidenceLoading ? (
                        <div className="p-8 text-center text-gray-400 text-xs">Loading evidence...</div>
                      ) : caseEvidence.length === 0 ? (
                        <div className="bg-gray-900/10 border border-gray-700/40 rounded-xl p-6 text-center text-gray-400 text-xs">
                          No evidence files attached to this case. Upload evidence in the Evidence module.
                        </div>
                      ) : (
                        <div className="overflow-x-auto border border-gray-700/60 rounded-xl">
                          <table className="w-full text-left text-xs border-collapse">
                            <thead>
                              <tr className="bg-gray-900/55 border-b border-gray-700/80 text-gray-300 font-semibold">
                                <th className="px-4 py-3">File Name</th>
                                <th className="px-4 py-3">Type</th>
                                <th className="px-4 py-3">File Size</th>
                                <th className="px-4 py-3">Acquisition Date</th>
                                <th className="px-4 py-3">SHA256 Hash</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-700/50 bg-gray-900/15">
                              {caseEvidence.map((e) => (
                                <tr key={e._id} className="hover:bg-gray-800/20 text-gray-300">
                                  <td className="px-4 py-3 font-semibold text-white truncate max-w-[200px]">{e.file_name}</td>
                                  <td className="px-4 py-3 uppercase text-[10px] font-mono text-cyan-400">{e.evidence_type}</td>
                                  <td className="px-4 py-3 font-mono">{(e.file_size / (1024 * 1024)).toFixed(2)} MB</td>
                                  <td className="px-4 py-3 text-gray-400">{new Date(e.collected_at).toLocaleDateString()}</td>
                                  <td className="px-4 py-3 font-mono text-[10px] text-gray-400 truncate max-w-[150px]" title={e.hash_sha256}>
                                    {e.hash_sha256}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* 2. Chain of Custody Tab */}
                {activeTab === 'coc' && (
                  <div className="space-y-6">
                    <div className="flex justify-between items-center mb-4">
                      <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wider font-mono">Chain of Custody Logs</h3>
                      <span className="text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full flex items-center gap-1">
                        <Shield size={11} /> Cryptographically Audited
                      </span>
                    </div>

                    {cocLoading ? (
                      <div className="p-8 text-center text-gray-400 text-xs">Loading custody chain...</div>
                    ) : cocRecords.length === 0 ? (
                      <div className="bg-gray-900/10 border border-gray-700/40 rounded-xl p-6 text-center text-gray-400 text-xs">
                        No custody logs available.
                      </div>
                    ) : (
                      <div className="relative border-l-2 border-gray-700/80 ml-3 pl-6 space-y-6">
                        {cocRecords.map((log, index) => (
                          <div key={log._id || index} className="relative group">
                            {/* Dot indicator */}
                            <div className="absolute -left-[31px] top-1.5 w-2.5 h-2.5 rounded-full bg-blue-500 border border-gray-900 shadow-[0_0_8px_rgba(59,130,246,0.5)] group-hover:scale-125 transition-transform" />
                            
                            <div className="bg-gray-900/20 border border-gray-700/50 p-4.5 rounded-xl hover:border-gray-600 transition-all space-y-2">
                              <div className="flex justify-between items-start flex-wrap gap-2">
                                <div>
                                  <span className="px-2 py-0.5 rounded bg-blue-500/15 text-blue-400 font-mono text-[9px] font-bold uppercase tracking-wider border border-blue-500/10">
                                    {log.action}
                                  </span>
                                  <span className="text-[10px] text-gray-500 font-mono ml-2">
                                    {new Date(log.timestamp).toLocaleString()}
                                  </span>
                                </div>
                                <span className="text-xs text-gray-300 flex items-center gap-1">
                                  <User size={12} className="text-gray-400" />
                                  <span className="font-mono text-cyan-400">{log.performed_by}</span>
                                </span>
                              </div>

                              <p className="text-xs text-gray-200">{log.notes}</p>

                              {(log.hash_before || log.hash_after) && (
                                <div className="mt-2.5 pt-2.5 border-t border-gray-800 text-[10px] font-mono text-gray-400 grid grid-cols-1 md:grid-cols-2 gap-2">
                                  {log.hash_before && (
                                    <div className="truncate">
                                      <span className="text-gray-500">Hash Before: </span>
                                      <span className="text-rose-400/90">{log.hash_before}</span>
                                    </div>
                                  )}
                                  {log.hash_after && (
                                    <div className="truncate">
                                      <span className="text-gray-500">Hash After: </span>
                                      <span className="text-emerald-400/90">{log.hash_after}</span>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* 3. Interactive Case Timeline Tab */}
                {activeTab === 'timeline' && (
                  <div className="space-y-6">
                    {/* Search and Filters */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 bg-gray-900/30 p-4 border border-gray-700/40 rounded-xl">
                      <div className="relative">
                        <Search size={14} className="absolute left-3 top-3 text-gray-500" />
                        <input
                          type="text"
                          value={searchTimeline}
                          onChange={(e) => setSearchTimeline(e.target.value)}
                          placeholder="Search events (e.g. NTFS, file)..."
                          className="w-full pl-9 pr-3 py-2 bg-gray-900 border border-gray-700 rounded-xl text-xs text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        />
                      </div>

                      <div className="relative">
                        <Filter size={14} className="absolute left-3 top-3 text-gray-500" />
                        <select
                          value={severityFilter}
                          onChange={(e) => setSeverityFilter(e.target.value)}
                          className="w-full pl-9 pr-3 py-2 bg-gray-900 border border-gray-700 rounded-xl text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                        >
                          <option value="">All Severities</option>
                          <option value="critical">Critical</option>
                          <option value="high">High</option>
                          <option value="medium">Medium</option>
                          <option value="low">Low</option>
                          <option value="info">Info</option>
                        </select>
                      </div>

                      <div className="relative">
                        <Layers size={14} className="absolute left-3 top-3 text-gray-500" />
                        <select
                          value={eventTypeFilter}
                          onChange={(e) => setEventTypeFilter(e.target.value)}
                          className="w-full pl-9 pr-3 py-2 bg-gray-900 border border-gray-700 rounded-xl text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                        >
                          <option value="">All Event Types</option>
                          <option value="Device insertion">Device Insertion</option>
                          <option value="File creation">File Creation</option>
                          <option value="File modification">File Modification</option>
                          <option value="File deletion">File Deletion</option>
                          <option value="Recovery events">Recovery Events</option>
                          <option value="Registry/Metadata Event">Registry/Metadata Events</option>
                          <option value="Case Event">Case Events</option>
                          <option value="Assignment Update">Assignment Updates</option>
                        </select>
                      </div>
                    </div>

                    {timelineLoading ? (
                      <div className="p-8 text-center text-gray-400 text-xs">Loading case events...</div>
                    ) : timelineEvents.length === 0 ? (
                      <div className="bg-gray-900/10 border border-gray-700/40 rounded-xl p-6 text-center text-gray-400 text-xs">
                        No timeline events match the filter criteria.
                      </div>
                    ) : (
                      <div className="overflow-x-auto border border-gray-700/60 rounded-xl">
                        <table className="w-full text-left text-xs border-collapse">
                          <thead>
                            <tr className="bg-gray-900/55 border-b border-gray-700/80 text-gray-300 font-semibold">
                              <th className="px-4 py-3">Timestamp</th>
                              <th className="px-4 py-3">Event Type</th>
                              <th className="px-4 py-3">Description</th>
                              <th className="px-4 py-3">Severity</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-700/50 bg-gray-900/15">
                            {timelineEvents.map((event) => (
                              <tr key={event._id} className="hover:bg-gray-800/20 text-gray-300">
                                <td className="px-4 py-3 font-mono text-[10px] text-gray-400">
                                  {new Date(event.timestamp).toLocaleString()}
                                </td>
                                <td className="px-4 py-3 font-semibold text-white">{event.event_type}</td>
                                <td className="px-4 py-3 text-gray-200">{event.description}</td>
                                <td className="px-4 py-3">
                                  <span className={`px-2.5 py-0.5 rounded-full text-[9px] font-mono font-semibold border ${getSeverityBadge(event.severity)}`}>
                                    {event.severity}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="h-[450px] border-2 border-dashed border-gray-700 rounded-xl flex flex-col justify-center items-center text-center p-6 text-gray-400">
              <FolderOpen size={48} className="text-gray-600 mb-3" />
              <h3 className="font-bold text-white text-base">No Case Selected</h3>
              <p className="text-xs max-w-sm mt-1">Select an active investigation from the left sidebar to view Case logs, Timeline analysis, and Chain of Custody records.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Cases;
