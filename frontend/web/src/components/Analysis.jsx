import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { analysisAPI, casesAPI } from '../api';

const Analysis = () => {
  const location = useLocation();
  const [analyses, setAnalyses] = useState([]);
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get('create') === 'true') {
      setShowForm(true);
    }
  }, [location]);
  const [activeTab, setActiveTab] = useState('results'); // 'results' | 'model'
  const [modelInfo, setModelInfo] = useState(null);
  const [modelLoading, setModelLoading] = useState(false);
  const [predictForm, setPredictForm] = useState({
    size_bytes: '',
    file_type: 'disk_image',
    entropy: '',
    partition: 'NTFS',
  });
  const [prediction, setPrediction] = useState(null);
  const [predicting, setPredicting] = useState(false);

  const [formData, setFormData] = useState({
    case_id: '',
    evidence_id: '',
    analysis_type: 'static',
    findings: {},
    severity: 'info'
  });

  useEffect(() => {
    fetchAnalyses();
    fetchCases();
  }, []);

  useEffect(() => {
    if (activeTab === 'model') {
      fetchModelInfo();
    }
  }, [activeTab]);

  const fetchAnalyses = async () => {
    setLoading(true);
    try {
      const response = await analysisAPI.getAnalyses();
      setAnalyses(response.data);
    } catch (err) {
      setError('Failed to load analyses');
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

  const fetchModelInfo = async () => {
    setModelLoading(true);
    try {
      const response = await analysisAPI.getModelInfo();
      setModelInfo(response.data);
    } catch (err) {
      console.error('Failed to fetch model info', err);
      setModelInfo(null);
    } finally {
      setModelLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await analysisAPI.createAnalysis(formData);
      setShowForm(false);
      setFormData({ case_id: '', evidence_id: '', analysis_type: 'static', findings: {}, severity: 'info' });
      fetchAnalyses();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create analysis');
    } finally {
      setLoading(false);
    }
  };

  const handlePredict = async (e) => {
    e.preventDefault();
    setPredicting(true);
    setPrediction(null);
    try {
      const response = await analysisAPI.predictRecoverability({
        size_bytes: parseInt(predictForm.size_bytes) || 1024,
        file_type: predictForm.file_type,
        entropy: parseFloat(predictForm.entropy) || 4.5,
        partition: predictForm.partition,
      });
      setPrediction(response.data);
    } catch (err) {
      setError('Prediction failed: ' + (err.response?.data?.error || err.message));
    } finally {
      setPredicting(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'in_progress': return 'bg-blue-100 text-blue-800';
      case 'completed': return 'bg-green-100 text-green-800';
      case 'failed': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'static': return '🔍';
      case 'dynamic': return '⚡';
      case 'memory': return '🧠';
      case 'network': return '🌐';
      case 'malware': return '🦠';
      case 'disk': return '💾';
      case 'log': return '📋';
      case 'ai': return '🤖';
      default: return '📊';
    }
  };

  const MetricCard = ({ label, value, color = 'indigo' }) => (
    <div className={`bg-${color}-50 border border-${color}-200 rounded-lg p-4 text-center`}>
      <div className={`text-2xl font-bold text-${color}-700`}>{value}</div>
      <div className={`text-xs text-${color}-500 mt-1 font-medium uppercase tracking-wide`}>{label}</div>
    </div>
  );

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-white">Analysis</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-blue-600 text-white px-4 py-2 rounded-xl hover:bg-blue-700 transition-all font-semibold hover:scale-[1.01]"
        >
          {showForm ? 'Cancel' : 'New Analysis'}
        </button>
      </div>

      {error && (
        <div className="bg-rose-950/20 border border-rose-500/30 text-rose-400 px-4 py-3 rounded-xl mb-4 text-xs font-mono flex justify-between items-center">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-300 font-bold ml-2">×</button>
        </div>
      )}

      {showForm && (
        <div className="bg-gray-800 border border-gray-700 rounded-xl shadow-xl p-6 mb-6">
          <h2 className="text-xl font-bold text-white mb-6">Create New Analysis</h2>
          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-gray-300 text-sm font-semibold mb-2">Case *</label>
                <select
                  value={formData.case_id}
                  onChange={(e) => setFormData({ ...formData, case_id: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-xl text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                  required
                >
                  <option value="">Select a case</option>
                  {cases.map((c) => (
                    <option key={c._id} value={c._id}>{c.case_number} - {c.title}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-gray-300 text-sm font-semibold mb-2">Evidence (Optional)</label>
                <input
                  type="text"
                  value={formData.evidence_id}
                  onChange={(e) => setFormData({ ...formData, evidence_id: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Evidence ID"
                />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div>
                <label className="block text-gray-300 text-sm font-semibold mb-2">Analysis Type *</label>
                <select
                  value={formData.analysis_type}
                  onChange={(e) => setFormData({ ...formData, analysis_type: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-xl text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="static">Static Analysis</option>
                  <option value="dynamic">Dynamic Analysis</option>
                  <option value="memory">Memory Analysis</option>
                  <option value="network">Network Analysis</option>
                  <option value="malware">Malware Analysis</option>
                  <option value="disk">Disk Analysis</option>
                  <option value="log">Log Analysis</option>
                  <option value="ai">AI Analysis</option>
                </select>
              </div>
              <div>
                <label className="block text-gray-300 text-sm font-semibold mb-2">Severity</label>
                <select
                  value={formData.severity}
                  onChange={(e) => setFormData({ ...formData, severity: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-xl text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="info">Info</option>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={loading}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-xl font-semibold transition-all hover:scale-[1.01] disabled:opacity-50"
              >
                {loading ? 'Creating...' : 'Start Analysis'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex border-b border-gray-700 mb-6">
        <button
          onClick={() => setActiveTab('results')}
          className={`px-4 py-2.5 -mb-px text-sm font-semibold border-b-2 transition-all ${
            activeTab === 'results'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-gray-400 hover:text-white hover:border-gray-700'
          }`}
        >
          📊 Analysis Results
        </button>
        <button
          onClick={() => setActiveTab('model')}
          className={`px-4 py-2.5 -mb-px text-sm font-semibold border-b-2 transition-all ${
            activeTab === 'model'
              ? 'border-purple-500 text-purple-400'
              : 'border-transparent text-gray-400 hover:text-white hover:border-gray-700'
          }`}
        >
          🤖 AI Model Intelligence
        </button>
      </div>

      {/* Analysis Results Tab */}
      {activeTab === 'results' && (
        <div className="bg-gray-800 border border-gray-700 rounded-xl shadow-xl overflow-hidden">
          <div className="p-4 border-b border-gray-700 bg-gray-900/30">
            <h2 className="text-xl font-bold text-white">Analysis Results</h2>
          </div>
          {loading && !showForm ? (
            <div className="p-8 text-center text-gray-400">Loading...</div>
          ) : analyses.length === 0 ? (
            <div className="p-8 text-center text-gray-400">No analyses found</div>
          ) : (
            <div className="divide-y divide-gray-700 bg-gray-850">
              {analyses.map((item) => (
                <div key={item._id} className="p-5 hover:bg-gray-700/20 transition-all">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center space-x-3">
                      <span className="text-2xl">{getTypeIcon(item.analysis_type)}</span>
                      <div>
                        <h3 className="font-bold text-white text-base">
                          {item.analysis_type?.replace('_', ' ')} Analysis
                        </h3>
                        {item.evidence_id && (
                          <p className="text-xs text-blue-400 font-mono mt-1">Evidence ID: {item.evidence_id}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {/* AI Prediction badge if available */}
                      {item.findings?.recoverable_label && (
                        <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                          item.findings.recoverable_label === 'recoverable'
                            ? 'bg-green-950/30 text-green-400 border border-green-500/20'
                            : 'bg-rose-950/30 text-rose-400 border border-rose-500/20'
                        }`}>
                          {item.findings.recoverable_label === 'recoverable' ? '✓ Recoverable' : '✗ Unrecoverable'}
                          {item.findings.confidence != null && ` ${Math.round(item.findings.confidence * 100)}%`}
                        </span>
                      )}
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(item.status)}`}>
                        {item.status}
                      </span>
                    </div>
                  </div>

                  {item.findings && Object.keys(item.findings).length > 0 && (
                    <div className="mt-3 p-3 bg-gray-900/50 border border-gray-700/60 rounded-xl text-sm text-gray-300">
                      <span className="font-semibold text-white">Findings:</span>
                      {/* Show anomalies if present */}
                      {item.findings.anomalies?.length > 0 && (
                        <div className="mt-1 space-y-1">
                          {item.findings.anomalies.map((a, idx) => (
                            <div key={idx} className="flex items-start gap-1 text-xs text-orange-400 bg-orange-950/20 border border-orange-500/20 px-2 py-1 rounded">
                              <span>⚠️</span> {a}
                            </div>
                          ))}
                        </div>
                      )}
                      {!item.findings.anomalies && (
                        <pre className="mt-1 text-xs overflow-x-auto">
                          {JSON.stringify(item.findings, null, 2)}
                        </pre>
                      )}
                    </div>
                  )}

                  <div className="text-xs text-gray-400 mt-4 font-mono">
                    Created: {item.analyzed_at && new Date(item.analyzed_at).toLocaleString()}
                    {item.completed_at && (
                      <span className="ml-4">Completed: {new Date(item.completed_at).toLocaleString()}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* AI Model Intelligence Tab */}
      {activeTab === 'model' && (
        <div className="space-y-6">
          {/* Model Metrics Card */}
          <div className="bg-gray-800 border border-gray-700 rounded-xl shadow-xl overflow-hidden">
            <div className="bg-gradient-to-r from-indigo-900 to-purple-900 p-5 border-b border-gray-700">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <span>🤖</span> Active ML Model — Random Forest Recoverability Classifier
              </h2>
              <p className="text-indigo-300 text-xs mt-1">
                Trained on forensic evidence features: file size, type, byte entropy, partition
              </p>
            </div>

            {modelLoading ? (
              <div className="p-8 text-center text-gray-400 animate-pulse">Loading model metadata...</div>
            ) : modelInfo ? (
              <div className="p-6">
                {modelInfo.status === 'no_model_loaded' ? (
                  <div className="text-center text-gray-400 py-8">
                    <p className="text-4xl mb-3">⚠️</p>
                    <p className="font-semibold">{modelInfo.message}</p>
                  </div>
                ) : (
                  <>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                      <div className="bg-indigo-950/20 border border-indigo-500/20 rounded-xl p-4 text-center">
                        <div className="text-2xl font-bold text-indigo-400 font-mono">{(modelInfo.accuracy * 100).toFixed(1)}%</div>
                        <div className="text-xs text-indigo-400/80 mt-1 font-semibold uppercase tracking-wide">Accuracy</div>
                      </div>
                      <div className="bg-emerald-950/20 border border-emerald-500/20 rounded-xl p-4 text-center">
                        <div className="text-2xl font-bold text-emerald-400 font-mono">{((modelInfo.precision || 0) * 100).toFixed(1)}%</div>
                        <div className="text-xs text-emerald-400/80 mt-1 font-semibold uppercase tracking-wide">Precision</div>
                      </div>
                      <div className="bg-sky-950/20 border border-sky-500/20 rounded-xl p-4 text-center">
                        <div className="text-2xl font-bold text-sky-400 font-mono">{((modelInfo.recall || 0) * 100).toFixed(1)}%</div>
                        <div className="text-xs text-sky-400/80 mt-1 font-semibold uppercase tracking-wide">Recall</div>
                      </div>
                      <div className="bg-purple-950/20 border border-purple-500/20 rounded-xl p-4 text-center">
                        <div className="text-2xl font-bold text-purple-400 font-mono">{((modelInfo.f1 || 0) * 100).toFixed(1)}%</div>
                        <div className="text-xs text-purple-400/80 mt-1 font-semibold uppercase tracking-wide">F1 Score</div>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-300">
                      <div className="bg-gray-900/40 border border-gray-700/60 rounded-xl p-4">
                        <p className="font-semibold text-gray-400 mb-2 uppercase text-xs tracking-wide font-mono">Model Details</p>
                        <p className="font-sans"><span className="font-medium text-gray-500">Name:</span> {modelInfo.model_name}</p>
                        <p className="font-sans"><span className="font-medium text-gray-500">Status:</span> <span className="text-green-400 font-bold">{modelInfo.status}</span></p>
                        <p className="font-sans"><span className="font-medium text-gray-500">Trained:</span> {modelInfo.trained_at ? new Date(modelInfo.trained_at).toLocaleString() : 'N/A'}</p>
                      </div>
                      <div className="bg-gray-900/40 border border-gray-700/60 rounded-xl p-4">
                        <p className="font-semibold text-gray-400 mb-2 uppercase text-xs tracking-wide font-mono">Features Used</p>
                        <div className="flex flex-wrap gap-2 mt-1">
                          {(modelInfo.features || []).map((f) => (
                            <span key={f} className="bg-indigo-950/40 text-indigo-400 border border-indigo-900/45 px-2 py-0.5 rounded text-xs font-mono font-medium">
                              {f}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <div className="p-6 text-center text-gray-400">
                <p>Could not load model information.</p>
                <button onClick={fetchModelInfo} className="mt-2 text-indigo-400 hover:underline text-sm font-semibold">Retry</button>
              </div>
            )}
          </div>

          {/* Recoverability Predictor */}
          <div className="bg-gray-800 border border-gray-700 rounded-xl shadow-xl overflow-hidden">
            <div className="p-4 border-b border-gray-700 bg-gray-900/30">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">🔬 Recoverability Predictor</h2>
              <p className="text-xs text-gray-400 mt-1">Enter evidence features to run a live ML prediction</p>
            </div>
            <div className="p-6">
              <form onSubmit={handlePredict} className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">File Size (bytes)</label>
                  <input
                    type="number"
                    value={predictForm.size_bytes}
                    onChange={(e) => setPredictForm({ ...predictForm, size_bytes: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="e.g. 31460635443"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Byte Entropy (0.0 – 8.0)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="8"
                    value={predictForm.entropy}
                    onChange={(e) => setPredictForm({ ...predictForm, entropy: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="e.g. 4.5"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">File / Evidence Type</label>
                  <select
                    value={predictForm.file_type}
                    onChange={(e) => setPredictForm({ ...predictForm, file_type: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-xl text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="file">File</option>
                    <option value="disk_image">Disk Image</option>
                    <option value="memory_dump">Memory Dump</option>
                    <option value="network_capture">Network Capture</option>
                    <option value="log_file">Log File</option>
                    <option value="registry">Registry</option>
                    <option value="email">Email</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Partition / Filesystem</label>
                  <select
                    value={predictForm.partition}
                    onChange={(e) => setPredictForm({ ...predictForm, partition: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-xl text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="NTFS">NTFS</option>
                    <option value="FAT32">FAT32</option>
                    <option value="EXT4">EXT4</option>
                    <option value="APFS">APFS</option>
                    <option value="exFAT">exFAT</option>
                  </select>
                </div>
                <div className="md:col-span-2">
                  <button
                    type="submit"
                    disabled={predicting}
                    className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-2.5 rounded-xl font-semibold transition-colors disabled:opacity-50"
                  >
                    {predicting ? '⚡ Running ML Prediction...' : '⚡ Predict Recoverability'}
                  </button>
                </div>
              </form>

              {prediction && (
                <div className={`rounded-xl p-5 border ${
                  prediction.prediction === 1
                    ? 'bg-green-950/20 border-green-500/30'
                    : 'bg-rose-950/20 border-rose-500/30'
                }`}>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <span className="text-3xl">{prediction.prediction === 1 ? '✅' : '❌'}</span>
                      <div>
                        <p className={`text-xl font-bold ${prediction.prediction === 1 ? 'text-green-400' : 'text-rose-400'}`}>
                          {prediction.prediction === 1 ? 'RECOVERABLE' : 'UNRECOVERABLE'}
                        </p>
                        <p className="text-xs text-gray-400">ML Classification Result</p>
                      </div>
                    </div>
                    <div className={`text-center rounded-xl px-4 py-2 border ${
                      prediction.prediction === 1 ? 'bg-green-950/40 text-green-400 border-green-500/20' : 'bg-rose-950/40 text-rose-400 border-rose-500/20'
                    }`}>
                      <p className="text-2xl font-black font-mono">{prediction.confidence}%</p>
                      <p className="text-[10px] font-semibold uppercase tracking-wider">Confidence</p>
                    </div>
                  </div>
                  {prediction.anomalies?.length > 0 && (
                    <div className="mt-3">
                      <p className="text-sm font-semibold text-orange-400 mb-2">⚠️ Anomalies Detected:</p>
                      {prediction.anomalies.map((a, idx) => (
                        <div key={idx} className="text-xs text-orange-400 bg-orange-950/20 border border-orange-500/20 px-3 py-1 rounded mb-1">
                          {a}
                        </div>
                      ))}
                    </div>
                  )}
                  {prediction.anomalies?.length === 0 && (
                    <p className="text-xs text-green-400 mt-2">✓ No anomalies detected in the feature set.</p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Analysis;
