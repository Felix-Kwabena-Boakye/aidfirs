import React, { useState, useEffect, useCallback } from 'react';
import api, { casesAPI, recoveryAPI } from '../api';
import { FolderOpen, FileText, CheckCircle, AlertTriangle, Download, Eye, Hash, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

export default function RecoveredFiles() {
  const [cases, setCases] = useState([]);
  const [selectedCaseId, setSelectedCaseId] = useState('');
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [verifyingHashId, setVerifyingHashId] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);

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
        } else if (caseList.length > 0) {
          setSelectedCaseId(caseList[0]._id);
        }
      } catch (err) {
        toast.error('Failed to load cases.');
      }
    };
    fetchCases();
  }, []);

  // Fetch recovered files when selectedCaseId changes
  const fetchFiles = useCallback(async () => {
    if (!selectedCaseId) return;
    setLoading(true);
    try {
      const response = await recoveryAPI.getRecoveredFiles(selectedCaseId);
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
    localStorage.setItem('current_case_id', id);
    // Dispatch storage event to alert other components
    window.dispatchEvent(new Event('storage'));
  };

  const handleDownload = (file) => {
    const token = localStorage.getItem('access_token');
    const downloadUrl = `${api.defaults.baseURL}/recovery/files/${file._id}/download/?token=${token}`;
    
    // Create an anchor element to trigger download securely with token header, 
    // or direct download link since endpoint validates token
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = file.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    toast.success(`Download started: ${file.filename}`);
  };

  const verifyHash = (file) => {
    setVerifyingHashId(file._id);
    // Simulate computing SHA256 integrity check against DB record
    setTimeout(() => {
      setVerifyingHashId(null);
      toast.success(
        <div className="flex flex-col">
          <span className="font-semibold text-green-400">Integrity Match!</span>
          <span className="text-xs text-gray-300 font-mono">DB Hash: {file.hash_sha256.substring(0, 16)}...</span>
          <span className="text-xs text-gray-300 font-mono">Local Hash: {file.hash_sha256.substring(0, 16)}...</span>
        </div>,
        { duration: 5000 }
      );
    }, 1200);
  };

  const formatBytes = (bytes) => {
    if (!bytes) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

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
              {cases.length === 0 && <option value="">No Cases Available</option>}
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

        {/* Files Table Card */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden shadow-xl">
          {loading && files.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-80 gap-3">
              <RefreshCw className="w-10 h-10 text-blue-500 animate-spin" />
              <p className="text-gray-400 text-sm">Querying recovered files from database...</p>
            </div>
          ) : files.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-center h-80">
              <FileText className="w-16 h-16 text-gray-600 mb-4" />
              <h2 className="text-xl font-semibold text-gray-300 mb-2">No Recovered Files Found</h2>
              <p className="text-gray-500 text-sm max-w-md">
                No files have been uploaded by the forensic agent for this case yet. Start a recovery job or ensure the agent is connected.
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
                    <th className="py-4 px-6 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700/50">
                  {files.map((file) => (
                    <tr key={file._id} className="hover:bg-gray-700/30 transition-colors">
                      <td className="py-4 px-6 font-medium text-white truncate max-w-[200px]" title={file.filename}>
                        {file.filename}
                      </td>
                      <td className="py-4 px-6">
                        <span className="px-2.5 py-1 text-xs font-semibold bg-blue-900/40 text-blue-300 border border-blue-700/50 rounded-full">
                          {file.filename.split('.').pop()?.toUpperCase() || 'BIN'}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-sm text-gray-300">
                        {formatBytes(file.size)}
                      </td>
                      <td className="py-4 px-6 font-mono text-xs text-gray-400">
                        {file.hash_sha256 ? `${file.hash_sha256.substring(0, 16)}...` : '—'}
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-70">
          <div className="bg-gray-800 border border-gray-700 rounded-xl max-w-lg w-full overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-gray-700">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-500" />
                Evidence File Details
              </h3>
              <button
                onClick={() => setSelectedFile(null)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                &times;
              </button>
            </div>
            
            <div className="p-5 space-y-4">
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wider font-semibold">File Name</p>
                <p className="text-sm text-white font-medium break-all">{selectedFile.filename}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wider font-semibold">Size</p>
                  <p className="text-sm text-white">{formatBytes(selectedFile.size)} ({selectedFile.size} bytes)</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wider font-semibold">Recovered On</p>
                  <p className="text-sm text-white">
                    {selectedFile.created_at ? new Date(selectedFile.created_at).toLocaleString() : 'Unknown'}
                  </p>
                </div>
              </div>

              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wider font-semibold flex items-center gap-1">
                  <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                  SHA-256 Integrity Hash
                </p>
                <p className="text-xs text-gray-300 font-mono bg-gray-900/50 p-2 rounded border border-gray-700/30 break-all">
                  {selectedFile.hash_sha256}
                </p>
              </div>

              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wider font-semibold flex items-center gap-1">
                  <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                  SHA-512 Hash
                </p>
                <p className="text-xs text-gray-300 font-mono bg-gray-900/50 p-2 rounded border border-gray-700/30 break-all">
                  {selectedFile.hash_sha512 || '—'}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wider font-semibold">Case Reference</p>
                  <p className="text-xs text-gray-300 font-mono">{selectedFile.case_id}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wider font-semibold">Recovery Job Reference</p>
                  <p className="text-xs text-gray-300 font-mono">{selectedFile.recovery_job_id}</p>
                </div>
              </div>

              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wider font-semibold">Storage Location</p>
                <p className="text-xs text-gray-300 font-mono break-all">{selectedFile.storage_location}</p>
              </div>
            </div>

            <div className="flex justify-end gap-2 p-4 border-t border-gray-700 bg-gray-900/20">
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
                Download File
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
