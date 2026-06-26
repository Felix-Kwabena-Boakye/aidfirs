import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { authAPI } from '../api';
import { Shield, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

export default function GoogleCallback() {
  const navigate = useNavigate();
  const location = useLocation();
  const [statusMessage, setStatusMessage] = useState('Initializing Security Operations Center handshake...');

  useEffect(() => {
    const searchParams = new URLSearchParams(location.search);
    const code = searchParams.get('code');

    if (!code) {
      toast.error('Authentication failed: Missing OAuth authorization code.');
      navigate('/');
      return;
    }

    const exchangeCode = async () => {
      try {
        setStatusMessage('Exchanging credentials with Google Identity Services...');
        const redirectUri = `${window.location.origin}/oauth/callback/google`;
        
        const response = await authAPI.googleOAuth({
          code,
          redirect_uri: redirectUri
        });

        // Store tokens
        localStorage.setItem('access_token', response.data.access);
        localStorage.setItem('refresh_token', response.data.refresh);
        localStorage.setItem('user', JSON.stringify(response.data.user));

        toast.success(`Access granted. Welcome back, ${response.data.user.first_name || response.data.user.username}!`);
        navigate('/dashboard');
      } catch (err) {
        console.error('Google OAuth error:', err);
        const errorMsg = err.response?.data?.error || err.response?.data?.detail || 'Verification failed';
        
        if (errorMsg.includes('deactivated') || errorMsg.includes('pending') || err.response?.status === 403) {
          toast.error('Access Denied: Account is pending administrator approval.');
        } else {
          toast.error(`Authentication Failed: ${errorMsg}`);
        }
        navigate('/');
      }
    };

    exchangeCode();
  }, [location, navigate]);

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4 relative overflow-hidden font-sans antialiased">
      {/* Dynamic Cyber Gradient Backgrounds */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-[120px] pointer-events-none" />

      <div className="max-w-md w-full bg-slate-900/60 backdrop-blur-xl rounded-2xl shadow-[0_0_50px_rgba(0,0,0,0.4)] border border-slate-800/80 p-8 text-center relative z-10">
        <div className="absolute top-4 left-6 right-6 flex items-center justify-between pointer-events-none">
          <span className="text-[9px] font-mono text-cyan-500/50 uppercase tracking-widest">GATEWAY: OAUTH</span>
          <span className="flex h-2 w-2 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
          </span>
        </div>

        <div className="flex justify-center mb-6 mt-4">
          <div className="p-3 bg-cyan-500/10 rounded-xl border border-cyan-500/20 animate-pulse">
            <Shield className="h-10 w-10 text-cyan-400" />
          </div>
        </div>

        <h2 className="text-xl font-semibold text-slate-100 mb-2 font-sans tracking-wide">
          Verifying Identity
        </h2>
        
        <p className="text-slate-400 text-sm mb-6 max-w-xs mx-auto">
          Please wait while the AIDFIRS platform authenticates your session with Google.
        </p>

        <div className="flex items-center justify-center space-x-3 bg-slate-950/80 border border-slate-800/60 p-4 rounded-xl font-mono text-xs text-cyan-400 max-w-sm mx-auto">
          <RefreshCw className="h-4 w-4 text-cyan-400 animate-spin flex-shrink-0" />
          <span className="truncate">{statusMessage}</span>
        </div>
      </div>
    </div>
  );
}
