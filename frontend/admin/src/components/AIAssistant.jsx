import React, { useState, useEffect, useRef } from 'react';
import { analysisAPI, casesAPI } from '../api';
import { Send, Bot, User, Trash2, ArrowRightCircle, Sparkles, AlertCircle } from 'lucide-react';

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
                role: 'assistant',
                content: "Hello! I'm your AI Forensic Assistant. I can help you analyze evidence, identify patterns, and guide your investigation. How can I assist you today?",
                timestamp: new Date()
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
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMessage = {
            role: 'user',
            content: input,
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setLoading(true);
        setError(null);

        try {
            // Get context if case is selected
            let caseContext = '';
            if (selectedCase) {
                const caseObj = cases.find(c => c._id === selectedCase);
                if (caseObj) {
                    caseContext = `Case Number: ${caseObj.case_number}\nTitle: ${caseObj.title}\nDescription: ${caseObj.description}`;
                }
            }

            // Prepare history for backend (excluding timestamps and formatting)
            const history = messages.map(msg => ({
                role: msg.role,
                content: msg.content
            }));

            const response = await analysisAPI.chatWithAssistant(caseContext, '', userMessage.content, history);

            const assistantMessage = {
                role: 'assistant',
                content: response.data.response,
                timestamp: new Date()
            };

            setMessages(prev => [...prev, assistantMessage]);
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to get response from AI');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const clearChat = () => {
        setMessages([
            {
                role: 'assistant',
                content: "Chat cleared. How else can I help you?",
                timestamp: new Date()
            }
        ]);
    };

    return (
        <div className="flex flex-col h-[calc(100vh-6rem)] p-4 md:p-6 bg-gray-900">
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center space-x-2">
                        <Bot className="text-blue-400" size={28} />
                        <span>Forensic AI Assistant</span>
                    </h1>
                    <p className="text-gray-400 text-sm">Expert guidance for your digital investigations</p>
                </div>

                <div className="flex items-center space-x-3 w-full md:w-auto">
                    <select
                        value={selectedCase}
                        onChange={(e) => setSelectedCase(e.target.value)}
                        className="flex-1 md:w-64 bg-gray-800 text-white border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="">Select Case Context (Optional)</option>
                        {cases.map((c) => (
                            <option key={c._id} value={c._id}>
                                {c.case_number} - {c.title}
                            </option>
                        ))}
                    </select>
                    <button
                        onClick={clearChat}
                        className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
                        title="Clear Chat"
                    >
                        <Trash2 size={20} />
                    </button>
                </div>
            </div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto mb-4 space-y-4 pr-2 custom-scrollbar">
                {messages.map((msg, idx) => (
                    <div
                        key={idx}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                        <div
                            className={`max-w-[80%] flex ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'} items-end gap-2`}
                        >
                            <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${msg.role === 'user' ? 'bg-blue-600' : 'bg-gray-700'
                                }`}>
                                {msg.role === 'user' ? <User size={18} className="text-white" /> : <Bot size={18} className="text-blue-400" />}
                            </div>

                            <div
                                className={`px-4 py-3 rounded-2xl shadow-lg relative ${msg.role === 'user'
                                    ? 'bg-blue-600 text-white rounded-br-none'
                                    : 'bg-gray-800 text-gray-200 border border-gray-700 rounded-bl-none'
                                    }`}
                            >
                                <div className="text-sm leading-relaxed whitespace-pre-wrap">
                                    {msg.content}
                                </div>
                                <div className={`text-[10px] mt-1 opacity-50 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
                {loading && (
                    <div className="flex justify-start">
                        <div className="flex items-end gap-2">
                            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center">
                                <Bot size={18} className="text-blue-400" />
                            </div>
                            <div className="bg-gray-800 border border-gray-700 px-4 py-3 rounded-2xl rounded-bl-none shadow-lg">
                                <div className="flex space-x-1">
                                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
                {error && (
                    <div className="flex justify-center">
                        <div className="bg-red-900/20 border border-red-500/50 text-red-200 px-4 py-2 rounded-lg text-sm flex items-center space-x-2">
                            <AlertCircle size={16} />
                            <span>{error}</span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <form onSubmit={handleSend} className="relative">
                <div className="relative group">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask a question about forensic analysis..."
                        className="w-full bg-gray-800 text-white border border-gray-700 rounded-xl px-4 py-4 pr-14 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all shadow-xl placeholder-gray-500"
                    />
                    <button
                        type="submit"
                        disabled={loading || !input.trim()}
                        className={`absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-lg transition-all ${input.trim() && !loading
                            ? 'bg-blue-600 text-white hover:bg-blue-500 shadow-lg shadow-blue-500/20'
                            : 'bg-gray-700 text-gray-500 cursor-not-allowed'
                            }`}
                    >
                        <Send size={20} />
                    </button>
                </div>
                <div className="mt-2 flex items-center justify-center space-x-4 text-[10px] text-gray-500 uppercase tracking-widest font-semibold">
                    <span className="flex items-center space-x-1">
                        <Sparkles size={10} className="text-blue-500" />
                        <span>Powered by Claude 3</span>
                    </span>
                    <span className="flex items-center space-x-1">
                        <ArrowRightCircle size={10} className="text-green-500" />
                        <span>End-to-End Encrypted</span>
                    </span>
                </div>
            </form>

            <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #374151;
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #4b5563;
        }
      `}</style>
        </div>
    );
};

export default AIAssistant;
