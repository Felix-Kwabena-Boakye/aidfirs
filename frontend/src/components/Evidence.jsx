import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { evidenceAPI, casesAPI, analysisAPI } from '../api';

const Evidence = () => {
  const [evidence, setEvidence] = useState([]);
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [activeAnalysis, setActiveAnalysis] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);
  const [chatMessage, setChatMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isChatting, setIsChatting] = useState(false);
  const [ingestStatus, setIngestStatus] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();

  const [formData, setFormData] = useState({
    case_id: localStorage.getItem('current_case_id') || '',
    evidence_type: 'file',
    file_name: '',
    description: ''
  });

  const fetchEvidence = async () => {
    setLoading(true);
    try {
      const response = await evidenceAPI.getEvidence();
      setEvidence(response.data);
    } catch (err) {
      setError('Failed to load evidence');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchCases = async () => {
    try {
      const response = await casesAPI.getCases();
      setCases(response.data);
    } catch (err) {
      console.error('Failed to load cases', err);
    }
  };

  useEffect(() => {
    fetchEvidence();
    fetchCases();
  }, [searchParams]);

  // Handle auto-analysis or auto-ingest if IDs are in params
  useEffect(() => {
    const autoAnalyzeId = searchParams.get('auto_analyze');
    const autoIngestId = searchParams.get('auto_ingest');

    if (autoIngestId) {
      handleAutoIngest(autoIngestId);
      const newParams = new URLSearchParams(searchParams);
      newParams.delete('auto_ingest');
      setSearchParams(newParams, { replace: true });
    } else if (autoAnalyzeId) {
      handleAnalyzePartitions(autoAnalyzeId);
      const newParams = new URLSearchParams(searchParams);
      newParams.delete('auto_analyze');
      setSearchParams(newParams, { replace: true });
    }
  }, [searchParams, evidence.length]);

  // Sync formData when cases load or current case changes in localStorage
  useEffect(() => {
    const handleStorageChange = () => {
      const currentCaseId = localStorage.getItem('current_case_id') || '';
      if (currentCaseId) {
        setFormData(prev => ({ ...prev, case_id: currentCaseId }));
      }
    };

    // Initial sync
    handleStorageChange();

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, [cases]);

  const toggleForm = async () => {
    // Show form immediately
    const nextShowForm = !showForm;
    setShowForm(nextShowForm);

    if (nextShowForm) {
      // Refresh form data with current case
      const currentCaseId = localStorage.getItem('current_case_id') || '';

      // Reset form to defaults + current case
      setFormData({
        case_id: currentCaseId,
        evidence_type: 'file',
        file_name: '',
        description: ''
      });

      // Try to get AI suggestions in background
      try {
        const caseItem = cases.find(c => c._id === currentCaseId);
        const caseContext = caseItem ? `Case: ${caseItem.title}, Description: ${caseItem.description}` : 'No specific case context available.';

        const aiResponse = await analysisAPI.getEvidenceSuggestions(caseContext);
        const { fileName, description } = aiResponse.data;

        // Only update if form is still open
        setFormData(prev => ({
          ...prev,
          file_name: prev.file_name || fileName || '',
          description: prev.description || description || ''
        }));
      } catch (err) {
        console.error('Failed to get AI suggestions:', err);
      }
    }
  };

  const handleAutoIngest = async (id) => {
    setLoading(true);
    setError(null);
    try {
      setIngestStatus('Step 1/6: Bit-for-bit Imaging (FTK Imager)...');
      await evidenceAPI.tskImage(id);

      setIngestStatus('Step 2/6: Analyzing Partitions (TSK)...');
      const partResponse = await evidenceAPI.tskPartitions(id);

      setIngestStatus('Step 3/6: Recovering Deleted Metadata...');
      const metaResponse = await evidenceAPI.tskRecoveredMetadata(id);

      setIngestStatus('Step 4/6: AI File Classification...');
      const classResponse = await analysisAPI.classify(JSON.stringify(metaResponse.data));

      setIngestStatus('Step 5/6: Anomaly Detection Analysis...');
      const anomalyResponse = await analysisAPI.detectAnomalies(JSON.stringify(metaResponse.data));

      setIngestStatus('Step 6/6: Generating Comprehensive Forensic Report...');
      const caseItem = cases.find(c => c._id === (evidence.find(e => e._id === id)?.case_id || localStorage.getItem('current_case_id')));
      const caseContext = caseItem ? `Case: ${caseItem.title}\nDesc: ${caseItem.description}` : 'Unknown context';
      const aiFindings = `Classifications: ${JSON.stringify(classResponse.data.classification || classResponse.data.response)}\nAnomalies: ${anomalyResponse.data.anomalies || anomalyResponse.data.response}`;
      const reportResponse = await analysisAPI.generateReport(caseContext, JSON.stringify(metaResponse.data), aiFindings);

      setActiveAnalysis(id);
      setAnalysisData({
        ...metaResponse.data,
        type: 'metadata',
        automated: true,
        ai_classification: classResponse.data.classification || classResponse.data.response,
        ai_anomalies: anomalyResponse.data.anomalies || anomalyResponse.data.response,
        ai_report: reportResponse.data.report || reportResponse.data.response
      });
      setIngestStatus('Pipeline Complete: AI Forensic Acquisition & Analysis Finished.');

      // Clear status after a few seconds
      setTimeout(() => setIngestStatus(null), 5000);
    } catch (err) {
      console.error('Automation failed:', err);
      setError(`Automation Error: ${err.response?.data?.error || err.message}`);
      setIngestStatus(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await evidenceAPI.uploadEvidence(formData);
      setShowForm(false);
      fetchEvidence();
    } catch (err) {
      // Show detailed backend error if available
      const backendError = err.response?.data?.error;
      const validationErrors = err.response?.data;

      let errorMsg = 'Failed to upload evidence.';
      if (backendError) {
        errorMsg = backendError;
      } else if (validationErrors && typeof validationErrors === 'object') {
        // Collect all validation errors (e.g., {"file_name": ["This field is required"]})
        errorMsg = Object.entries(validationErrors)
          .map(([key, val]) => `${key}: ${Array.isArray(val) ? val.join(', ') : val}`)
          .join(' | ');
      }

      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'collected':
        return 'bg-green-100 text-green-800';
      case 'analyzing':
        return 'bg-blue-100 text-blue-800';
      case 'analyzed':
        return 'bg-purple-100 text-purple-800';
      case 'archived':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'file':
        return '📄';
      case 'disk_image':
        return '💾';
      case 'memory_dump':
        return '🧠';
      case 'network_capture':
        return '🌐';
      case 'log_file':
        return '📋';
      case 'registry':
        return '🔧';
      case 'email':
        return '📧';
      default:
        return '📁';
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return 'N/A';
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i), 2) + ' ' + sizes[i];
  };

  const handleAnalyzePartitions = async (id) => {
    setLoading(true);
    setError(null);
    try {
      const response = await evidenceAPI.tskPartitions(id);
      setActiveAnalysis(id);
      setAnalysisData(response.data);
    } finally {
      setLoading(false);
    }
  };

  const handleRecoverDeletedMetadata = async (id, offset = '0') => {
    setLoading(true);
    setError(null);
    try {
      const response = await evidenceAPI.tskRecoveredMetadata(id, offset);
      setActiveAnalysis(id);
      setAnalysisData({ ...response.data, type: 'metadata' });
    } catch (err) {
      const errorMsg = err.response?.data?.error || err.message || 'Failed to recover deleted metadata.';
      setError(`Recovery Error: ${errorMsg}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSendChatMessage = async () => {
    if (!chatMessage.trim()) return;

    const messageToSend = chatMessage;
    setIsChatting(true);
    const newMessage = { role: 'user', content: messageToSend };
    const updatedHistory = [...chatHistory, newMessage];
    setChatHistory(updatedHistory);
    setChatMessage('');

    try {
      const activeEvidenceItem = evidence.find(e => e._id === activeAnalysis);
      const caseItem = cases.find(c => c._id === activeEvidenceItem?.case_id);
      const context = caseItem ? `Case: ${caseItem.title}\nDesc: ${caseItem.description}` : 'Unknown case context';
      const forensicOutput = analysisData ? JSON.stringify(analysisData) : 'No forensic data analyzed yet';

      // Pass updatedHistory (which includes the current message) as the history context
      const response = await analysisAPI.chatWithAssistant(context, forensicOutput, messageToSend, updatedHistory);

      if (response.data.success || response.data.response) {
        setChatHistory(prev => [...prev, { role: 'assistant', content: response.data.response }]);
      } else {
        throw new Error(response.data.error || 'Unknown AI error');
      }
    } catch (err) {
      console.error('AI Chat Error:', err);
      const errorDetail = err.response?.data?.error || err.message;
      setChatHistory(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${errorDetail}. Please check your API key and connection.`
      }]);
    } finally {
      setIsChatting(false);
    }
  };

  const handleDownloadReport = async (id, fileName) => {
    try {
      const response = await evidenceAPI.downloadReport(id);

      // Create a URL for the blob and trigger download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `report_${fileName}.pdf`);
      document.body.appendChild(link);
      link.click();

      // Cleanup
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to download PDF report.');
      console.error(err);
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Evidence</h1>
        <button
          onClick={toggleForm}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          {showForm ? 'Cancel' : 'Add Evidence'}
        </button>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4 flex justify-between items-center">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-900 font-bold">&times;</button>
        </div>
      )}

      {analysisData?.mock && (
        <div className="bg-yellow-100 border border-yellow-400 text-yellow-800 px-4 py-2 rounded mb-4 flex items-center">
          <span className="mr-2">⚠️</span>
          <span><strong>Mock Mode Active:</strong> Digital forensic tools (TSK) are missing. Displaying simulated data for demonstration.</span>
        </div>
      )}

      {ingestStatus && (
        <div className="bg-blue-600 text-white px-4 py-3 rounded mb-4 flex items-center shadow-lg animate-pulse">
          <span className="mr-3">🚀</span>
          <span className="font-semibold">{ingestStatus}</span>
        </div>
      )}

      {showForm && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Add New Evidence</h2>
          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-gray-700 text-sm font-bold mb-2">
                  Case *
                </label>
                <select
                  value={formData.case_id}
                  onChange={(e) => setFormData({ ...formData, case_id: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                >
                  <option value="">Select a case</option>
                  {cases.map((c) => (
                    <option key={c._id} value={c._id}>
                      {c.case_number} - {c.title}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-gray-700 text-sm font-bold mb-2">
                  Evidence Type *
                </label>
                <select
                  value={formData.evidence_type}
                  onChange={(e) => setFormData({ ...formData, evidence_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="file">File</option>
                  <option value="disk_image">Disk Image</option>
                  <option value="memory_dump">Memory Dump</option>
                  <option value="network_capture">Network Capture</option>
                  <option value="log_file">Log File</option>
                  <option value="registry">Registry</option>
                  <option value="email">Email</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-gray-700 text-sm font-bold mb-2">
                File Name *
              </label>
              <input
                type="text"
                value={formData.file_name}
                onChange={(e) => setFormData({ ...formData, file_name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter file name"
                required
              />
            </div>

            <div className="mb-4">
              <label className="block text-gray-700 text-sm font-bold mb-2">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows="4"
                placeholder="Evidence description..."
              />
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={loading}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {loading ? 'Adding...' : 'Add Evidence'}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold">Evidence List</h2>
        </div>

        {loading && !showForm ? (
          <div className="p-8 text-center text-gray-500">Loading...</div>
        ) : evidence.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No evidence found</div>
        ) : (
          <div className="divide-y divide-gray-200">
            {evidence.map((item) => (
              <div key={item._id} className="p-4 hover:bg-gray-50">
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center space-x-3">
                    <span className="text-2xl">{getTypeIcon(item.evidence_type)}</span>
                    <div>
                      <h3 className="font-semibold text-gray-800">{item.file_name}</h3>
                      <p className="text-sm text-gray-600">Type: {item.evidence_type.replace('_', ' ')}</p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(item.status)}`}>
                    {item.status}
                  </span>
                </div>

                {item.description && (
                  <p className="text-gray-600 mb-2">{item.description}</p>
                )}

                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm text-gray-500">
                  <div>
                    <span className="font-medium">Size:</span> {formatFileSize(item.file_size)}
                  </div>
                  {item.hash_sha256 && (
                    <div className="col-span-2">
                      <span className="font-medium">SHA256:</span>
                      <span className="font-mono text-xs ml-1">{item.hash_sha256?.substring(0, 16)}...</span>
                    </div>
                  )}
                </div>

                <div className="text-sm text-gray-500 mt-2">
                  Collected: {item.collected_at && new Date(item.collected_at).toLocaleString()}
                </div>

                <div className="mt-4 flex space-x-2">
                  <button
                    onClick={() => handleAnalyzePartitions(item._id)}
                    className="bg-indigo-100 text-indigo-700 px-3 py-1 rounded text-sm hover:bg-indigo-200 transition-colors"
                  >
                    Analyze Partitions
                  </button>
                  <button
                    onClick={() => handleRecoverDeletedMetadata(item._id)}
                    className="bg-red-100 text-red-700 px-3 py-1 rounded text-sm hover:bg-red-200 transition-colors"
                  >
                    Recover Deleted Metadata
                  </button>
                  <button
                    onClick={() => handleDownloadReport(item._id, item.file_name)}
                    className="bg-green-100 text-green-700 px-3 py-1 rounded text-sm hover:bg-green-200 transition-colors flex items-center"
                  >
                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Download PDF
                  </button>
                </div>

                {activeAnalysis === item._id && analysisData && (
                  <div className="mt-4 p-4 border border-indigo-200 rounded-lg bg-indigo-50">
                    <div className="flex flex-col md:flex-row gap-4 mb-4">
                      <div className="flex-1">
                        <h4 className="font-semibold text-indigo-900 mb-2">
                          {analysisData.type === 'metadata' ? 'Recovered Deleted Metadata' : 'Analysis Results'}
                        </h4>
                        {analysisData.type === 'metadata' ? (
                          <div className="overflow-x-auto max-h-60 overflow-y-auto bg-white border border-gray-200 rounded">
                            <table className="min-w-full divide-y divide-gray-200 text-xs text-left">
                              <thead className="bg-gray-50">
                                <tr>
                                  <th className="px-2 py-1 font-medium text-gray-500">Inode</th>
                                  <th className="px-2 py-1 font-medium text-gray-500">Name</th>
                                  <th className="px-2 py-1 font-medium text-gray-500">Size</th>
                                  <th className="px-2 py-1 font-medium text-gray-500">Deleted At</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-gray-200">
                                {analysisData.metadata?.map((meta, idx) => (
                                  <tr key={idx} className="hover:bg-gray-50 text-red-600 font-mono">
                                    <td className="px-2 py-1">{meta.inode}</td>
                                    <td className="px-2 py-1">{meta.name}</td>
                                    <td className="px-2 py-1">{formatFileSize(parseInt(meta.size))}</td>
                                    <td className="px-2 py-1">{new Date(parseInt(meta.mtime) * 1000).toLocaleString()}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : (
                          <pre className="bg-gray-800 text-green-400 p-4 rounded text-xs overflow-x-auto max-h-60 overflow-y-auto">
                            {analysisData.raw || JSON.stringify(analysisData, null, 2)}
                          </pre>
                        )}
                      </div>

                      <div className="flex-1 flex flex-col h-64">
                        <h4 className="font-semibold text-indigo-900 mb-2">Forensic AI Chat</h4>
                        <div className="flex-1 bg-white border border-gray-300 rounded overflow-y-auto p-3 mb-2 flex flex-col shadow-inner">
                          {chatHistory.length === 0 ? (
                            <p className="text-gray-400 text-sm text-center my-auto">Consult the AI about findings, anomalies, or next steps.</p>
                          ) : (
                            chatHistory.map((msg, i) => (
                              <div key={i} className={`mb-2 p-2 rounded max-w-[85%] ${msg.role === 'user' ? 'bg-blue-600 text-white self-end' : 'bg-white border border-gray-200 text-gray-800 self-start shadow-sm'}`}>
                                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                              </div>
                            ))
                          )}
                          {isChatting && <div className="text-gray-500 text-xs mt-2 text-center animate-pulse">AI is analyzing...</div>}
                        </div>
                        <div className="flex space-x-2">
                          <input
                            type="text"
                            value={chatMessage}
                            onChange={(e) => setChatMessage(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleSendChatMessage()}
                            placeholder="Ask the assistant..."
                            className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          />
                          <button
                            onClick={handleSendChatMessage}
                            disabled={isChatting || !chatMessage.trim()}
                            className="bg-indigo-600 text-white px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                          >
                            Send
                          </button>
                        </div>
                      </div>
                    </div>

                    {analysisData.automated && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 border-t border-indigo-200 pt-4">
                        <div className="bg-white p-3 rounded-lg border border-gray-200 shadow-sm">
                          <h5 className="font-bold text-gray-800 text-sm mb-2 flex items-center">
                            <span className="mr-2">📂</span> AI File Classification
                          </h5>
                          <div className="text-xs max-h-40 overflow-y-auto">
                            {Array.isArray(analysisData.ai_classification) ? (
                              <ul className="space-y-1">
                                {analysisData.ai_classification.map((f, i) => (
                                  <li key={i} className="flex justify-between items-start border-b border-gray-50 pb-1">
                                    <span className="font-medium truncate mr-2">{f.name}</span>
                                    <span className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-bold ${f.classification === 'Malicious' ? 'bg-red-100 text-red-700' :
                                        f.classification === 'Suspicious' ? 'bg-orange-100 text-orange-700' :
                                          'bg-green-100 text-green-700'
                                      }`}>{f.classification}</span>
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p className="text-gray-600 break-words">{analysisData.ai_classification}</p>
                            )}
                          </div>
                        </div>

                        <div className="bg-white p-3 rounded-lg border border-gray-200 shadow-sm">
                          <h5 className="font-bold text-gray-800 text-sm mb-2 flex items-center">
                            <span className="mr-2">🔍</span> Behavior & Anomaly Detection
                          </h5>
                          <p className="text-xs text-gray-600 leading-relaxed overflow-y-auto max-h-40">
                            {analysisData.ai_anomalies}
                          </p>
                        </div>

                        <div className="col-span-full bg-slate-800 text-slate-100 p-4 rounded-lg shadow-inner overflow-hidden">
                          <h5 className="font-bold text-blue-400 text-sm mb-3 flex items-center">
                            <span className="mr-2">📝</span> Automated Forensic Report
                          </h5>
                          <div className="text-sm font-mono whitespace-pre-wrap max-h-80 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700">
                            {analysisData.ai_report}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Evidence;
