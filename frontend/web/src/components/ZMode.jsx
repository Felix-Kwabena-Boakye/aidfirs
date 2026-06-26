import React, { useState, useEffect, useRef } from 'react';
import { Bot, Terminal, Cpu, Zap, Activity, ShieldCheck, ChevronRight, Play } from 'lucide-react';
import { analysisAPI } from '../api';

const ZMode = () => {
    const [command, setCommand] = useState('');
    const [isExecuting, setIsExecuting] = useState(false);
    const [logs, setLogs] = useState([
        { time: new Date().toLocaleTimeString(), type: 'info', msg: 'Cloud Z Autonomous Kernel initialized.' },
        { time: new Date().toLocaleTimeString(), type: 'system', msg: 'Universal Recovery Engine: Ready' },
        { time: new Date().toLocaleTimeString(), type: 'system', msg: 'Modular AI Orchestrator: Active (Claude 3.5 Sonnet)' }
    ]);
    const logEndRef = useRef(null);

    useEffect(() => {
        logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    const addLog = (msg, type = 'info') => {
        setLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), type, msg }]);
    };

    const handleExecute = (e) => {
        e.preventDefault();
        if (!command.trim() || isExecuting) return;

        setIsExecuting(true);
        addLog(`User Instruction Received: "${command}"`, 'user');

        // Simulate AI Thought Process
        setTimeout(() => {
            addLog('AI Planning: Analyzing system capabilities...', 'ai');
            setTimeout(() => {
                addLog('Plan Created: [1] Scan Disk, [2] Extract Metadata, [3] Summarize Findings', 'ai');
                setTimeout(() => {
                    addLog('Action: Initiating Disk Fragment Carving...', 'system');
                    setTimeout(() => {
                        addLog('Step Complete: 457 fragments retrieved.', 'success');
                        setTimeout(() => {
                            addLog('Action: Running AI Metadata Classifier...', 'system');
                            setTimeout(() => {
                                addLog('Step Complete: Critical indicators found in 12 files.', 'success');
                                setIsExecuting(false);
                                setCommand('');
                                addLog('Autonomous Task Completed Successfully.', 'done');
                            }, 1500);
                        }, 1000);
                    }, 2000);
                }, 1000);
            }, 1000);
        }, 800);
    };

    return (
        <div className="flex flex-col h-[calc(100vh-6rem)] p-4 md:p-8 bg-black text-blue-400 font-mono">
            {/* HUD Header */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="border border-blue-900 bg-blue-950/20 p-4 rounded-lg flex items-center space-x-4 shadow-[0_0_15px_rgba(30,58,138,0.3)]">
                    <div className="p-3 bg-blue-900/30 rounded-full animate-pulse">
                        <Cpu size={24} />
                    </div>
                    <div>
                        <div className="text-[10px] uppercase text-blue-500 font-bold">Mental State</div>
                        <div className="text-lg font-bold text-white tracking-widest">READY / IDLE</div>
                    </div>
                </div>

                <div className="border border-purple-900 bg-purple-950/20 p-4 rounded-lg flex items-center space-x-4">
                    <div className="p-3 bg-purple-900/30 rounded-full">
                        <Zap size={24} className="text-purple-400" />
                    </div>
                    <div>
                        <div className="text-[10px] uppercase text-purple-500 font-bold">Neural Engine</div>
                        <div className="text-lg font-bold text-white tracking-widest">HIGH-POWER</div>
                    </div>
                </div>

                <div className="border border-green-900 bg-green-950/20 p-4 rounded-lg flex items-center space-x-4">
                    <div className="p-3 bg-green-900/30 rounded-full">
                        <ShieldCheck size={24} className="text-green-400" />
                    </div>
                    <div>
                        <div className="text-[10px] uppercase text-green-500 font-bold">Subsystem Integrity</div>
                        <div className="text-lg font-bold text-white tracking-widest">STABLE</div>
                    </div>
                </div>
            </div>

            {/* Terminal Main Area */}
            <div className="flex-1 flex flex-col border border-blue-900 rounded-xl overflow-hidden bg-gray-950/50 backdrop-blur-sm relative">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-blue-900/10 via-transparent to-transparent pointer-events-none"></div>

                {/* Terminal Header */}
                <div className="bg-blue-950/40 border-b border-blue-900 px-4 py-2 flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                        <Terminal size={14} />
                        <span className="text-xs font-bold uppercase tracking-widest text-blue-300">Autonomous Z-Kernel Console</span>
                    </div>
                    <div className="flex space-x-1.5">
                        <div className="w-2.5 h-2.5 rounded-full bg-red-900/40 border border-red-500/50"></div>
                        <div className="w-2.5 h-2.5 rounded-full bg-yellow-900/40 border border-yellow-500/50"></div>
                        <div className="w-2.5 h-2.5 rounded-full bg-green-900/40 border border-green-500/50"></div>
                    </div>
                </div>

                {/* Log View */}
                <div className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar text-sm">
                    {logs.map((log, i) => (
                        <div key={i} className="flex space-x-3 group">
                            <span className="text-blue-900 text-[10px] mt-1 shrink-0">[{log.time}]</span>
                            <span className={`
                                ${log.type === 'user' ? 'text-white font-bold' : ''}
                                ${log.type === 'ai' ? 'text-purple-400 italic' : ''}
                                ${log.type === 'system' ? 'text-blue-500' : ''}
                                ${log.type === 'success' ? 'text-green-400' : ''}
                                ${log.type === 'done' ? 'text-yellow-400 font-bold underline' : 'text-blue-300'}
                            `}>
                                <span className="opacity-50 mr-2">{'>'}</span>
                                {log.msg}
                            </span>
                        </div>
                    ))}
                    {isExecuting && (
                        <div className="flex space-x-3">
                            <span className="text-blue-900 text-[10px] mt-1 shrink-0">[{new Date().toLocaleTimeString()}]</span>
                            <span className="text-blue-300 animate-pulse">
                                <span className="opacity-50 mr-2">{'>'}</span>
                                Processing...
                            </span>
                        </div>
                    )}
                    <div ref={logEndRef} />
                </div>

                {/* Input Bar */}
                <div className="p-4 border-t border-blue-900 bg-blue-950/20">
                    <form onSubmit={handleExecute} className="relative flex items-center">
                        <ChevronRight className="absolute left-3 text-blue-600" size={20} />
                        <input
                            type="text"
                            value={command}
                            onChange={(e) => setCommand(e.target.value)}
                            disabled={isExecuting}
                            placeholder="Enter high-level command (e.g., 'Autonomous scan and report latest case')"
                            className="w-full bg-transparent border border-blue-900 rounded-lg py-3 pl-10 pr-14 text-white focus:outline-none focus:ring-1 focus:ring-blue-500/50 placeholder-blue-950/50 tracking-wider"
                        />
                        <button
                            type="submit"
                            disabled={isExecuting || !command.trim()}
                            className="absolute right-2 p-2 bg-blue-900/40 text-blue-400 rounded-md hover:bg-blue-600 hover:text-white transition-all disabled:opacity-30"
                        >
                            <Play size={18} fill="currentColor" />
                        </button>
                    </form>
                </div>
            </div>

            {/* HUD Footer Information */}
            <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-[10px]">
                    <div className="text-blue-900 font-bold uppercase">Uptime</div>
                    <div className="text-blue-400">00:00:24:55</div>
                </div>
                <div className="text-[10px]">
                    <div className="text-blue-900 font-bold uppercase">Data Processed</div>
                    <div className="text-blue-400">1.2 TB</div>
                </div>
                <div className="text-[10px]">
                    <div className="text-blue-900 font-bold uppercase">Current Case</div>
                    <div className="text-blue-400">NONE / MONITORING</div>
                </div>
                <div className="text-[10px]">
                    <div className="text-blue-900 font-bold uppercase">Z-Level</div>
                    <div className="text-blue-400">NARROW_GENERAL_BETA</div>
                </div>
            </div>

            <style jsx>{`
                .custom-scrollbar::-webkit-scrollbar {
                    width: 4px;
                }
                .custom-scrollbar::-webkit-scrollbar-track {
                    background: transparent;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb {
                    background: #1e3a8a;
                    border-radius: 2px;
                }
            `}</style>
        </div>
    );
};

export default ZMode;
