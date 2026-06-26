import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell
} from "recharts";
import {
  AlertTriangle, FileText, FolderOpen, TrendingUp, BarChart3, ChevronDown, ChevronUp,
  Bot, Send, Lightbulb, Search, FileSearch, Activity, MessageSquare, Cpu, Trash2
} from "lucide-react";
import { casesAPI, evidenceAPI, analysisAPI } from "../api";
import { toast } from "sonner";

export default function Dashboard() {
  const navigate = useNavigate();
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
  const [aiLoading, setAiLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState([
    {
      role: 'assistant',
      content: "### Hi there! I am the Forensic AI Assistant.\nI am the core intelligence of the Digital Forensics System. How can I help you today?\n\nYou can ask me about:\n- **NTFS** file system recovery\n- **FAT32** file system recovery\n- **EXT4** file system recovery\n- **APFS** file system recovery\n- **SQLite** database recovery\n- **Time-Stomping** anti-forensics\n- **Carving** signatures and patterns",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const handleSuggestionClick = (suggestion) => {
    setAiMessage(suggestion.prompt || `Tell me about ${suggestion.title}`);
  };

  const handleClearChat = () => {
    setChatMessages([
      {
        role: 'assistant',
        content: "### Hi there! I am the Forensic AI Assistant.\nI am the core intelligence of the Digital Forensics System. How can I help you today?\n\nYou can ask me about:\n- **NTFS** file system recovery\n- **FAT32** file system recovery\n- **EXT4** file system recovery\n- **APFS** file system recovery\n- **SQLite** database recovery\n- **Time-Stomping** anti-forensics\n- **Carving** signatures and patterns",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
  };

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
        priority: 'high',
        prompt: 'How do I create a new case to begin the investigation?'
      });
    }

    if (evidenceData.length === 0 && casesData.length > 0) {
      suggestions.push({
        icon: FileSearch,
        title: 'Upload Evidence',
        description: 'Add evidence files to your case for analysis.',
        action: 'Upload Evidence',
        priority: 'high',
        prompt: 'How do I upload evidence files to the active case?'
      });
    }

    if (casesData.length > 0 && evidenceData.length > 0) {
      suggestions.push({
        icon: Activity,
        title: 'Run AI Analysis',
        description: 'Analyze uploaded evidence using AI to detect anomalies and patterns.',
        action: 'Run Analysis',
        priority: 'medium',
        prompt: 'How do I run AI analysis on the evidence files?'
      });
    }

    if (analysesData.filter(a => a.status === 'pending').length > 0) {
      suggestions.push({
        icon: Search,
        title: 'Review Pending Analysis',
        description: 'You have pending analysis results waiting for review.',
        action: 'View Results',
        priority: 'medium',
        prompt: 'How can I review pending analysis results?'
      });
    }

    // Always add general tips
    suggestions.push({
      icon: Lightbulb,
      title: 'Best Practices',
      description: 'Always maintain chain of custody and document all findings.',
      action: 'Learn More',
      priority: 'low',
      prompt: 'What are the best practices for maintaining chain of custody and documenting findings?'
    });

    setAiSuggestions(suggestions);
  };

  const handleAiSubmit = async (e) => {
    e.preventDefault();
    const msg = aiMessage.trim();
    if (!msg) return;

    const userMsgObj = {
      role: 'user',
      content: msg,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    
    setChatMessages(prev => [...prev, userMsgObj]);
    setAiMessage('');
    setAiLoading(true);

    try {
      const case_context = cases?.[0]?.title || 'No case selected';
      const forensic_data = evidence?.length ? { evidence_count: evidence.length } : '';
      
      const history = chatMessages.map(m => ({
        role: m.role,
        content: m.content
      }));

      const res = await analysisAPI.chatWithAssistant(case_context, forensic_data, msg, history);
      const responseText = res?.data?.response || res?.data?.result?.response || 'No response from AI.';

      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: responseText,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    } catch (err) {
      toast.error('AI chat failed: ' + (err.response?.data?.error || err.message));
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: "⚠️ An error occurred while communicating with the Forensic AI core.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    } finally {
      setAiLoading(false);
    }
  };

  const stats = [
    { name: "Active Cases", value: cases.length.toString(), icon: FolderOpen, color: "text-blue-400" },
    { name: "Evidence Uploaded", value: evidence.length.toString(), icon: FileText, color: "text-green-400" },
    { name: "Pending Analysis", value: analyses.filter(a => a.status === 'pending').length.toString(), icon: TrendingUp, color: "text-yellow-400" },
    { name: "Critical Alerts", value: "0", icon: AlertTriangle, color: "text-red-400" },
    { name: "Deleted Files Recovered", value: "0", icon: FileSearch, color: "text-orange-400" },
    { name: "Carved Artifacts", value: "0", icon: Activity, color: "text-purple-400" },
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
    {
      name: "Cases",
      icon: FolderOpen,
      items: [
        { label: "Create Case", path: "/cases?create=true" },
        { label: "View Cases", path: "/cases" },
        { label: "Case Reports", path: "/reports" }
      ]
    },
    {
      name: "Evidence",
      icon: FileText,
      items: [
        { label: "Upload Evidence", path: "/evidence?create=true" },
        { label: "View Evidence", path: "/evidence" },
        { label: "Evidence Analysis", path: "/analysis" }
      ]
    },
    {
      name: "Analysis",
      icon: TrendingUp,
      items: [
        { label: "Run Analysis", path: "/analysis?create=true" },
        { label: "View Results", path: "/analysis" },
        { label: "Analysis History", path: "/analysis" }
      ]
    },
    {
      name: "Reports",
      icon: BarChart3,
      items: [
        { label: "Generate Report", path: "/reports" },
        { label: "View Reports", path: "/reports" },
        { label: "Export Data", path: "/reports" }
      ]
    },
    {
      name: "Settings",
      icon: AlertTriangle,
      items: [
        { label: "User Settings", path: "/settings?tab=profile" },
        { label: "System Config", path: "/settings?tab=ai" },
        { label: "Security", path: "/settings?tab=security" }
      ]
    }
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
                    <button
                      key={subItem.label}
                      onClick={() => {
                        navigate(subItem.path);
                        setOpenDropdown(null);
                      }}
                      className="w-full text-left px-4 py-2 hover:bg-gray-700 first:rounded-t-lg last:rounded-b-lg transition-colors text-gray-200 text-sm"
                    >
                      {subItem.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* AI Helper Panel */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 space-y-6">
          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {stats.map(({ name, value, icon: Icon, color }) => (
              <div key={name} className="bg-slate-900/40 backdrop-blur-md border border-slate-800/80 rounded-xl p-5 hover:border-cyan-500/30 transition-all shadow-[0_4px_12px_rgba(0,0,0,0.15)] flex justify-between items-center group">
                <div>
                  <p className="text-[10px] uppercase font-mono tracking-wider text-slate-400">{name}</p>
                  <p className="text-2xl font-bold text-white mt-1 font-mono">{value}</p>
                </div>
                <div className="p-3 bg-slate-950/50 rounded-xl border border-slate-800 group-hover:border-cyan-500/20 transition-all">
                  <Icon className={`w-6 h-6 ${color}`} />
                </div>
              </div>
            ))}
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/80 rounded-xl p-6 h-[380px] shadow-[0_4px_12px_rgba(0,0,0,0.15)]">
              <h3 className="font-bold text-white text-sm uppercase tracking-wider font-mono mb-4">Cases Over Time</h3>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={caseData}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
                  <YAxis stroke="#64748b" fontSize={11} />
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: "8px" }} />
                  <Bar dataKey="cases" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/80 rounded-xl p-6 h-[380px] shadow-[0_4px_12px_rgba(0,0,0,0.15)]">
              <h3 className="font-bold text-white text-sm uppercase tracking-wider font-mono mb-4">Evidence Distribution</h3>
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
          <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/80 rounded-xl p-6 shadow-[0_4px_12px_rgba(0,0,0,0.15)]">
            <h3 className="font-bold text-white text-sm uppercase tracking-wider font-mono mb-4">Recent Activity</h3>
            <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-4 font-mono text-xs text-emerald-400 max-h-[220px] overflow-y-auto custom-scrollbar space-y-1.5 shadow-[inset_0_2px_8px_rgba(0,0,0,0.4)]">
              {recentActivity.length === 0 ? (
                <div className="text-slate-500 py-3 text-center">No recent activities logged on system.</div>
              ) : (
                recentActivity.map(a => (
                  <div key={a.id} className="flex justify-between items-start gap-4 hover:bg-slate-900/40 py-1 px-2 rounded transition-all">
                    <div className="flex items-center gap-2 flex-wrap min-w-0">
                      <span className="text-cyan-500 font-bold shrink-0">[SOC-LOG]</span>
                      <span className="text-slate-200 font-semibold">{a.action}</span>
                      <span className="text-slate-600">|</span>
                      <span className="text-slate-400 truncate">{a.case}</span>
                    </div>
                    <span className="text-slate-500 text-[10px] whitespace-nowrap">{a.time}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* AI Helper Sidebar */}
        <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/80 rounded-xl p-6 flex flex-col h-[650px] shadow-[0_4px_12px_rgba(0,0,0,0.25)]">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-800 shrink-0">
            <div className="flex items-center gap-2">
              <Cpu className="w-5 h-5 text-cyan-400 animate-pulse" />
              <h3 className="font-bold text-xs uppercase tracking-wider font-mono text-white">AI Assistant</h3>
            </div>
            <div className="flex items-center gap-3">
              {chatMessages.length > 1 && (
                <button
                  onClick={handleClearChat}
                  className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-all"
                  title="Clear Conversation"
                >
                  <Trash2 size={15} />
                </button>
              )}
              <button onClick={() => setShowAiPanel(!showAiPanel)} className="text-gray-400 hover:text-white transition-colors">
                {showAiPanel ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
              </button>
            </div>
          </div>

          {showAiPanel && (
            <div className="flex flex-col flex-1 min-h-0">
              <style>{`
                .custom-scrollbar::-webkit-scrollbar { width: 4px; height: 4px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: #4b5563; border-radius: 4px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #6b7280; }
              `}</style>

              {/* Chat Messages List */}
              <div className="flex-1 overflow-y-auto pr-1 mb-4 space-y-4 custom-scrollbar min-h-0">
                {chatMessages.map((msg, index) => (
                  <div
                    key={index}
                    className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
                  >
                    <div className="flex items-center gap-1.5 mb-1 text-[9px] text-gray-500 uppercase tracking-wider font-mono">
                      {msg.role === 'user' ? (
                        <>
                          <span>You</span>
                          <span className="text-gray-600">•</span>
                          <span>{msg.timestamp}</span>
                        </>
                      ) : (
                        <>
                          <Cpu size={9} className="text-cyan-400" />
                          <span className="text-cyan-400 font-semibold">Forensic AI</span>
                          <span className="text-gray-600">•</span>
                          <span>{msg.timestamp}</span>
                        </>
                      )}
                    </div>
                    <div
                      className={`p-3.5 rounded-2xl shadow-md ${msg.role === 'user' ?
                        'bg-gradient-to-r from-blue-600/30 to-blue-500/20 border border-blue-500/30 text-white rounded-tr-none max-w-[85%] text-xs leading-relaxed font-sans' :
                        'bg-gray-700/40 border border-gray-600/40 text-gray-200 rounded-tl-none max-w-[95%]'
                        }`}
                    >
                      {msg.role === 'user' ? (
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                      ) : (
                        <MarkdownViewer text={msg.content} />
                      )}
                    </div>
                  </div>
                ))}
                
                {aiLoading && (
                  <div className="flex items-center space-x-2 text-cyan-400 animate-pulse pl-2 py-2 text-xs">
                    <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    <span className="text-[10px] text-gray-500 uppercase tracking-widest pl-1 font-mono">Forensic Core Searching...</span>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </div>

              {/* Suggestions (only on start) */}
              {chatMessages.length === 1 && aiSuggestions.length > 0 && (
                <div className="mb-4 border-t border-gray-700/60 pt-3 shrink-0">
                  <p className="text-[10px] font-semibold text-gray-400 mb-2 uppercase tracking-wider font-mono">Suggested Prompts:</p>
                  <div className="grid grid-cols-1 gap-2 max-h-[160px] overflow-y-auto pr-1 custom-scrollbar">
                    {aiSuggestions.map((suggestion, index) => (
                      <button
                        key={index}
                        onClick={() => handleSuggestionClick(suggestion)}
                        className={`text-left p-2.5 rounded-xl border text-xs transition-all flex items-start gap-2.5 hover:bg-gray-700/30 ${suggestion.priority === 'high' ? 'border-red-900/40 bg-red-950/10' :
                          suggestion.priority === 'medium' ? 'border-yellow-900/40 bg-yellow-950/10' :
                            'border-gray-700 bg-gray-800/50'
                          }`}
                      >
                        <suggestion.icon className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${suggestion.priority === 'high' ? 'text-red-400' :
                          suggestion.priority === 'medium' ? 'text-yellow-400' :
                            'text-blue-400'
                          }`} />
                        <div>
                          <p className="font-semibold text-[11px] text-gray-200">{suggestion.title}</p>
                          <p className="text-[10px] text-gray-400 mt-0.5 line-clamp-1">{suggestion.description}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* AI Chat Input */}
              <form onSubmit={handleAiSubmit} className="border-t border-gray-700 pt-3 shrink-0">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={aiMessage}
                    onChange={(e) => setAiMessage(e.target.value)}
                    placeholder="Ask AI for help (e.g. NTFS, carve)..."
                    className="flex-1 px-3 py-2 bg-gray-900 border border-gray-600 rounded-xl text-xs text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 transition-all focus:border-cyan-500"
                  />
                  <button
                    type="submit"
                    disabled={aiLoading || !aiMessage.trim()}
                    className={`p-2 rounded-xl transition-all ${aiMessage.trim() && !aiLoading
                      ? 'bg-cyan-500 text-black shadow-[0_0_15px_rgba(6,182,212,0.3)] hover:scale-105'
                      : 'bg-gray-700 text-gray-500 cursor-not-allowed'
                      }`}
                  >
                    <Send size={15} />
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

// Custom Markdown Viewer component
const MarkdownViewer = ({ text }) => {
  if (!text) return null;

  const lines = text.split("\n");
  let inTable = false;
  let tableHeaders = [];
  let tableRows = [];

  const elements = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Check for table rows
    if (line.startsWith("|")) {
      inTable = true;
      const parts = line.split("|").map(p => p.trim()).filter((p, idx, arr) => idx > 0 && idx < arr.length - 1);
      
      if (line.includes("---")) {
        continue;
      }
      
      if (tableHeaders.length === 0) {
        tableHeaders = parts;
      } else {
        tableRows.push(parts);
      }
      continue;
    } else {
      if (inTable && tableHeaders.length > 0) {
        elements.push(
          <div key={`table-${i}`} className="overflow-x-auto my-2 border border-gray-700 rounded-lg">
            <table className="w-full text-left text-[11px] border-collapse">
              <thead>
                <tr className="bg-gray-800 border-b border-gray-700">
                  {tableHeaders.map((h, idx) => (
                    <th key={idx} className="px-2 py-1.5 font-semibold text-cyan-400">{parseInline(h)}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {tableRows.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-gray-700/30">
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} className="px-2 py-1.5 text-gray-300">{parseInline(cell)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        inTable = false;
        tableHeaders = [];
        tableRows = [];
      }
    }

    if (line === "") {
      elements.push(<div key={`space-${i}`} className="h-1.5" />);
      continue;
    }

    if (line.startsWith("### ")) {
      elements.push(
        <h3 key={`h3-${i}`} className="text-cyan-400 font-bold text-xs mt-2.5 mb-1 uppercase tracking-wider font-mono">
          {parseInline(line.substring(4))}
        </h3>
      );
    } else if (line.startsWith("## ")) {
      elements.push(
        <h2 key={`h2-${i}`} className="text-cyan-300 font-extrabold text-sm mt-3 mb-1.5 font-mono">
          {parseInline(line.substring(3))}
        </h2>
      );
    } else if (line.startsWith("# ")) {
      elements.push(
        <h1 key={`h1-${i}`} className="text-white font-black text-sm mt-3.5 mb-1.5 font-mono">
          {parseInline(line.substring(2))}
        </h1>
      );
    } else if (/^\d+\.\s/.test(line)) {
      const textContent = line.replace(/^\d+\.\s+/, "");
      const numMatch = line.match(/^\d+/);
      elements.push(
        <div key={`li-${i}`} className="flex items-start gap-1.5 ml-1 my-0.5">
          <span className="text-cyan-400 font-bold text-[11px] mt-0.5">{numMatch ? numMatch[0] : "1"}.</span>
          <p className="text-[11px] text-gray-300 leading-relaxed flex-1">{parseInline(textContent)}</p>
        </div>
      );
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      const textContent = line.substring(2);
      elements.push(
        <div key={`bullet-${i}`} className="flex items-start gap-1.5 ml-1 my-0.5">
          <span className="text-cyan-500 font-bold text-xs mt-[-1px]">•</span>
          <p className="text-[11px] text-gray-300 leading-relaxed flex-1">{parseInline(textContent)}</p>
        </div>
      );
    } else {
      elements.push(
        <p key={`p-${i}`} className="text-[11px] text-gray-300 leading-relaxed my-0.5">
          {parseInline(line)}
        </p>
      );
    }
  }

  if (inTable && tableHeaders.length > 0) {
    elements.push(
      <div key="table-end" className="overflow-x-auto my-2 border border-gray-700 rounded-lg">
        <table className="w-full text-left text-[11px] border-collapse">
          <thead>
            <tr className="bg-gray-800 border-b border-gray-700">
              {tableHeaders.map((h, idx) => (
                <th key={idx} className="px-2 py-1.5 font-semibold text-cyan-400">{parseInline(h)}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {tableRows.map((row, rIdx) => (
              <tr key={rIdx} className="hover:bg-gray-700/30">
                {row.map((cell, cIdx) => (
                  <td key={cIdx} className="px-2 py-1.5 text-gray-300">{parseInline(cell)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return <div className="space-y-0.5">{elements}</div>;
};

// Inline bold and code parser
function parseInline(text) {
  if (!text) return "";
  const regex = /(\*\*.*?\*\*|`.*?`)/g;
  const matches = text.split(regex);
  
  return matches.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index} className="font-semibold text-white">{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={index} className="bg-gray-950 border border-gray-700 px-1 py-0.2 rounded text-[10px] font-mono text-pink-400">{part.slice(1, -1)}</code>;
    }
    return part;
  });
}
