import React, { useState, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell
} from "recharts";
import {
  AlertTriangle, FileText, FolderOpen, TrendingUp, BarChart3, ChevronDown, ChevronUp,
  Bot, Send, Lightbulb, Search, FileSearch, Activity, MessageSquare
} from "lucide-react";
import { casesAPI, evidenceAPI, analysisAPI } from "../api";

export default function Dashboard() {
  const [cases, setCases] = useState([]);
  const [evidence, setEvidence] = useState([]);
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isVisible, setIsVisible] = useState(false);
  const [openDropdown, setOpenDropdown] = useState(null);

  // AI Helper state
  const [aiMessage, setAiMessage] = useState('');
  const [aiSuggestions, setAiSuggestions] = useState([]);
  const [showAiPanel, setShowAiPanel] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [casesRes, evidenceRes, analysesRes] = await Promise.all([
          casesAPI.getCases(),
          evidenceAPI.getEvidence(),
          analysisAPI.getAnalyses()
        ]);
        setCases(casesRes.data);
        setEvidence(evidenceRes.data);
        setAnalyses(analysesRes.data);

        // Generate AI suggestions based on data
        generateAISuggestions(casesRes.data, evidenceRes.data, analysesRes.data);
      } catch (err) {
        toast.error('Failed to load dashboard data: ' + (err.response?.data?.error || err.message));
        if (err.response?.status === 401 || err.response?.status === 403) {
          toast.error('Session expired. Please login again.');
          setTimeout(() => window.location.href = '/', 2000);
        }
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Generate AI suggestions for investigators
  const generateAISuggestions = (casesData, evidenceData, analysesData) => {
    const suggestions = [];

    if (casesData.length === 0) {
      suggestions.push({
        icon: FolderOpen,
        title: 'Create Your First Case',
        description: 'Start by creating a new case to begin your forensic investigation.',
        action: 'Create Case',
        priority: 'high'
      });
    }

    if (evidenceData.length === 0 && casesData.length > 0) {
      suggestions.push({
        icon: FileSearch,
        title: 'Upload Evidence',
        description: 'Add evidence files to your case for analysis.',
        action: 'Upload Evidence',
        priority: 'high'
      });
    }

    if (casesData.length > 0 && evidenceData.length > 0) {
      suggestions.push({
        icon: Activity,
        title: 'Run AI Analysis',
        description: 'Analyze uploaded evidence using AI to detect anomalies and patterns.',
        action: 'Run Analysis',
        priority: 'medium'
      });
    }

    if (analysesData.filter(a => a.status === 'pending').length > 0) {
      suggestions.push({
        icon: Search,
        title: 'Review Pending Analysis',
        description: 'You have pending analysis results waiting for review.',
        action: 'View Results',
        priority: 'medium'
      });
    }

    // Always add general tips
    suggestions.push({
      icon: Lightbulb,
      title: 'Best Practices',
      description: 'Always maintain chain of custody and document all findings.',
      action: 'Learn More',
      priority: 'low'
    });

    setAiSuggestions(suggestions);
  };

  const handleAiSubmit = (e) => {
    e.preventDefault();
    if (!aiMessage.trim()) return;

    // Simple AI response simulation
    const lowerMsg = aiMessage.toLowerCase();
    let response = "I'm here to help with your investigation. Here are some suggestions:";

    if (lowerMsg.includes('case') || lowerMsg.includes('create')) {
      response = "To create a new case, click on 'Cases' in the sidebar, then click 'Create New Case'. Fill in the case details like number, title, and description.";
    } else if (lowerMsg.includes('evidence') || lowerMsg.includes('upload')) {
      response = "To upload evidence, go to 'Evidence' section. You can upload documents, images, videos, or log files for analysis.";
    } else if (lowerMsg.includes('analyze') || lowerMsg.includes('analysis')) {
      response = "AI Analysis helps detect anomalies in your evidence. Upload evidence first, then run analysis from the Analysis section.";
    } else if (lowerMsg.includes('report')) {
      response = "Generate reports from the Reports section. You can export case summaries, evidence lists, and analysis results.";
    } else if (lowerMsg.includes('help') || lowerMsg.includes('what')) {
      response = "I can help you with: Creating cases, uploading evidence, running AI analysis, generating reports, and more. Just ask!";
    }

    setAiSuggestions([{
      icon: Bot,
      title: 'AI Assistant',
      description: response,
      action: 'Got it',
      priority: 'low'
    }, ...aiSuggestions]);
    setAiMessage('');
  };

  const stats = [
    { name: "Active Cases", value: cases.length.toString(), icon: FolderOpen, color: "text-blue-400" },
    { name: "Evidence Uploaded", value: evidence.length.toString(), icon: FileText, color: "text-green-400" },
    { name: "Pending Analysis", value: analyses.filter(a => a.status === 'pending').length.toString(), icon: TrendingUp, color: "text-yellow-400" },
    { name: "Critical Alerts", value: "0", icon: AlertTriangle, color: "text-red-400" },
  ];

  const caseData = [
    { name: "Jan", cases: cases.filter(c => new Date(c.created_at).getMonth() === 0).length },
    { name: "Feb", cases: cases.filter(c => new Date(c.created_at).getMonth() === 1).length },
    { name: "Mar", cases: cases.filter(c => new Date(c.created_at).getMonth() === 2).length },
    { name: "Apr", cases: cases.filter(c => new Date(c.created_at).getMonth() === 3).length },
    { name: "May", cases: cases.filter(c => new Date(c.created_at).getMonth() === 4).length },
    { name: "Jun", cases: cases.filter(c => new Date(c.created_at).getMonth() === 5).length },
  ];

  const evidenceTypes = [
    { name: "Documents", value: evidence.filter(e => e.file_type === 'document').length, color: "#3B82F6" },
    { name: "Images", value: evidence.filter(e => e.file_type === 'image').length, color: "#10B981" },
    { name: "Videos", value: evidence.filter(e => e.file_type === 'video').length, color: "#F59E0B" },
    { name: "Logs", value: evidence.filter(e => e.file_type === 'log').length, color: "#EF4444" },
  ];

  const recentActivity = [
    ...cases.slice(-2).map(c => ({ id: `case-${c.id}`, action: "New case created", case: c.title, time: new Date(c.created_at).toLocaleString() })),
    ...evidence.slice(-2).map(e => ({ id: `evidence-${e.id}`, action: "Evidence uploaded", case: e.case_title || 'Unknown', time: new Date(e.uploaded_at).toLocaleString() })),
    ...analyses.slice(-2).map(a => ({ id: `analysis-${a.id}`, action: "Analysis completed", case: a.case_title || 'Unknown', time: new Date(a.completed_at).toLocaleString() })),
  ].sort((a, b) => new Date(b.time) - new Date(a.time)).slice(0, 4);

  if (loading) {
    return (
      <section className="space-y-8">
        <header>
          <h1 className="text-3xl font-bold">Digital Forensics Dashboard</h1>
          <p className="text-gray-400 mt-1">Loading...</p>
        </header>
      </section>
    );
  }

  // Error handled by toast

  const toggleDropdown = (dropdown) => {
    setOpenDropdown(openDropdown === dropdown ? null : dropdown);
  };

  const menuItems = [
    { name: "Cases", icon: FolderOpen, items: ["Create Case", "View Cases", "Case Reports"] },
    { name: "Evidence", icon: FileText, items: ["Upload Evidence", "View Evidence", "Evidence Analysis"] },
    { name: "Analysis", icon: TrendingUp, items: ["Run Analysis", "View Results", "Analysis History"] },
    { name: "Reports", icon: BarChart3, items: ["Generate Report", "View Reports", "Export Data"] },
    { name: "Settings", icon: AlertTriangle, items: ["User Settings", "System Config", "Security"] }
  ];

  return (
    <section className="space-y-8">
      {/* Header with Toggle */}
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Digital Forensics Dashboard</h1>
          <p className="text-gray-400 mt-1">
            Welcome back, {(() => {
              try {
                const user = JSON.parse(localStorage.getItem('user') || '{}');
                const role = user.role || 'investigator';
                if (role === 'admin') return 'Administrator';
                return role.charAt(0).toUpperCase() + role.slice(1);
              } catch (e) {
                return 'Investigator';
              }
            })()}. Here's your system overview.
          </p>
        </div>
        <button onClick={() => setIsVisible(!isVisible)} className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors">
          {isVisible ? <ChevronUp size={24} /> : <ChevronDown size={24} />}
        </button>
      </header>

      {/* Menu Dropdowns */}
      {isVisible && (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
          {menuItems.map((item) => (
            <div key={item.name} className="relative">
              <button onClick={() => toggleDropdown(item.name)} className="w-full bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg p-4 flex items-center justify-between transition-colors">
                <div className="flex items-center gap-3">
                  <item.icon className="w-5 h-5 text-blue-400" />
                  <span className="font-medium">{item.name}</span>
                </div>
                {openDropdown === item.name ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>
              {openDropdown === item.name && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-10">
                  {item.items.map((subItem) => (
                    <button key={subItem} className="w-full text-left px-4 py-2 hover:bg-gray-700 first:rounded-t-lg last:rounded-b-lg transition-colors">{subItem}</button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* AI Helper Panel */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2">
          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mb-6">
            {stats.map(({ name, value, icon: Icon, color }) => (
              <div key={name} className="bg-gray-800 border border-gray-700 rounded-lg p-5">
                <div className="flex justify-between items-center">
                  <div>
                    <p className="text-sm text-gray-400">{name}</p>
                    <p className="text-2xl font-semibold">{value}</p>
                  </div>
                  <Icon className={`w-8 h-8 ${color}`} />
                </div>
              </div>
            ))}
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 h-[380px]">
              <h3 className="font-semibold mb-4">Cases Over Time</h3>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={caseData}>
                  <CartesianGrid stroke="#374151" strokeDasharray="3 3" />
                  <XAxis dataKey="name" stroke="#9CA3AF" />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151" }} />
                  <Bar dataKey="cases" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 h-[380px]">
              <h3 className="font-semibold mb-4">Evidence Distribution</h3>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={evidenceTypes} dataKey="value" outerRadius={90} label>
                    {evidenceTypes.map((e, i) => (<Cell key={i} fill={e.color} />))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Activity */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <h3 className="font-semibold mb-4">Recent Activity</h3>
            <ul className="divide-y divide-gray-700">
              {recentActivity.map(a => (
                <li key={a.id} className="py-3 flex justify-between">
                  <div>
                    <p className="font-medium">{a.action}</p>
                    <p className="text-sm text-gray-400">{a.case}</p>
                  </div>
                  <span className="text-sm text-gray-500">{a.time}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* AI Helper Sidebar */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Bot className="w-6 h-6 text-blue-400" />
              <h3 className="font-semibold text-lg">AI Investigation Assistant</h3>
            </div>
            <button onClick={() => setShowAiPanel(!showAiPanel)} className="text-gray-400 hover:text-white">
              {showAiPanel ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            </button>
          </div>

          {showAiPanel && (
            <>
              <p className="text-sm text-gray-400 mb-4">AI-powered suggestions to help guide your investigation:</p>

              <div className="space-y-3 mb-6">
                {aiSuggestions.map((suggestion, index) => (
                  <div key={index} className={`p-3 rounded-lg border ${suggestion.priority === 'high' ? 'border-red-600 bg-red-900/20' :
                    suggestion.priority === 'medium' ? 'border-yellow-600 bg-yellow-900/20' :
                      'border-gray-600 bg-gray-700/30'
                    }`}>
                    <div className="flex items-start gap-2">
                      <suggestion.icon className={`w-5 h-5 mt-0.5 ${suggestion.priority === 'high' ? 'text-red-400' :
                        suggestion.priority === 'medium' ? 'text-yellow-400' :
                          'text-blue-400'
                        }`} />
                      <div className="flex-1">
                        <p className="font-medium text-sm">{suggestion.title}</p>
                        <p className="text-xs text-gray-400 mt-1">{suggestion.description}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* AI Chat Input */}
              <form onSubmit={handleAiSubmit} className="border-t border-gray-700 pt-4">
                <p className="text-sm text-gray-400 mb-2 flex items-center gap-1">
                  <MessageSquare size={14} /> Ask AI for help:
                </p>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={aiMessage}
                    onChange={(e) => setAiMessage(e.target.value)}
                    placeholder="How do I..."
                    className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-sm text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button type="submit" className="p-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors">
                    <Send size={18} />
                  </button>
                </div>
              </form>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
