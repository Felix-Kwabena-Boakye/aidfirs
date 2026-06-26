import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { authAPI, aiSettingsAPI, analysisAPI } from '../api';

const Settings = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState(() => {
    const userData = localStorage.getItem('user');
    return userData ? JSON.parse(userData) : null;
  });

  // Check authentication on mount
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      navigate('/');
      return;
    }
    // Also check if user data exists
    const userData = localStorage.getItem('user');
    if (!userData) {
      navigate('/');
      return;
    }
    setUser(JSON.parse(userData));
  }, [navigate]);

  const [activeTab, setActiveTab] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('tab') || 'profile';
  });

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const tab = params.get('tab');
    if (tab && tab !== activeTab) {
      setActiveTab(tab);
    }
  }, [location]);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [profileData, setProfileData] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    email: user?.email || ''
  });

  // Security (Change Password) state
  const [passwords, setPasswords] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [updatingPassword, setUpdatingPassword] = useState(false);

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setSuccessMessage('');
    setErrorMessage('');

    if (passwords.new_password !== passwords.confirm_password) {
      setErrorMessage('New password and confirmation do not match.');
      return;
    }

    if (passwords.new_password.length < 6) {
      setErrorMessage('New password must be at least 6 characters.');
      return;
    }

    setUpdatingPassword(true);
    try {
      const response = await authAPI.changePassword({
        current_password: passwords.current_password,
        new_password: passwords.new_password,
        confirm_password: passwords.confirm_password
      });
      setSuccessMessage(response.data.message || 'Password updated successfully!');
      setPasswords({
        current_password: '',
        new_password: '',
        confirm_password: ''
      });
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'Failed to update password.';
      setErrorMessage(msg);
    } finally {
      setUpdatingPassword(false);
    }
  };

  // AI Settings state
  const [aiSettings, setAiSettings] = useState({
    claude_enabled: false,
    claude_model: 'claude-3-haiku-20240307',
    claude_configured: false
  });
  const [apiKey, setApiKey] = useState('');
  const [loadingAI, setLoadingAI] = useState(false);

  // AI Oracle Training state
  const [modelInfo, setModelInfo] = useState(null);
  const [loadingModel, setLoadingModel] = useState(false);
  const [trainingInProgress, setTrainingInProgress] = useState(false);
  const [trainingResult, setTrainingResult] = useState(null);

  useEffect(() => {
    if (activeTab === 'ai') {
      loadAISettings();
    }
    if (activeTab === 'oracle') {
      loadModelInfo();
    }
  }, [activeTab]);

  const loadAISettings = async () => {
    setLoadingAI(true);
    try {
      const response = await aiSettingsAPI.getSettings();
      setAiSettings(response.data);
    } catch (err) {
      console.error('Failed to load AI settings:', err);
    } finally {
      setLoadingAI(false);
    }
  };

  const loadModelInfo = async () => {
    setLoadingModel(true);
    try {
      const response = await analysisAPI.getModelInfo();
      setModelInfo(response.data);
    } catch (err) {
      console.error('Failed to load model info:', err);
      setModelInfo(null);
    } finally {
      setLoadingModel(false);
    }
  };

  const handleTrainModel = async () => {
    setTrainingInProgress(true);
    setTrainingResult(null);
    setSuccessMessage('');
    setErrorMessage('');
    try {
      const response = await analysisAPI.trainModel();
      setTrainingResult(response.data);
      if (response.data.success) {
        setSuccessMessage('AI Oracle model trained successfully!');
        // Reload model info to show updated metrics
        loadModelInfo();
      } else {
        setErrorMessage(response.data.error || 'Training failed.');
      }
    } catch (err) {
      const status = err.response?.status;
      if (status === 401) {
        setErrorMessage('Your session has expired. Please log out and log back in, then try again.');
      } else if (status === 403) {
        setErrorMessage('Permission denied: Only Admins and Investigators can train the AI Oracle.');
      } else {
        const msg = err.response?.data?.error || err.message || 'Failed to train model.';
        setErrorMessage(msg);
      }
    } finally {
      setTrainingInProgress(false);
    }
  };


  const handleProfileUpdate = async (e) => {
    e.preventDefault();
    setSuccessMessage('');
    setErrorMessage('');

    try {
      setSuccessMessage('Profile updated successfully');
    } catch (err) {
      setErrorMessage('Failed to update profile');
    }
  };

  const handleAIUpdate = async (e) => {
    e.preventDefault();
    setSuccessMessage('');
    setErrorMessage('');

    try {
      const payload = {
        claude_enabled: aiSettings.claude_enabled,
        claude_model: aiSettings.claude_model
      };
      if (apiKey) {
        payload.api_key = apiKey;
      }

      const response = await aiSettingsAPI.updateSettings(payload);
      setSuccessMessage('AI settings updated successfully');
      if (response.data) {
        setAiSettings(response.data);
      }
      setApiKey(''); // Clear the input field for security
    } catch (err) {
      setErrorMessage('Failed to update AI settings');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    window.location.href = '/';
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-white mb-6">Settings</h1>

      {successMessage && (
        <div className="bg-emerald-950/20 border border-emerald-500/30 text-emerald-400 px-4 py-3 rounded-xl mb-4 text-xs font-mono">
          {successMessage}
        </div>
      )}

      {errorMessage && (
        <div className="bg-rose-950/20 border border-rose-500/30 text-rose-400 px-4 py-3 rounded-xl mb-4 text-xs font-mono">
          {errorMessage}
        </div>
      )}

      <div className="bg-gray-800 border border-gray-700 rounded-xl shadow-xl overflow-hidden">
        {/* Tabs */}
        <div className="border-b border-gray-700">
          <nav className="flex space-x-4 px-4" aria-label="Tabs">
            <button
              onClick={() => setActiveTab('profile')}
              className={`py-4 px-2 border-b-2 font-semibold text-sm transition-all ${activeTab === 'profile'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-white hover:border-gray-700'
                }`}
            >
              Profile
            </button>
            {user?.role === 'admin' && (
              <button
                onClick={() => setActiveTab('ai')}
                className={`py-4 px-2 border-b-2 font-semibold text-sm transition-all ${activeTab === 'ai'
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-gray-400 hover:text-white hover:border-gray-700'
                  }`}
              >
                AI Settings
              </button>
            )}
            <button
              onClick={() => setActiveTab('notifications')}
              className={`py-4 px-2 border-b-2 font-semibold text-sm transition-all ${activeTab === 'notifications'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-white hover:border-gray-700'
                }`}
            >
              Notifications
            </button>
            {user?.role === 'admin' && (
              <button
                onClick={() => setActiveTab('oracle')}
                className={`py-4 px-2 border-b-2 font-semibold text-sm transition-all ${activeTab === 'oracle'
                  ? 'border-purple-500 text-purple-400'
                  : 'border-transparent text-gray-400 hover:text-white hover:border-gray-700'
                  }`}
              >
                🧠 AI Oracle
              </button>
            )}
            <button
              onClick={() => setActiveTab('security')}
              className={`py-4 px-2 border-b-2 font-semibold text-sm transition-all ${activeTab === 'security'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-white hover:border-gray-700'
                }`}
            >
              Security
            </button>
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'profile' && (
            <form onSubmit={handleProfileUpdate}>
              <div className="space-y-4">
                <div>
                  <label className="block text-gray-300 text-sm font-semibold mb-2">
                    Username
                  </label>
                  <input
                    type="text"
                    value={user?.username || ''}
                    disabled
                    className="w-full px-3 py-2 border border-gray-800 rounded-xl bg-gray-900/50 text-gray-500 cursor-not-allowed font-mono text-sm"
                  />
                  <p className="text-xs text-gray-500 mt-1.5">Username cannot be changed</p>
                </div>

                <div>
                  <label className="block text-gray-300 text-sm font-semibold mb-2">
                    First Name
                  </label>
                  <input
                    type="text"
                    value={profileData.first_name}
                    onChange={(e) => setProfileData({ ...profileData, first_name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-700 rounded-xl bg-gray-900 text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-gray-300 text-sm font-semibold mb-2">
                    Last Name
                  </label>
                  <input
                    type="text"
                    value={profileData.last_name}
                    onChange={(e) => setProfileData({ ...profileData, last_name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-700 rounded-xl bg-gray-900 text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-gray-300 text-sm font-semibold mb-2">
                    Email
                  </label>
                  <input
                    type="email"
                    value={profileData.email}
                    onChange={(e) => setProfileData({ ...profileData, email: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-700 rounded-xl bg-gray-900 text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-gray-300 text-sm font-semibold mb-2">
                    Role
                  </label>
                  <input
                    type="text"
                    value={user?.role || ''}
                    disabled
                    className="w-full px-3 py-2 border border-gray-800 rounded-xl bg-gray-900/50 text-gray-500 cursor-not-allowed capitalize font-mono text-sm"
                  />
                </div>

                <div className="pt-4">
                  <button
                    type="submit"
                    className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-xl font-semibold transition-all hover:scale-[1.01]"
                  >
                    Save Changes
                  </button>
                </div>
              </div>
            </form>
          )}

          {activeTab === 'ai' && user?.role === 'admin' && (
            <form onSubmit={handleAIUpdate}>
              <div className="space-y-6">
                <div className="bg-blue-950/20 border-l-4 border-blue-500 p-4 rounded-r-xl">
                  <div className="flex">
                    <div className="ml-3">
                      <p className="text-xs text-blue-400 leading-relaxed">
                        Configure AI-powered analysis using Claude API. Enhanced features include intelligent summarization,
                        advanced indicator extraction, and risk assessment.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between py-3.5 border-b border-gray-700">
                  <div>
                    <h3 className="font-semibold text-white text-sm">Claude API Integration</h3>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {aiSettings.claude_configured
                        ? 'API key is configured. Enable to use AI features.'
                        : 'API key not configured. Enter your API key below.'}
                    </p>
                  </div>
                  <div className={`px-3 py-1 rounded-full text-xs font-semibold border ${aiSettings.claude_configured
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                    : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                    }`}>
                    {aiSettings.claude_configured ? 'Configured' : 'Not Configured'}
                  </div>
                </div>

                <div className="flex items-center justify-between py-3.5 border-b border-gray-700">
                  <div>
                    <h3 className="font-semibold text-white text-sm">Enable AI Analysis</h3>
                    <p className="text-xs text-gray-400 mt-0.5">Use Claude API for enhanced forensic analysis</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      checked={aiSettings.claude_enabled}
                      onChange={(e) => setAiSettings({ ...aiSettings, claude_enabled: e.target.checked })}
                      disabled={!aiSettings.claude_configured}
                    />
                    <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600 disabled:opacity-50"></div>
                  </label>
                </div>

                <div>
                  <label className="block text-gray-300 text-sm font-semibold mb-2">
                    Anthropic API Key
                  </label>
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder={aiSettings.claude_configured ? "******** (Update existing key)" : "sk-ant-..."}
                    className="w-full px-3 py-2 border border-gray-700 rounded-xl bg-gray-900 text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <p className="text-xs text-gray-400 mt-1.5">Leave blank to keep existing key.</p>
                </div>

                <div>
                  <label className="block text-gray-300 text-sm font-semibold mb-2">
                    Claude Model
                  </label>
                  <select
                    value={aiSettings.claude_model}
                    onChange={(e) => setAiSettings({ ...aiSettings, claude_model: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-700 rounded-xl bg-gray-900 text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                    disabled={!aiSettings.claude_configured}
                  >
                    <option value="claude-3-haiku-20240307">Claude 3 Haiku (Fast)</option>
                    <option value="claude-3-sonnet-20240229">Claude 3 Sonnet (Balanced)</option>
                    <option value="claude-3-opus-20240229">Claude 3 Opus (Powerful)</option>
                  </select>
                </div>

                <div className="pt-4">
                  <button
                    type="submit"
                    className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-xl font-semibold transition-all disabled:opacity-50"
                    disabled={loadingAI}
                  >
                    {loadingAI ? 'Loading...' : 'Save AI Settings'}
                  </button>
                </div>
              </div>
            </form>
          )}

          {activeTab === 'notifications' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between py-3.5 border-b border-gray-700">
                <div>
                  <h3 className="font-semibold text-white text-sm">Email Notifications</h3>
                  <p className="text-xs text-gray-400 mt-0.5">Receive email notifications for case updates</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" defaultChecked />
                  <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>

              <div className="flex items-center justify-between py-3.5 border-b border-gray-700">
                <div>
                  <h3 className="font-semibold text-white text-sm">Case Alerts</h3>
                  <p className="text-xs text-gray-400 mt-0.5">Get notified when cases are assigned or updated</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" defaultChecked />
                  <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>

              <div className="flex items-center justify-between py-3.5 border-b border-gray-700">
                <div>
                  <h3 className="font-semibold text-white text-sm">SMS Notifications</h3>
                  <p className="text-xs text-gray-400 mt-0.5">Receive SMS for critical alerts</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" />
                  <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>
            </div>
          )}

          {activeTab === 'oracle' && user?.role === 'admin' && (
            <div className="space-y-6">
              {/* Header */}
              <div className="bg-gradient-to-r from-purple-950/20 to-indigo-950/20 border-l-4 border-purple-500 p-5 rounded-r-xl">
                <h2 className="text-sm font-bold text-purple-400 flex items-center gap-2 uppercase tracking-wider font-mono">
                  🧠 AI Oracle — Forensic Intelligence Engine
                </h2>
                <p className="text-xs text-purple-300/80 leading-relaxed mt-1.5 font-sans">
                  The AI Oracle is the brain behind file recoverability predictions. It learns from your
                  forensic data — file types, sizes, entropy, and partitions — to predict which deleted
                  files can be recovered <strong>before</strong> you spend time trying.
                </p>
              </div>

              {/* How It Works — Layman Section */}
              <div className="bg-gray-900/40 border border-gray-700/60 rounded-xl p-5">
                <h3 className="font-bold text-white text-sm mb-4 flex items-center gap-2 font-mono uppercase tracking-wider">
                  📖 How Does the AI Oracle Work?
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="flex items-start gap-3 p-3.5 bg-gray-900/60 border border-gray-800/80 rounded-xl">
                    <span className="text-xl">📂</span>
                    <div>
                      <strong className="text-gray-200 block mb-0.5">File Size</strong>
                      <p className="text-gray-400 leading-relaxed">Larger files are harder to recover because they fragment across the disk. The AI weighs file size when predicting success.</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 p-3.5 bg-gray-900/60 border border-gray-800/80 rounded-xl">
                    <span className="text-xl">🏷️</span>
                    <div>
                      <strong className="text-gray-200 block mb-0.5">File Type</strong>
                      <p className="text-gray-400 leading-relaxed">JPEGs and PDFs have distinct headers that act like fingerprints. Log files and registry exports are almost always recoverable.</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 p-3.5 bg-gray-900/60 border border-gray-800/80 rounded-xl">
                    <span className="text-xl">💾</span>
                    <div>
                      <strong className="text-gray-200 block mb-0.5">File System (Partition)</strong>
                      <p className="text-gray-400 leading-relaxed">NTFS preserves more metadata than FAT32, so recovery on NTFS partitions is generally more successful.</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 p-3.5 bg-gray-900/60 border border-gray-800/80 rounded-xl">
                    <span className="text-xl">🔐</span>
                    <div>
                      <strong className="text-gray-200 block mb-0.5">Entropy (Complexity)</strong>
                      <p className="text-gray-400 leading-relaxed">Entropy measures randomness. Files with entropy above ~7.1 are likely encrypted or compressed, making recovery harder.</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Current Model Metrics */}
              <div className="bg-gray-900/40 border border-gray-700/60 rounded-xl p-5">
                <h3 className="font-bold text-white text-sm mb-4 flex items-center gap-2 font-mono uppercase tracking-wider">
                  📊 Current Model Performance
                </h3>

                {loadingModel ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-500"></div>
                    <span className="ml-3 text-gray-400 font-mono text-xs">Syncing engine metrics...</span>
                  </div>
                ) : modelInfo && modelInfo.status !== 'no_model_loaded' ? (
                  <div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
                      <div className="bg-green-500/5 border border-green-500/20 rounded-xl p-4 text-center">
                        <div className="text-xl font-bold text-green-400 font-mono">
                          {modelInfo.accuracy != null ? `${(modelInfo.accuracy * 100).toFixed(1)}%` : '—'}
                        </div>
                        <div className="text-[10px] text-green-500/80 font-bold uppercase tracking-wider mt-1 font-mono">Accuracy</div>
                        <div className="text-[10px] text-gray-500 mt-0.5">Overall correctness</div>
                      </div>
                      <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl p-4 text-center">
                        <div className="text-xl font-bold text-blue-400 font-mono">
                          {modelInfo.precision != null ? `${(modelInfo.precision * 100).toFixed(1)}%` : '—'}
                        </div>
                        <div className="text-[10px] text-blue-500/80 font-bold uppercase tracking-wider mt-1 font-mono">Precision</div>
                        <div className="text-[10px] text-gray-500 mt-0.5">True Positive rate</div>
                      </div>
                      <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4 text-center">
                        <div className="text-xl font-bold text-amber-400 font-mono">
                          {modelInfo.recall != null ? `${(modelInfo.recall * 100).toFixed(1)}%` : '—'}
                        </div>
                        <div className="text-[10px] text-amber-500/80 font-bold uppercase tracking-wider mt-1 font-mono">Recall</div>
                        <div className="text-[10px] text-gray-500 mt-0.5">Sensitivity rate</div>
                      </div>
                      <div className="bg-purple-500/5 border border-purple-500/20 rounded-xl p-4 text-center">
                        <div className="text-xl font-bold text-purple-400 font-mono">
                          {modelInfo.f1 != null ? `${(modelInfo.f1 * 100).toFixed(1)}%` : '—'}
                        </div>
                        <div className="text-[10px] text-purple-500/80 font-bold uppercase tracking-wider mt-1 font-mono">F1 Score</div>
                        <div className="text-[10px] text-gray-500 mt-0.5">Balanced metric</div>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-4 text-xs text-gray-400 border-t border-gray-700/60 pt-3 font-mono">
                      <div>
                        <span className="font-semibold text-gray-500">MODEL:</span>{' '}
                        <span className="bg-gray-950 px-2 py-0.5 rounded text-cyan-400 border border-gray-800 text-[10px]">
                          {modelInfo.model_name || 'Unknown'}
                        </span>
                      </div>
                      <div>
                        <span className="font-semibold text-gray-500">STATUS:</span>{' '}
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          modelInfo.status === 'active' ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20'
                        }`}>
                          {modelInfo.status}
                        </span>
                      </div>
                      {modelInfo.trained_at && (
                        <div>
                          <span className="font-semibold text-gray-500">SYNCD:</span>{' '}
                          {new Date(modelInfo.trained_at).toLocaleString()}
                        </div>
                      )}
                    </div>

                    {modelInfo.features && modelInfo.features.length > 0 && (
                      <div className="mt-4 flex items-center gap-2 border-t border-gray-700/60 pt-3">
                        <span className="font-semibold text-gray-500 text-[10px] uppercase font-mono">FEATURES:</span>
                        <div className="flex flex-wrap gap-1.5">
                          {modelInfo.features.map((f, i) => (
                            <span key={i} className="bg-indigo-500/5 text-indigo-400 text-[10px] font-mono px-2 py-0.5 rounded-full border border-indigo-500/20">
                              {f}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8 font-mono">
                    <div className="text-3xl mb-2">🤖</div>
                    <p className="text-gray-300 font-medium text-xs">No trained model available</p>
                    <p className="text-[11px] text-gray-500 mt-1">
                      Click "Train AI Oracle" below to create the first model from your forensic data.
                    </p>
                  </div>
                )}
              </div>

              {/* Training Result (after training) */}
              {trainingResult && trainingResult.success && (
                <div className="bg-green-500/5 border border-green-500/30 rounded-xl p-5">
                  <h3 className="font-bold text-green-400 mb-2 flex items-center gap-2 font-mono uppercase tracking-wider text-xs">
                    ✅ Training Complete!
                  </h3>
                  {trainingResult.explanations && trainingResult.explanations.length > 0 && (
                    <div className="space-y-2">
                      {trainingResult.explanations.map((explanation, i) => (
                        <p key={i} className="text-xs text-green-300 leading-relaxed bg-green-950/20 p-3 rounded-lg border border-green-950/50">
                          {explanation}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Train Button */}
              <div className="bg-gray-900/30 border border-gray-700/60 rounded-xl p-5 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-gray-200 text-sm">Re-train the AI Oracle</h3>
                  <p className="text-xs text-gray-400 mt-1">
                    Export the latest forensic data and retrain the model. This may take a moment.
                  </p>
                </div>
                <button
                  onClick={handleTrainModel}
                  disabled={trainingInProgress}
                  className={`px-5 py-2.5 rounded-xl font-semibold text-xs text-white transition-all duration-200 flex items-center gap-2 ${
                    trainingInProgress
                      ? 'bg-gray-700 text-gray-500 cursor-not-allowed border border-gray-600'
                      : 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 shadow-md hover:shadow-lg'
                  }`}
                >
                  {trainingInProgress ? (
                    <>
                      <div className="animate-spin rounded-full h-3 w-3 border-2 border-white border-t-transparent"></div>
                      Training...
                    </>
                  ) : (
                    <>
                      🚀 Train AI Oracle
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold text-white text-sm mb-4 uppercase tracking-wider font-mono">Change Password</h3>
                <form onSubmit={handleChangePassword} className="space-y-4">
                  <div>
                    <label className="block text-gray-300 text-sm font-semibold mb-2">
                      Current Password
                    </label>
                    <input
                      type="password"
                      value={passwords.current_password}
                      onChange={(e) => setPasswords({ ...passwords, current_password: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-700 rounded-xl bg-gray-900 text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Enter current password"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-gray-300 text-sm font-semibold mb-2">
                      New Password
                    </label>
                    <input
                      type="password"
                      value={passwords.new_password}
                      onChange={(e) => setPasswords({ ...passwords, new_password: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-700 rounded-xl bg-gray-900 text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Enter new password (min. 6 characters)"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-gray-300 text-sm font-semibold mb-2">
                      Confirm New Password
                    </label>
                    <input
                      type="password"
                      value={passwords.confirm_password}
                      onChange={(e) => setPasswords({ ...passwords, confirm_password: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-700 rounded-xl bg-gray-900 text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Confirm new password"
                      required
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={updatingPassword}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-xl font-semibold transition-all hover:scale-[1.01] disabled:opacity-50"
                  >
                    {updatingPassword ? 'Updating...' : 'Update Password'}
                  </button>
                </form>
              </div>

              <div className="pt-6 border-t border-gray-700">
                <h3 className="font-semibold text-white text-sm mb-4 uppercase tracking-wider font-mono">Session Management</h3>
                <button
                  onClick={handleLogout}
                  className="bg-red-600 hover:bg-red-700 text-white px-6 py-2.5 rounded-xl font-semibold transition-all hover:scale-[1.01]"
                >
                  Sign Out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Settings;
