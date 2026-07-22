import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { casesAPI, recoveryAPI } from '../api';
import { FolderOpen, FileText, CheckCircle, AlertTriangle, Download, Eye, Hash, RefreshCw, Search, Shield } from 'lucide-react';
import { toast } from 'sonner';

export default function RecoveredFiles() {
  const navigate = useNavigate();
  const [cases, setCases] = useState([]);
  const [selectedCaseId, setSelectedCaseId] = useState('');
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [verifyingHashId, setVerifyingHashId] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState('');
  const [filterExtension, setFilterExtension] = useState('');
  const [filterMinSize, setFilterMinSize] = useState('');

  // Load cases
  useEffect(() => {
    const fetchCases = async () => {
      try {
        const response = await casesAPI.getCases();
        const caseList = response.data || [];
        setCases(caseList);
        
        // Default to active case in localStorage if present
        const cachedCaseId = localStorage.getItem('current_case_id');
        if (cachedCaseId && caseList.some(c => c._id === cachedCaseId)) {
          setSelectedCaseId(cachedCaseId);
        } else {
          setSelectedCaseId(''); // default to all cases
        }
      } catch (err) {
        toast.error('Failed to load cases.');
      }
    };
    fetchCases();
  }, []);

  // Fetch recovered files when selectedCaseId changes
  const fetchFiles = useCallback(async () => {
    setLoading(true);
    try {
      let response;
      if (selectedCaseId) {
        response = await recoveryAPI.getRecoveredFiles(selectedCaseId);
      } else {
        response = await recoveryAPI.getAllFiles();
      }
      setFiles(response.data.files || []);
    } catch (err) {
      toast.error('Failed to load recovered files.');
    } finally {
      setLoading(false);
    }
  }, [selectedCaseId]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  const handleCaseChange = (e) => {
    const id = e.target.value;
    setSelectedCaseId(id);
    if (id) {
      localStorage.setItem('current_case_id', id);
    } else {
      localStorage.removeItem('current_case_id');
    }
    window.dispatchEvent(new Event('storage'));
  };

  const handleDownload = (file) => {
    const token = localStorage.getItem('access_token');
    const downloadUrl = `${api.defaults.baseURL}/recovery/files/${file._id}/download/?token=${token}`;
    
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = file.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    toast.success(`Download started: ${file.filename}`);
  };

  const verifyHash = async (file) => {
    setVerifyingHashId(file._id);
    try {
      const res = await recoveryAPI.verifyFileHash(file._id);
      const result = res.data;
      const status = result.verification_status;
      const hashes = result.hashes || {};

      if (status === 'verified') {
        toast.success(
          <div className="flex flex-col gap-1 text-left">
            <span className="font-semibold text-green-400">✓ Integrity Verified</span>
            <span className="text-xs text-gray-300 font-mono">
              SHA256: {hashes.sha256?.computed?.substring(0, 16)}…
            </span>
            <span className="text-xs text-gray-400">All hashes match database record.</span>
          </div>,
          { duration: 6000 }
        );
      } else if (status === 'modified') {
        toast.error(
          <div className="flex flex-col gap-1 text-left">
            <span className="font-semibold text-red-400">⚠ TAMPERING DETECTED</span>
            <span className="text-xs">Hash mismatch — file may have been altered.</span>
            <span className="text-xs font-mono">SHA256 match: {String(hashes.sha256?.match)}</span>
          </div>,
          { duration: 8000 }
        );
      } else {
        toast.warning(
          <div className="flex flex-col gap-1 text-left">
            <span className="font-semibold text-yellow-300">Unverifiable</span>
            <span className="text-xs">Insufficient hash data for complete verification.</span>
          </div>,
          { duration: 5000 }
        );
      }
    } catch (err) {
      toast.error(`Hash verification failed: ${err.response?.data?.error || 'Server error'}`);
    } finally {
      setVerifyingHashId(null);
    }
  };

  const formatBytes = (bytes) => {
    if (!bytes) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Client-side search and filtering
  const filteredFiles = files.filter(file => {
    const q = searchQuery.toLowerCase().strip ? searchQuery.toLowerCase().trim() : searchQuery.toLowerCase();
    const nameMatch = file.filename.toLowerCase().includes(q);
    const hashMatch = (file.hash_sha256 || '').toLowerCase().includes(q) ||
                      (file.hash_md5 || '').toLowerCase().includes(q) ||
                      (file.hash_sha1 || '').toLowerCase().includes(q);
    const textMatch = (file.description || '').toLowerCase().includes(q) ||
                      (file.recovery_method || '').toLowerCase().includes(q);

    const matchesSearch = q === '' || nameMatch || hashMatch || textMatch;

    const ext = filterExtension.trim().toLowerCase().replace('.', '');
    const matchesExt = ext === '' || (file.file_extension || '').toLowerCase() === ext || file.filename.toLowerCase().endsWith('.' + ext);

    let matchesSize = true;
    if (filterMinSize.trim() !== '') {
      const minBytes = parseFloat(filterMinSize) * 1024 * 1024; // MB
      if (!isNaN(minBytes)) {
        matchesSize = file.size >= minBytes;
      }
    }

    return matchesSearch && matchesExt && matchesSize;
  });

  return (
    <div className="p-6 min-h-screen bg-gray-900 text-white">
      <div className="max-w-6xl mx-auto">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <FolderOpen className="w-8 h-8 text-blue-500" />
              Recovered Files
            </h1>
            <p className="text-gray-400 text-sm mt-1">
              Browse, preview, and securely download files recovered by local forensic agents.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-400 font-medium">Select Case:</span>
            <select
              value={selectedCaseId}
              onChange={handleCaseChange}
              className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 p-2.5 min-w-[200px]"
            >
              <option value="">— All Cases (Global View) —</option>
              {cases.map((c) => (
                <option key={c._id} value={c._id}>
                  {c.case_number} - {c.title}
                </option>
              ))}
            </select>
            <button
              onClick={fetchFiles}
              disabled={loading}
              className="p-2.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-gray-300 hover:text-white transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Search & Filters */}
        <div className="bg-gray-850 border border-gray-700 rounded-xl p-4 mb-6 grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="relative">
            <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Search File/Hash/Desc</label>
            <div className="relative">
              <input
                type="text"
                placeholder="Filename, SHA256, MD5..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg pl-8 pr-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <Search className="w-4 h-4 text-gray-500 absolute left-2.5 top-3" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Extension</label>
            <input
              type="text"
              placeholder="e.g. pdf, jpg, zip"
              value={filterExtension}
              onChange={e => setFilterExtension(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Min Size (MB)</label>
            <input
              type="number"
              placeholder="e.g. 1"
              value={filterMinSize}
              onChange={e => setFilterMinSize(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={() => { setSearchQuery(''); setFilterExtension(''); setFilterMinSize(''); }}
              className="w-full bg-gray-700 hover:bg-gray-600 text-white text-xs font-semibold rounded-lg py-2.5 transition-colors"
            >
              Reset Filters
            </button>
          </div>
        </div>

        {/* Files Table Card */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden shadow-xl">
          {loading && files.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-80 gap-3">
              <RefreshCw className="w-10 h-10 text-blue-500 animate-spin" />
              <p className="text-gray-400 text-sm">Querying recovered files from database...</p>
            </div>
          ) : filteredFiles.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-center h-80">
              <FileText className="w-16 h-16 text-gray-600 mb-4" />
              <h2 className="text-xl font-semibold text-gray-300 mb-2">No Recovered Files Found</h2>
              <p className="text-gray-500 text-sm max-w-md">
                No files match your query or have been uploaded by the forensic agent for this view yet.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-gray-900 border-b border-gray-700 text-gray-400 text-xs font-semibold uppercase tracking-wider">
                    <th className="py-4 px-6">File Name</th>
                    <th className="py-4 px-6">Type</th>
                    <th className="py-4 px-6">Size</th>
                    <th className="py-4 px-6">SHA-256 Hash</th>
                    <th className="py-4 px-6">Recovery Method</th>
                    <th className="py-4 px-6 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700/50">
                  {filteredFiles.map((file) => (
                    <tr key={file._id} className="hover:bg-gray-700/30 transition-colors">
                      <td className="py-4 px-6 font-medium text-white truncate max-w-[200px]" title={file.filename}>
                        {file.filename}
                      </td>
                      <td className="py-4 px-6">
                        <span className="px-2.5 py-1 text-xs font-semibold bg-blue-900/40 text-blue-300 border border-blue-700/50 rounded-full">
                          {(file.file_extension || file.filename.split('.').pop() || 'BIN').toUpperCase()}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-sm text-gray-300">
                        {formatBytes(file.size)}
                      </td>
                      <td className="py-4 px-6 font-mono text-xs text-gray-400">
                        {file.hash_sha256 ? `${file.hash_sha256.substring(0, 16)}...` : '—'}
                      </td>
                      <td className="py-4 px-6 text-sm text-gray-400 italic">
                        {file.recovery_method || 'Signature Carving'}
                      </td>
                      <td className="py-4 px-6 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => setSelectedFile(file)}
                            className="p-1.5 bg-gray-700 hover:bg-gray-600 rounded text-gray-300 hover:text-white transition-colors"
                            title="Preview Details"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => verifyHash(file)}
                            disabled={verifyingHashId === file._id}
                            className="p-1.5 bg-gray-700 hover:bg-gray-600 rounded text-gray-300 hover:text-white transition-colors disabled:opacity-50"
                            title="Verify Hash Integrity"
                          >
                            <Hash className={`w-4 h-4 ${verifyingHashId === file._id ? 'animate-pulse text-yellow-400' : ''}`} />
                          </button>
                          <button
                            onClick={() => handleDownload(file)}
                            className="p-1.5 bg-blue-600 hover:bg-blue-500 rounded text-white transition-colors"
                            title="Secure Download"
                          >
                            <Download className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Details Preview Modal */}
      {selectedFile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-70 backdrop-blur-sm">
          <div className="bg-gray-800 border border-gray-700 rounded-xl max-w-lg w-full overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-gray-700 bg-gray-900/40">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-500" />
                Forensic Evidence Details
              </h3>
              <button
                onClick={() => setSelectedFile(null)}
                className="text-gray-400 hover:text-white transition-colors text-2xl font-bold"
              >
                &times;
              </button>
            </div>
            
            <div className="p-5 space-y-4 max-h-[70vh] overflow-y-auto">
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold">File Name</p>
                <p className="text-sm text-white font-medium break-all bg-gray-900/40 p-2 rounded">{selectedFile.filename}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold">File Size</p>
                  <p className="text-sm text-gray-200">{formatBytes(selectedFile.size)} ({selectedFile.size} bytes)</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Examiner</p>
                  <p className="text-sm text-gray-200">{selectedFile.examiner || 'Unknown'}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Recovery Method</p>
                  <p className="text-sm text-blue-400 font-semibold">{selectedFile.recovery_method || 'Signature Carving'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Recovery Status</p>
                  <p className="text-sm text-green-400 font-semibold">{selectedFile.recovery_status || 'Recovered'}</p>
                </div>
              </div>

              {selectedFile.original_path && (
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Original Device Path</p>
                  <p className="text-xs text-gray-300 font-mono bg-gray-900/40 p-2 rounded break-all">{selectedFile.original_path}</p>
                </div>
              )}

              {selectedFile.carve_offset !== undefined && selectedFile.carve_offset !== null && (
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Carve Byte Offset</p>
                  <p className="text-sm text-gray-300 font-mono">
                    {selectedFile.carve_offset} (0x{selectedFile.carve_offset.toString(16).toUpperCase()})
                  </p>
                </div>
              )}

              {/* Hashes Section */}
              <div className="border-t border-gray-700/60 pt-3 space-y-2">
                <span className="text-xs text-gray-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-blue-500" />
                  Forensic Cryptographic Signatures
                </span>
                <div>
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider">SHA-256</p>
                  <p className="text-xs text-gray-300 font-mono bg-gray-900/50 p-2 rounded break-all">{selectedFile.hash_sha256}</p>
                </div>
                {selectedFile.hash_md5 && (
                  <div>
                    <p className="text-[10px] text-gray-500 uppercase tracking-wider">MD5</p>
                    <p className="text-xs text-gray-300 font-mono bg-gray-900/50 p-2 rounded break-all">{selectedFile.hash_md5}</p>
                  </div>
                )}
                {selectedFile.hash_sha1 && (
                  <div>
                    <p className="text-[10px] text-gray-500 uppercase tracking-wider">SHA-1</p>
                    <p className="text-xs text-gray-300 font-mono bg-gray-900/50 p-2 rounded break-all">{selectedFile.hash_sha1}</p>
                  </div>
                )}
              </div>

              {/* Timestamps Section */}
              <div className="border-t border-gray-700/60 pt-3 grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Modified Time</p>
                  <p className="text-xs text-gray-300 font-mono">{selectedFile.modified_time || '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Created Time</p>
                  <p className="text-xs text-gray-300 font-mono">{selectedFile.created_time || '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Accessed Time</p>
                  <p className="text-xs text-gray-300 font-mono">{selectedFile.accessed_time || '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Imported to System</p>
                  <p className="text-xs text-gray-300 font-mono">
                    {selectedFile.created_at ? new Date(selectedFile.created_at).toLocaleString() : '—'}
                  </p>
                </div>
              </div>
            </div>

            <div className="flex justify-between items-center p-4 border-t border-gray-700 bg-gray-900/40">
              <button
                onClick={() => {
                  setSelectedFile(null);
                  navigate(`/evidence-preview?file_id=${selectedFile._id}&case_id=${selectedFile.case_id}`);
                }}
                className="px-4 py-2 text-xs font-semibold bg-gray-700 hover:bg-gray-600 rounded-lg text-white transition-colors flex items-center gap-1.5"
              >
                <Eye className="w-3.5 h-3.5 text-blue-400" />
                Hex/Media Preview
              </button>
              <div className="flex gap-2">
                <button
                  onClick={() => setSelectedFile(null)}
                  className="px-4 py-2 text-xs font-semibold bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
                >
                  Close
                </button>
                <button
                  onClick={() => {
                    handleDownload(selectedFile);
                    setSelectedFile(null);
                  }}
                  className="px-4 py-2 text-xs font-semibold bg-blue-600 hover:bg-blue-500 rounded-lg text-white transition-colors flex items-center gap-1.5"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

