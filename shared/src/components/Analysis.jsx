import React, { useState, useEffect } from 'react';
import { analysisAPI, casesAPI } from '../api';

const Analysis = () => {
  const [analyses, setAnalyses] = useState([]);
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await analysisAPI.createAnalysis(formData);
      setShowForm(false);
      setFormData({
        case_id: '',
        evidence_id: '',
        analysis_type: 'static',
        findings: {},
        severity: 'info'
      });
      fetchAnalyses();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create analysis');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'in_progress':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'static':
        return '🔍';
      case 'dynamic':
        return '⚡';
      case 'memory':
        return '🧠';
      case 'network':
        return '🌐';
      case 'malware':
        return '🦠';
      case 'disk':
        return '💾';
      case 'log':
        return '📋';
      case 'ai':
        return '🤖';
      default:
        return '📊';
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Analysis</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          {showForm ? 'Cancel' : 'New Analysis'}
        </button>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {showForm && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Create New Analysis</h2>
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
                  Evidence (Optional)
                </label>
                <input
                  type="text"
                  value={formData.evidence_id}
                  onChange={(e) => setFormData({ ...formData, evidence_id: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Evidence ID"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-gray-700 text-sm font-bold mb-2">
                  Analysis Type *
                </label>
                <select
                  value={formData.analysis_type}
                  onChange={(e) => setFormData({ ...formData, analysis_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                <label className="block text-gray-700 text-sm font-bold mb-2">
                  Severity
                </label>
                <select
                  value={formData.severity}
                  onChange={(e) => setFormData({ ...formData, severity: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {loading ? 'Creating...' : 'Start Analysis'}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold">Analysis Results</h2>
        </div>

        {loading && !showForm ? (
          <div className="p-8 text-center text-gray-500">Loading...</div>
        ) : analyses.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No analyses found</div>
        ) : (
          <div className="divide-y divide-gray-200">
            {analyses.map((item) => (
              <div key={item._id} className="p-4 hover:bg-gray-50">
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center space-x-3">
                    <span className="text-2xl">{getTypeIcon(item.analysis_type)}</span>
                    <div>
                      <h3 className="font-semibold text-gray-800">
                        {item.analysis_type?.replace('_', ' ')} Analysis
                      </h3>
                      {item.evidence_id && (
                        <p className="text-sm text-gray-600">Evidence ID: {item.evidence_id}</p>
                      )}
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(item.status)}`}>
                    {item.status}
                  </span>
                </div>
                
                {item.findings && Object.keys(item.findings).length > 0 && (
                  <div className="mt-2 p-3 bg-gray-50 rounded text-sm">
                    <span className="font-medium">Findings:</span>
                    <pre className="mt-1 text-xs overflow-x-auto">
                      {JSON.stringify(item.findings, null, 2)}
                    </pre>
                  </div>
                )}
                
                <div className="text-sm text-gray-500 mt-2">
                  Created: {item.created_at && new Date(item.created_at).toLocaleString()}
                  {item.completed_at && (
                    <span className="ml-4">Completed: {new Date(item.completed_at).toLocaleString()}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Analysis;
