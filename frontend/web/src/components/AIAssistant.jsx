import React, { useState, useEffect, useRef } from 'react';
import { analysisAPI, casesAPI } from '../api';
import { Send, Cpu, User, Trash2, Zap, Sparkles, Activity, Shield, Loader2 } from 'lucide-react';

const AIAssistant = () => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [cases, setCases] = useState([]);
    const [selectedCase, setSelectedCase] = useState('');
    const [error, setError] = useState(null);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        // Load initial greeting
        setMessages([
            {
                role: 'system',
                content: "| [SYTEM]: Trained Supreme Intelligence (TSI) active. Forensic Oracle v5.0 loaded.",
                timestamp: new Date()
            },
            {
                role: 'assistant',
                content: "| Forensic AI Assistant: \"Hi there! 👋 I am the core intelligence of the Digital Forensics System. My training is complete, and I am ready to guide your investigation. What is our objective today?\"",
                timestamp: new Date(),
                latency: "0.001ms"
            }
        ]);
        fetchCases();
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const fetchCases = async () => {
        try {
            const response = await casesAPI.getCases();
            setCases(response.data);
        } catch (err) {
            console.error('Failed to load cases', err);
        }
    };

    const handleSend = async (e) => {
        if (e) e.preventDefault();
        if (!input.trim() || loading) return;

        const userMsg = input;
        setMessages(prev => [...prev, {
            role: 'user',
            content: userMsg,
            timestamp: new Date()
        }]);

        setInput('');
        setLoading(true);
        setError(null);

        try {
            let caseContext = '';
            if (selectedCase) {
                const caseObj = cases.find(c => c._id === selectedCase);
                if (caseObj) {
                    caseContext = `Case: ${caseObj.case_number} - ${caseObj.title}`;
                }
            }

            const history = messages.filter(m => m.role !== 'system').map(msg => ({
                role: msg.role,
                content: msg.content
            }));

            const response = await analysisAPI.chatWithAssistant(caseContext, '', userMsg, history);

            setMessages(prev => [...prev, {
                role: 'assistant',
                content: `| Forensic AI Assistant: "${response.data.response}"`,
                timestamp: new Date(),
                latency: "0.001ms"
            }]);
        } catch (err) {
            const errMsg = err.response?.data?.error || 'Neural link interrupted.';
            setError(errMsg);
            setMessages(prev => [...prev, {
                role: 'system',
                content: `| [ERROR]: ${errMsg}`,
                timestamp: new Date()
            }]);
        } finally {
            setLoading(false);
        }
    };

    const clearChat = () => {
        setMessages([
            {
                role: 'system',
                content: "| [SYTEM]: Trained Supreme Intelligence (TSI) active. Forensic Oracle v5.0 loaded.",
                timestamp: new Date()
            },
            {
                role: 'assistant',
                content: "| Forensic AI Assistant: \"Hi there! 👋 I am the core intelligence of the Digital Forensics System. My training is complete, and I am ready to guide your investigation. What is our objective today?\"",
                timestamp: new Date(),
                latency: "0.001ms"
            }
        ]);
    };

    return (
        <div className="flex flex-col h-[calc(100vh-6rem)] p-4 md:p-6 bg-[#05070a] relative overflow-hidden">
            {/* Background Glows */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/5 blur-[100px] pointer-events-none" />
            <div className="absolute bottom-0 left-0 w-64 h-64 bg-purple-500/5 blur-[100px] pointer-events-none" />

            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4 z-10">
                <div className="flex items-center space-x-3">
                    <div className="p-2 bg-cyan-500/10 border border-cyan-500/20 rounded-xl">
                        <Cpu className="text-cyan-400" size={32} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-black text-white italic tracking-tighter uppercase">
                            Forensic <span className="text-cyan-400">AI</span> Assistant
                        </h1>
                        <p className="text-cyan-500/40 text-[10px] font-mono tracking-widest uppercase">Autonomous Intelligence Link</p>
                    </div>
                </div>

                <div className="flex items-center space-x-3 w-full md:w-auto">
                    <select
                        value={selectedCase}
                        onChange={(e) => setSelectedCase(e.target.value)}
                        className="flex-1 md:w-72 bg-gray-900 border border-white/10 text-gray-300 rounded-xl px-4 py-2.5 text-xs focus:outline-none focus:border-cyan-400/50 transition-colors"
                    >
                        <option value="">Neural Context: Global Investigation</option>
                        {cases.map((c) => (
                            <option key={c._id} value={c._id}>
                                {c.case_number} - {c.title}
                            </option>
                        ))}
                    </select>
                    <button
                        onClick={clearChat}
                        className="p-2.5 text-gray-500 hover:text-red-400 hover:bg-red-400/10 rounded-xl border border-white/5 transition-all"
                        title="Purge Neural History"
                    >
                        <Trash2 size={20} />
                    </button>
                </div>
            </div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto mb-6 space-y-4 pr-3 custom-scrollbar font-mono text-xs z-10">
                {messages.map((msg, idx) => (
                    <div
                        key={idx}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                        <div className={`max-w-[90%] ${msg.role === 'user' ? 'w-auto' : 'w-full'}`}>
                            {msg.role === 'user' ? (
                                <div className="bg-white/5 border border-white/10 p-4 rounded-2xl rounded-tr-none shadow-xl">
                                    <div className="text-[9px] text-gray-500 uppercase tracking-widest border-b border-white/5 mb-2 pb-1">User Command</div>
                                    <div className="text-gray-200 text-sm">{msg.content}</div>
                                </div>
                            ) : (
                                <div className={`py-1 ${msg.role === 'system' ? 'text-cyan-400 border-l-2 border-cyan-400/30 pl-4' : 'text-purple-400/80 italic border-l-2 border-purple-400/30 pl-4 bg-purple-500/5 rounded-r-xl p-4'}`}>
                                    {msg.role === 'assistant' && msg.latency && (
                                        <div className="flex items-center space-x-2 text-[8px] text-cyan-400/50 uppercase font-bold tracking-tighter mb-1 mt-2">
                                            <Activity size={10} />
                                            <span>Response Time: {msg.latency}</span>
                                        </div>
                                    )}
                                    <div className={msg.role === 'assistant' ? 'text-sm font-sans not-italic text-gray-300 leading-relaxed whitespace-pre-wrap' : ''}>
                                        {msg.content}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
                {loading && (
                    <div className="flex items-center space-x-3 text-cyan-400 animate-pulse pl-4 border-l-2 border-cyan-400/30">
                        <Loader2 className="animate-spin" size={14} />
                        <span className="text-[10px] uppercase font-bold tracking-widest">| Traversing Neural Grid...</span>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="z-10 bg-[#111111] border border-white/10 rounded-2xl p-4 shadow-2xl relative transition-all focus-within:border-cyan-400/30">
                <div className="flex items-center space-x-4">
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleSend();
                            }
                        }}
                        placeholder="Dispatch mission-critical forensic command..."
                        className="flex-1 bg-transparent border-none text-sm text-gray-200 placeholder-gray-600 focus:outline-none resize-none h-12 py-2 font-sans"
                    />
                    <button
                        onClick={handleSend}
                        disabled={loading || !input.trim()}
                        className={`p-3 rounded-xl transition-all ${input.trim() && !loading
                            ? 'bg-cyan-400 text-black shadow-[0_0_20px_rgba(34,211,238,0.4)]'
                            : 'bg-white/10 text-gray-500 opacity-50 cursor-not-allowed'
                            }`}
                    >
                        {loading ? <Loader2 className="animate-spin" size={20} /> : <Zap size={20} />}
                    </button>
                </div>

                <div className="mt-3 pt-3 border-t border-white/5 flex justify-between items-center text-[9px] font-mono text-gray-600 uppercase tracking-widest">
                    <div className="flex items-center space-x-3">
                        <span className="text-cyan-400/50">Core: TSI-4.0</span>
                        <span className="text-purple-400/50">Status: Supreme</span>
                    </div>
                    <div className="italic">* Authorized Investigators Only</div>
                </div>
            </div>

            <style jsx>{`
                .custom-scrollbar::-webkit-scrollbar { width: 4px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 2px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #334155; }
            `}</style>
        </div>
    );
};

export default AIAssistant;
