import React, { useState, useEffect, useCallback } from 'react';
import { recoveryAPI, casesAPI } from '../api';
import {
  Hash, CheckCircle, XCircle, AlertTriangle, Search,
  RefreshCw, Shield, ClipboardList, Loader, FileText
} from 'lucide-react';
import { toast } from 'sonner';

const STATUS_CONFIG = {
  verified:      { icon: CheckCircle, color: 'text-green-400',  bg: 'bg-green-900/20 border-green-700/40', label: 'Integrity Verified', desc: 'All hashes match. File has not been tampered with.' },
  modified:      { icon: XCircle,     color: 'text-red-400',    bg: 'bg-red-900/20 border-red-700/40',    label: 'Tampering Detected!',  desc: 'Hash mismatch. File may have been modified.' },
  unverifiable:  { icon: AlertTriangle, color: 'text-yellow-400', bg: 'bg-yellow-900/20 border-yellow-700/40', label: 'Unverifiable', desc: 'Insufficient hash data to fully verify.' },
  error:         { icon: AlertTriangle, color: 'text-orange-400', bg: 'bg-orange-900/20 border-orange-700/40', label: 'Verification Error', desc: 'Could not read file from server.' },
};

function HashRow({ algo, stored, computed, match }) {
  return (
    <tr className="border-b border-gray-700/40 hover:bg-gray-700/20">
      <td className="py-3 px-4 font-bold text-gray-300 text-sm">{algo}</td>
      <td className="py-3 px-4 font-mono text-xs text-gray-400 break-all">{stored || <span className="text-gray-600 italic">not stored</span>}</td>
      <td className="py-3 px-4 font-mono text-xs text-gray-400 break-all">{computed || <span className="text-gray-600 italic">not computed</span>}</td>
      <td className="py-3 px-4">
        {match === true && <CheckCircle className="w-5 h-5 text-green-400" />}
        {match === false && <XCircle className="w-5 h-5 text-red-400" />}
        {match === null && <AlertTriangle className="w-4 h-4 text-yellow-400" />}
      </td>
    </tr>
  );
}

function VerificationResult({ result }) {
  if (!result) return null;
  const cfg = STATUS_CONFIG[result.verification_status] || STATUS_CONFIG.unverifiable;
  const Icon = cfg.icon;
  return (
    <div className={`border rounded-xl p-5 ${cfg.bg} mt-4`}>
      <div className="flex items-center gap-3 mb-3">
        <Icon className={`w-8 h-8 ${cfg.color}`} />
        <div>
          <p className={`text-lg font-bold ${cfg.color}`}>{cfg.label}</p>
          <p className="text-sm text-gray-400">{cfg.desc}</p>
        </div>
      </div>
      {result.hashes && (
        <div className="overflow-x-auto">
          <table className="w-full text-left mt-2">
            <thead>
              <tr className="text-xs text-gray-500 uppercase tracking-wider border-b border-gray-700">
                <th className="py-2 px-4">Algorithm</th>
                <th className="py-2 px-4">Stored Hash</th>
                <th className="py-2 px-4">Computed Hash</th>
                <th className="py-2 px-4">Match</th>
              </tr>
            </thead>
            <tbody>
              <HashRow algo="SHA-256" {...result.hashes.sha256} />
              <HashRow algo="MD5"     {...result.hashes.md5}    />
              <HashRow algo="SHA-1"   {...result.hashes.sha1}   />
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function HashVerification() {
  const [tab, setTab] = useState('file'); // 'file' | 'hash'
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState('');
  const [files, setFiles] = useState([]);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [verifyingId, setVerifyingId] = useState(null);
  const [results, setResults] = useState({}); // { fileId: resultObj }
  const [selected, setSelected] = useState(new Set());
  const [batchRunning, setBatchRunning] = useState(false);
  // Hash string search
  const [hashInput, setHashInput] = useState('');
  const [hashAlgo, setHashAlgo] = useState('SHA256');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  // History
  const [history, setHistory] = useState([]);

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

  const fetchFiles = useCallback(async () => {
    if (!selectedCase) return;
    setLoadingFiles(true);
    try {
      const res = await recoveryAPI.getRecoveredFiles(selectedCase);
      setFiles(res.data.files || []);
    } catch {
      toast.error('Failed to load files.');
    } finally {
      setLoadingFiles(false);
    }
  }, [selectedCase]);

  useEffect(() => { fetchFiles(); }, [fetchFiles]);

  const doVerify = async (fileId, filename) => {
    setVerifyingId(fileId);
    try {
      const res = await recoveryAPI.verifyFileHash(fileId);
      const result = res.data;
      setResults(prev => ({ ...prev, [fileId]: result }));
      setHistory(prev => [{
        fileId, filename, status: result.verification_status,
        time: new Date().toLocaleTimeString()
      }, ...prev.slice(0, 49)]);
      if (result.verification_status === 'verified') toast.success(`✓ ${filename}: Integrity Verified`);
      else if (result.verification_status === 'modified') toast.error(`⚠ ${filename}: TAMPERING DETECTED`);
      else toast.warning(`${filename}: Unverifiable`);
    } catch (err) {
      toast.error(`Verification failed: ${err.response?.data?.error || 'Unknown error'}`);
    } finally {
      setVerifyingId(null);
    }
  };

  const handleBatchVerify = async () => {
    if (selected.size === 0) return;
    setBatchRunning(true);
    for (const fileId of selected) {
      const file = files.find(f => f._id === fileId);
      await doVerify(fileId, file?.filename || fileId);
    }
    setBatchRunning(false);
  };

  const handleHashSearch = async () => {
    if (!hashInput.trim()) return;
    setSearching(true);
    try {
      const res = await recoveryAPI.searchFiles({ hash: hashInput.trim() });
      setSearchResults(res.data.files || []);
      if ((res.data.files || []).length === 0) toast.info('No files found matching this hash.');
    } catch {
      toast.error('Hash search failed.');
    } finally {
      setSearching(false);
    }
  };

  const toggleSelect = (id) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === files.length) setSelected(new Set());
    else setSelected(new Set(files.map(f => f._id)));
  };

  return (
    <div className="p-6 min-h-screen bg-gray-900 text-white">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Hash className="w-7 h-7 text-blue-500" />
            Hash Verification
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            Cryptographic integrity verification for recovered forensic evidence files.
          </p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-5 bg-gray-800 border border-gray-700 rounded-xl p-1 w-fit">
          {[{ id: 'file', icon: FileText, label: 'Verify by File' }, { id: 'hash', icon: Search, label: 'Search by Hash' }].map(t => {
            const Icon = t.icon;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${tab === t.id ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
              >
                <Icon className="w-4 h-4" />
                {t.label}
              </button>
            );
          })}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main panel */}
          <div className="lg:col-span-2">
            {tab === 'file' && (
              <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
                {/* Sub-header */}
                <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-gray-700 bg-gray-900/40">
                  <select
                    value={selectedCase}
                    onChange={e => { setSelectedCase(e.target.value); localStorage.setItem('current_case_id', e.target.value); }}
                    className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg p-2 flex-1 max-w-xs"
                  >
                    <option value="">— Select Case —</option>
                    {cases.map(c => <option key={c._id} value={c._id}>{c.case_number} — {c.title}</option>)}
                  </select>
                  <div className="flex items-center gap-2">
                    {selected.size > 0 && (
                      <button
                        onClick={handleBatchVerify}
                        disabled={batchRunning}
                        className="flex items-center gap-1.5 px-3 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-semibold transition-colors"
                      >
                        {batchRunning ? <Loader className="w-3 h-3 animate-spin" /> : <Shield className="w-3 h-3" />}
                        Verify Selected ({selected.size})
                      </button>
                    )}
                    <button onClick={fetchFiles} className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-gray-300">
                      <RefreshCw className={`w-4 h-4 ${loadingFiles ? 'animate-spin' : ''}`} />
                    </button>
                  </div>
                </div>
                {/* File list */}
                {loadingFiles ? (
                  <div className="flex justify-center items-center h-48">
                    <RefreshCw className="w-7 h-7 text-blue-500 animate-spin" />
                  </div>
                ) : files.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-48 text-gray-500">
                    <FileText className="w-10 h-10 mb-2" />
                    <p>No files found for this case.</p>
                  </div>
                ) : (
                  <>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left">
                        <thead>
                          <tr className="text-xs text-gray-500 uppercase tracking-wider border-b border-gray-700 bg-gray-900/30">
                            <th className="py-3 px-4">
                              <input type="checkbox" checked={selected.size === files.length && files.length > 0} onChange={toggleAll} className="rounded" />
                            </th>
                            <th className="py-3 px-4">Filename</th>
                            <th className="py-3 px-4">Ext</th>
                            <th className="py-3 px-4">Size</th>
                            <th className="py-3 px-4">Status</th>
                            <th className="py-3 px-4">Action</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-700/40">
                          {files.map(file => {
                            const res = results[file._id];
                            const isVerifying = verifyingId === file._id;
                            return (
                              <React.Fragment key={file._id}>
                                <tr className="hover:bg-gray-700/20">
                                  <td className="py-3 px-4">
                                    <input type="checkbox" checked={selected.has(file._id)} onChange={() => toggleSelect(file._id)} className="rounded" />
                                  </td>
                                  <td className="py-3 px-4 text-sm text-white font-medium truncate max-w-[180px]" title={file.filename}>{file.filename}</td>
                                  <td className="py-3 px-4">
                                    <span className="px-2 py-0.5 bg-gray-700 text-gray-300 text-xs rounded-full">{file.file_extension?.toUpperCase() || 'BIN'}</span>
                                  </td>
                                  <td className="py-3 px-4 text-xs text-gray-400">
                                    {file.size >= 1048576 ? `${(file.size / 1048576).toFixed(1)} MB` : `${(file.size / 1024).toFixed(1)} KB`}
                                  </td>
                                  <td className="py-3 px-4">
                                    {res && (
                                      <span className={`text-xs font-semibold ${STATUS_CONFIG[res.verification_status]?.color || 'text-gray-400'}`}>
                                        {STATUS_CONFIG[res.verification_status]?.label || res.verification_status}
                                      </span>
                                    )}
                                  </td>
                                  <td className="py-3 px-4">
                                    <button
                                      onClick={() => doVerify(file._id, file.filename)}
                                      disabled={isVerifying || batchRunning}
                                      className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
                                    >
                                      {isVerifying ? <Loader className="w-3 h-3 animate-spin" /> : <Hash className="w-3 h-3" />}
                                      {isVerifying ? 'Verifying…' : 'Verify'}
                                    </button>
                                  </td>
                                </tr>
                                {res && (
                                  <tr>
                                    <td colSpan={6} className="px-4 pb-4">
                                      <VerificationResult result={res} />
                                    </td>
                                  </tr>
                                )}
                              </React.Fragment>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
              </div>
            )}

            {tab === 'hash' && (
              <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 space-y-4">
                <h3 className="text-sm font-semibold text-gray-300">Search Files by Hash Value</h3>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={hashInput}
                    onChange={e => setHashInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleHashSearch()}
                    placeholder="Paste SHA256, MD5, or SHA1 hash…"
                    className="flex-1 bg-gray-900 border border-gray-700 text-white rounded-lg p-2.5 text-sm font-mono focus:ring-blue-500 focus:border-blue-500"
                  />
                  <button
                    onClick={handleHashSearch}
                    disabled={searching || !hashInput.trim()}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50 flex items-center gap-2"
                  >
                    {searching ? <Loader className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                    Search
                  </button>
                </div>
                {searchResults.length > 0 && (
                  <div className="space-y-3">
                    <p className="text-sm text-gray-400">{searchResults.length} file(s) found:</p>
                    {searchResults.map(file => (
                      <div key={file._id} className="bg-gray-900/60 border border-gray-700 rounded-xl p-4 flex items-center justify-between gap-4">
                        <div>
                          <p className="text-sm font-medium text-white">{file.filename}</p>
                          <p className="text-xs text-gray-400 font-mono mt-0.5">{file.hash_sha256?.slice(0, 32)}…</p>
                        </div>
                        <button
                          onClick={() => doVerify(file._id, file.filename)}
                          disabled={verifyingId === file._id}
                          className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-xs font-semibold"
                        >
                          {verifyingId === file._id ? <Loader className="w-3 h-3 animate-spin" /> : 'Verify'}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* History sidebar */}
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
              <ClipboardList className="w-4 h-4 text-blue-400" />
              Verification History
            </h3>
            {history.length === 0 ? (
              <p className="text-xs text-gray-500 italic">No verifications yet this session.</p>
            ) : (
              <div className="space-y-2">
                {history.map((h, i) => {
                  const cfg = STATUS_CONFIG[h.status] || STATUS_CONFIG.unverifiable;
                  const Icon = cfg.icon;
                  return (
                    <div key={i} className="flex items-center gap-2 py-2 border-b border-gray-700/40 last:border-0">
                      <Icon className={`w-4 h-4 flex-shrink-0 ${cfg.color}`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-white truncate font-medium">{h.filename}</p>
                        <p className={`text-xs ${cfg.color}`}>{cfg.label}</p>
                      </div>
                      <span className="text-xs text-gray-500 flex-shrink-0">{h.time}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
