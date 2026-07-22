import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import api, { recoveryAPI, casesAPI } from '../api';
import {
  Eye, Download, RefreshCw, Copy, CheckCircle, FileText,
  Image, Film, Music, Code, Hash, AlertTriangle, Loader
} from 'lucide-react';
import { toast } from 'sonner';

function formatBytes(bytes) {
  if (!bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

// Hex viewer component
function HexViewer({ data }) {
  if (!data) return null;
  const bytes = Array.from(new Uint8Array(data));
  const rows = [];
  for (let i = 0; i < bytes.length; i += 16) {
    const chunk = bytes.slice(i, i + 16);
    const hex = chunk.map(b => b.toString(16).padStart(2, '0').toUpperCase()).join(' ');
    const ascii = chunk.map(b => (b >= 32 && b < 127) ? String.fromCharCode(b) : '.').join('');
    rows.push({ offset: i, hex, ascii });
  }
  return (
    <div className="font-mono text-xs overflow-auto max-h-[400px] bg-gray-950 p-4 rounded-xl border border-gray-700">
      <div className="text-gray-500 mb-2">Hex Dump (first {bytes.length} bytes)</div>
      {rows.map(row => (
        <div key={row.offset} className="flex gap-4 leading-5 hover:bg-gray-800/50">
          <span className="text-gray-600 w-12 flex-shrink-0">{row.offset.toString(16).padStart(8, '0')}</span>
          <span className="text-green-400 flex-1">{row.hex.padEnd(47)}</span>
          <span className="text-gray-400">{row.ascii}</span>
        </div>
      ))}
    </div>
  );
}

// Determine preview type from mime_type or extension
function getPreviewType(file) {
  const mime = file?.mime_type || '';
  const ext = (file?.file_extension || file?.filename?.split('.').pop() || '').toLowerCase();
  if (mime.startsWith('image/') || ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(ext)) return 'image';
  if (mime === 'application/pdf' || ext === 'pdf') return 'pdf';
  if (mime.startsWith('video/') || ['mp4', 'avi', 'mov', 'mkv', 'webm'].includes(ext)) return 'video';
  if (mime.startsWith('audio/') || ['mp3', 'wav', 'ogg', 'flac', 'm4a'].includes(ext)) return 'audio';
  if (mime.startsWith('text/') || ['txt', 'log', 'md', 'csv', 'html', 'xml', 'json', 'js', 'py', 'sh', 'bat', 'cfg', 'ini'].includes(ext)) return 'text';
  return 'binary';
}

export default function EvidencePreview() {
  const [searchParams] = useSearchParams();
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState('');
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [previewContent, setPreviewContent] = useState(null); // text or ArrayBuffer
  const [previewError, setPreviewError] = useState(null);
  const [copied, setCopied] = useState('');

  const token = localStorage.getItem('access_token');

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
    setLoadingFiles(true);
    setSelectedFile(null);
    setPreviewContent(null);
    try {
      const res = await recoveryAPI.getRecoveredFiles(selectedCase);
      const list = res.data.files || [];
      setFiles(list);
      // Check for pre-selected file via query param
      const fileIdParam = searchParams.get('file_id');
      if (fileIdParam) {
        const match = list.find(f => f._id === fileIdParam);
        if (match) setSelectedFile(match);
      }
    } catch {
      toast.error('Failed to load files.');
    } finally {
      setLoadingFiles(false);
    }
  }, [selectedCase, searchParams]);

  useEffect(() => { fetchFiles(); }, [fetchFiles]);

  // Load preview when file selected
  useEffect(() => {
    if (!selectedFile) { setPreviewContent(null); return; }
    const previewType = getPreviewType(selectedFile);
    if (previewType === 'image' || previewType === 'video' || previewType === 'audio' || previewType === 'pdf') {
      // These are served directly via URL with token, no fetch needed
      setPreviewContent({ type: previewType, url: `${api.defaults.baseURL}/recovery/files/${selectedFile._id}/preview/` });
      return;
    }
    // Text and binary: fetch with auth header
    setLoadingPreview(true);
    setPreviewError(null);
    const url = `${api.defaults.baseURL}/recovery/files/${selectedFile._id}/preview/`;
    const maxBytes = previewType === 'binary' ? 1024 : 64 * 1024;
    fetch(url, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(async res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        if (previewType === 'text') {
          const text = await res.text();
          setPreviewContent({ type: 'text', content: text.slice(0, maxBytes) });
        } else {
          const buf = await res.arrayBuffer();
          setPreviewContent({ type: 'binary', content: buf.slice(0, 1024) });
        }
      })
      .catch(err => setPreviewError(err.message))
      .finally(() => setLoadingPreview(false));
  }, [selectedFile, token]);

  const handleDownload = () => {
    if (!selectedFile) return;
    const url = `${api.defaults.baseURL}/recovery/files/${selectedFile._id}/download/?token=${token}`;
    const a = document.createElement('a');
    a.href = url;
    a.download = selectedFile.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    toast.success(`Download: ${selectedFile.filename}`);
  };

  const copyHash = (hash, label) => {
    navigator.clipboard.writeText(hash);
    setCopied(label);
    setTimeout(() => setCopied(''), 1500);
  };

  const previewType = selectedFile ? getPreviewType(selectedFile) : null;

  return (
    <div className="p-6 min-h-screen bg-gray-900 text-white">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Eye className="w-7 h-7 text-blue-500" />
              Evidence Preview
            </h1>
            <p className="text-gray-400 text-sm mt-1">In-browser forensic evidence viewer with hex analysis.</p>
          </div>
          <select
            value={selectedCase}
            onChange={e => { setSelectedCase(e.target.value); localStorage.setItem('current_case_id', e.target.value); }}
            className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg p-2.5 min-w-[220px]"
          >
            <option value="">— Select Case —</option>
            {cases.map(c => <option key={c._id} value={c._id}>{c.case_number} — {c.title}</option>)}
          </select>
        </div>

        <div className="flex gap-4 h-[calc(100vh-200px)] min-h-[500px]">
          {/* File List (left) */}
          <div className="w-64 flex-shrink-0 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden flex flex-col">
            <div className="px-4 py-3 border-b border-gray-700 bg-gray-900/40 flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Files ({files.length})</span>
              <button onClick={fetchFiles} className="text-gray-500 hover:text-gray-300">
                <RefreshCw className={`w-3.5 h-3.5 ${loadingFiles ? 'animate-spin' : ''}`} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              {loadingFiles ? (
                <div className="flex justify-center items-center h-24">
                  <Loader className="w-5 h-5 text-blue-500 animate-spin" />
                </div>
              ) : files.length === 0 ? (
                <p className="text-xs text-gray-500 p-4 text-center">No files found.</p>
              ) : (
                files.map(file => {
                  const isSelected = selectedFile?._id === file._id;
                  const pt = getPreviewType(file);
                  const icons = { image: Image, video: Film, audio: Music, text: Code, pdf: FileText, binary: Hash };
                  const FIcon = icons[pt] || FileText;
                  return (
                    <button
                      key={file._id}
                      onClick={() => setSelectedFile(file)}
                      className={`w-full text-left px-4 py-3 border-b border-gray-700/40 hover:bg-gray-700/40 transition-colors ${isSelected ? 'bg-blue-600/20 border-l-2 border-l-blue-500' : ''}`}
                    >
                      <div className="flex items-center gap-2">
                        <FIcon className="w-4 h-4 text-gray-400 flex-shrink-0" />
                        <span className="text-xs text-gray-200 truncate font-medium">{file.filename}</span>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-gray-500">{formatBytes(file.size)}</span>
                        <span className="text-xs text-gray-600">{(file.file_extension || '?').toUpperCase()}</span>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          {/* Preview + Metadata (right) */}
          <div className="flex-1 flex flex-col gap-4 overflow-hidden">
            {/* Preview pane */}
            <div className="flex-1 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden flex flex-col">
              <div className="flex items-center justify-between px-5 py-3 border-b border-gray-700 bg-gray-900/40">
                <div className="flex items-center gap-2">
                  <Eye className="w-4 h-4 text-blue-400" />
                  <span className="text-sm font-semibold text-gray-200">
                    {selectedFile ? selectedFile.filename : 'Select a file to preview'}
                  </span>
                  {selectedFile && (
                    <span className="text-xs text-gray-500 ml-1">({previewType})</span>
                  )}
                </div>
                {selectedFile && (
                  <button
                    onClick={handleDownload}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-semibold"
                  >
                    <Download className="w-3.5 h-3.5" /> Download
                  </button>
                )}
              </div>
              <div className="flex-1 overflow-auto p-4">
                {!selectedFile && (
                  <div className="flex flex-col items-center justify-center h-full text-gray-600">
                    <Eye className="w-16 h-16 mb-3" />
                    <p>Choose a file from the list to preview it here.</p>
                  </div>
                )}
                {selectedFile && loadingPreview && (
                  <div className="flex justify-center items-center h-full">
                    <Loader className="w-8 h-8 text-blue-500 animate-spin" />
                  </div>
                )}
                {selectedFile && previewError && (
                  <div className="flex flex-col items-center justify-center h-full text-orange-400 gap-2">
                    <AlertTriangle className="w-10 h-10" />
                    <p className="text-sm">Preview failed: {previewError}</p>
                  </div>
                )}
                {selectedFile && !loadingPreview && !previewError && previewContent && (
                  <>
                    {previewContent.type === 'image' && (
                      <div className="flex justify-center">
                        <img
                          src={`${previewContent.url}?token=${token}`}
                          alt={selectedFile.filename}
                          className="max-w-full max-h-[400px] object-contain rounded-lg border border-gray-700"
                          onError={e => { e.target.style.display = 'none'; setPreviewError('Image failed to load'); }}
                        />
                      </div>
                    )}
                    {previewContent.type === 'pdf' && (
                      <embed
                        src={`${previewContent.url}?token=${token}`}
                        type="application/pdf"
                        className="w-full h-[400px] rounded-lg"
                      />
                    )}
                    {previewContent.type === 'video' && (
                      <video
                        controls
                        className="w-full max-h-[400px] rounded-lg"
                        src={`${previewContent.url}?token=${token}`}
                      />
                    )}
                    {previewContent.type === 'audio' && (
                      <div className="flex flex-col items-center justify-center h-full gap-4">
                        <Music className="w-16 h-16 text-blue-400" />
                        <audio controls src={`${previewContent.url}?token=${token}`} className="w-full max-w-lg" />
                      </div>
                    )}
                    {previewContent.type === 'text' && (
                      <pre className="text-xs text-gray-300 bg-gray-950 p-4 rounded-xl border border-gray-700 overflow-auto max-h-[400px] whitespace-pre-wrap break-all">
                        {previewContent.content}
                      </pre>
                    )}
                    {previewContent.type === 'binary' && (
                      <HexViewer data={previewContent.content} />
                    )}
                  </>
                )}
              </div>
            </div>

            {/* Metadata pane */}
            {selectedFile && (
              <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 flex-shrink-0">
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Evidence Metadata</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                  {[
                    { label: 'Size', value: formatBytes(selectedFile.size) },
                    { label: 'Extension', value: selectedFile.file_extension?.toUpperCase() || '—' },
                    { label: 'MIME Type', value: selectedFile.mime_type || '—' },
                    { label: 'Recovery Method', value: selectedFile.recovery_method || '—' },
                    { label: 'Examiner', value: selectedFile.examiner || '—' },
                    { label: 'Recovered At', value: selectedFile.created_at ? new Date(selectedFile.created_at).toLocaleString() : '—' },
                    { label: 'Modified Time', value: selectedFile.modified_time || '—' },
                    { label: 'Original Path', value: selectedFile.original_path || '—' },
                  ].map(item => (
                    <div key={item.label}>
                      <p className="text-gray-500 mb-0.5">{item.label}</p>
                      <p className="text-gray-200 font-medium truncate" title={item.value}>{item.value}</p>
                    </div>
                  ))}
                </div>
                {/* Hash display */}
                <div className="mt-3 space-y-1.5">
                  {[
                    { label: 'SHA-256', hash: selectedFile.hash_sha256 },
                    { label: 'MD5',     hash: selectedFile.hash_md5 },
                    { label: 'SHA-1',   hash: selectedFile.hash_sha1 },
                  ].filter(h => h.hash).map(({ label, hash }) => (
                    <div key={label} className="flex items-center gap-2 text-xs">
                      <span className="text-gray-500 w-14 flex-shrink-0">{label}:</span>
                      <span className="font-mono text-gray-400 flex-1 truncate">{hash}</span>
                      <button
                        onClick={() => copyHash(hash, label)}
                        className="text-gray-500 hover:text-gray-300 flex-shrink-0"
                      >
                        {copied === label ? <CheckCircle className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
