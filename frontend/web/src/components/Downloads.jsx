import React, { useState, useEffect, useCallback } from 'react';
import api, { recoveryAPI, casesAPI } from '../api';
import {
  Download, Shield, Eye, Archive, RefreshCw, CheckCircle,
  XCircle, AlertTriangle, Loader, FileText, Clock, Package
} from 'lucide-react';
import { toast } from 'sonner';

function formatBytes(bytes) {
  if (!bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

const VERIFY_STATES = {
  idle:       null,
  verifying:  { color: 'text-yellow-400', icon: Loader,        label: 'Verifying…' },
  verified:   { color: 'text-green-400',  icon: CheckCircle,   label: 'Verified' },
  modified:   { color: 'text-red-400',    icon: XCircle,       label: 'TAMPERED' },
  error:      { color: 'text-orange-400', icon: AlertTriangle, label: 'Error' },
};

function FileRow({ file, onDownload, onPreview }) {
  const [verifyState, setVerifyState] = useState('idle');
  const [verifyResult, setVerifyResult] = useState(null);
  const [showModal, setShowModal] = useState(false);

  const doVerifyAndDownload = async () => {
    setVerifyState('verifying');
    try {
      const res = await recoveryAPI.verifyFileHash(file._id);
      const result = res.data;
      setVerifyResult(result);
      if (result.verification_status === 'verified') {
        setVerifyState('verified');
        setShowModal(true);
      } else if (result.verification_status === 'modified') {
        setVerifyState('modified');
        toast.error(`⚠ TAMPERED: ${file.filename} — Hash mismatch detected. Download blocked.`);
      } else {
        setVerifyState('error');
        toast.warning(`Hash unverifiable for ${file.filename}. Download at your own risk.`);
        setShowModal(true);
      }
    } catch (err) {
      setVerifyState('error');
      toast.error(`Verification error: ${err.response?.data?.error || 'Connection failed'}`);
    }
  };

  const proceedDownload = () => {
    setShowModal(false);
    onDownload(file);
  };

  const stateInfo = verifyState !== 'idle' ? VERIFY_STATES[verifyState] : null;

  return (
    <>
      <tr className="hover:bg-gray-700/20 transition-colors">
        <td className="py-3 px-4 font-medium text-white text-sm truncate max-w-[180px]" title={file.filename}>
          {file.filename}
        </td>
        <td className="py-3 px-4">
          <span className="px-2 py-0.5 bg-gray-700 text-gray-300 text-xs rounded-full">
            {(file.file_extension || file.filename?.split('.').pop() || 'BIN').toUpperCase()}
          </span>
        </td>
        <td className="py-3 px-4 text-xs text-gray-400">{formatBytes(file.size)}</td>
        <td className="py-3 px-4 font-mono text-xs text-gray-500" title={file.hash_sha256}>
          {file.hash_sha256 ? file.hash_sha256.slice(0, 12) + '…' : '—'}
        </td>
        <td className="py-3 px-4 font-mono text-xs text-gray-500" title={file.hash_md5}>
          {file.hash_md5 ? file.hash_md5.slice(0, 12) + '…' : '—'}
        </td>
        <td className="py-3 px-4 text-xs text-gray-400">{file.recovery_method || '—'}</td>
        <td className="py-3 px-4">
          {stateInfo && (
            <div className={`flex items-center gap-1 text-xs font-semibold ${stateInfo.color}`}>
              <stateInfo.icon className={`w-3.5 h-3.5 ${verifyState === 'verifying' ? 'animate-spin' : ''}`} />
              {stateInfo.label}
            </div>
          )}
        </td>
        <td className="py-3 px-4">
          <div className="flex items-center gap-1.5">
            <button
              onClick={doVerifyAndDownload}
              disabled={verifyState === 'verifying' || verifyState === 'modified'}
              title="Verify integrity then download"
              className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
            >
              {verifyState === 'verifying' ? <Loader className="w-3 h-3 animate-spin" /> : <Shield className="w-3 h-3" />}
              Verify & Download
            </button>
            <button
              onClick={() => onPreview(file)}
              title="Preview in browser"
              className="p-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-gray-300 transition-colors"
            >
              <Eye className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => {
                toast.warning(`Downloading ${file.filename} without integrity verification.`);
                onDownload(file);
              }}
              title="Quick download (no verification)"
              className="p-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-gray-400 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
            </button>
          </div>
        </td>
      </tr>

      {/* Verification modal */}
      {showModal && verifyResult && (
        <tr>
          <td colSpan={8} className="px-4 pb-3">
            <div className={`border rounded-xl p-4 ${verifyResult.verification_status === 'verified' ? 'bg-green-900/20 border-green-700/40' : 'bg-yellow-900/20 border-yellow-700/40'}`}>
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  {verifyResult.verification_status === 'verified'
                    ? <CheckCircle className="w-5 h-5 text-green-400" />
                    : <AlertTriangle className="w-5 h-5 text-yellow-400" />
                  }
                  <span className={`font-semibold text-sm ${verifyResult.verification_status === 'verified' ? 'text-green-300' : 'text-yellow-300'}`}>
                    {verifyResult.verification_status === 'verified' ? 'Integrity Verified — Safe to Download' : 'Unverifiable — Proceed with Caution'}
                  </span>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => setShowModal(false)} className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-xs">Cancel</button>
                  <button onClick={proceedDownload} className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-semibold flex items-center gap-1">
                    <Download className="w-3 h-3" /> Download
                  </button>
                </div>
              </div>
              {verifyResult.hashes && (
                <div className="mt-3 grid grid-cols-3 gap-3 text-xs font-mono">
                  {['sha256', 'md5', 'sha1'].map(algo => {
                    const h = verifyResult.hashes[algo];
                    if (!h) return null;
                    return (
                      <div key={algo} className="bg-gray-900/40 rounded p-2">
                        <span className="text-gray-500 uppercase">{algo}:</span>
                        <span className={`ml-1 ${h.match === true ? 'text-green-400' : h.match === false ? 'text-red-400' : 'text-gray-400'}`}>
                          {h.match === true ? '✓' : h.match === false ? '✗' : '?'} {h.computed?.slice(0, 16)}…
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function Downloads() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState('');
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [exportingZip, setExportingZip] = useState(false);
  const [downloadHistory, setDownloadHistory] = useState([]);

  useEffect(() => {
    casesAPI.getCases().then(r => {
      const list = r.data || [];
      setCases(list);
      const cached = localStorage.getItem('current_case_id');
      if (cached && list.some(c => c._id === cached)) setSelectedCase(cached);
      else if (list.length > 0) setSelectedCase(list[0]._id);
    }).catch(() => {});
  }, []);

  const fetchFiles = useCallback(async () => {
    if (!selectedCase) return;
    setLoading(true);
    try {
      const res = await recoveryAPI.getRecoveredFiles(selectedCase);
      setFiles(res.data.files || []);
    } catch {
      toast.error('Failed to load files.');
    } finally {
      setLoading(false);
    }
  }, [selectedCase]);

  useEffect(() => { fetchFiles(); }, [fetchFiles]);

  const handleDownload = (file) => {
    const token = localStorage.getItem('access_token');
    const url = `${api.defaults.baseURL}/recovery/files/${file._id}/download/?token=${token}`;
    const a = document.createElement('a');
    a.href = url;
    a.download = file.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setDownloadHistory(prev => [{
      filename: file.filename,
      time: new Date().toLocaleTimeString(),
      size: formatBytes(file.size)
    }, ...prev.slice(0, 19)]);
    toast.success(`Download started: ${file.filename}`);
  };

  const handlePreview = (file) => {
    window.location.href = `/evidence-preview?file_id=${file._id}`;
  };

  const handleExportZip = async () => {
    if (!selectedCase) return;
    setExportingZip(true);
    try {
      const res = await recoveryAPI.exportZip(selectedCase);
      const url = URL.createObjectURL(res.data);
      const caseName = cases.find(c => c._id === selectedCase)?.case_number || selectedCase;
      const a = document.createElement('a');
      a.href = url;
      a.download = `AIDFIRS_${caseName}_Export.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('ZIP export downloaded successfully.');
    } catch {
      toast.error('Failed to export ZIP package.');
    } finally {
      setExportingZip(false);
    }
  };

  const totalSize = files.reduce((sum, f) => sum + (f.size || 0), 0);
  const verifiedCount = 0; // count from verifications would need state tracking

  return (
    <div className="p-6 min-h-screen bg-gray-900 text-white">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Download className="w-7 h-7 text-blue-500" />
              Download Manager
            </h1>
            <p className="text-gray-400 text-sm mt-1">
              Securely download forensic evidence with hash-verified integrity checks.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchFiles()}
              disabled={loading}
              className="p-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-gray-300"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={handleExportZip}
              disabled={!selectedCase || exportingZip || files.length === 0}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50"
            >
              {exportingZip ? <Loader className="w-4 h-4 animate-spin" /> : <Package className="w-4 h-4" />}
              {exportingZip ? 'Exporting…' : 'Export Case ZIP'}
            </button>
          </div>
        </div>

        {/* Case selector */}
        <div className="mb-5">
          <select
            value={selectedCase}
            onChange={e => { setSelectedCase(e.target.value); localStorage.setItem('current_case_id', e.target.value); }}
            className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg p-2.5 min-w-[220px]"
          >
            <option value="">— Select Case —</option>
            {cases.map(c => <option key={c._id} value={c._id}>{c.case_number} — {c.title}</option>)}
          </select>
        </div>

        {/* Stats */}
        {files.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-5">
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
              <p className="text-2xl font-bold">{files.length}</p>
              <p className="text-xs text-gray-400">Recovered Files</p>
            </div>
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
              <p className="text-2xl font-bold">{formatBytes(totalSize)}</p>
              <p className="text-xs text-gray-400">Total Size</p>
            </div>
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
              <p className="text-2xl font-bold">{downloadHistory.length}</p>
              <p className="text-xs text-gray-400">Downloads This Session</p>
            </div>
          </div>
        )}

        {/* Files table */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden shadow-xl mb-6">
          {loading ? (
            <div className="flex justify-center items-center h-52">
              <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
            </div>
          ) : !selectedCase ? (
            <div className="flex flex-col items-center justify-center h-52 text-gray-500">
              <Download className="w-12 h-12 mb-2" />
              <p>Select a case to view downloadable files.</p>
            </div>
          ) : files.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-52 text-gray-500">
              <FileText className="w-12 h-12 mb-2" />
              <p>No recovered files found for this case.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="bg-gray-900 border-b border-gray-700 text-xs text-gray-400 uppercase tracking-wider">
                    <th className="py-3 px-4">Filename</th>
                    <th className="py-3 px-4">Type</th>
                    <th className="py-3 px-4">Size</th>
                    <th className="py-3 px-4">SHA256</th>
                    <th className="py-3 px-4">MD5</th>
                    <th className="py-3 px-4">Method</th>
                    <th className="py-3 px-4">Integrity</th>
                    <th className="py-3 px-4">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700/40">
                  {files.map(file => (
                    <FileRow key={file._id} file={file} onDownload={handleDownload} onPreview={handlePreview} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Download history */}
        {downloadHistory.length > 0 && (
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-400" />
              Session Download History
            </h3>
            <div className="space-y-2">
              {downloadHistory.map((h, i) => (
                <div key={i} className="flex items-center justify-between text-xs border-b border-gray-700/40 last:border-0 py-2">
                  <span className="text-white font-medium">{h.filename}</span>
                  <span className="text-gray-500">{h.size}</span>
                  <span className="text-gray-500">{h.time}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
