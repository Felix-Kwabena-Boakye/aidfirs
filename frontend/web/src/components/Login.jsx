import React, { useState } from "react";
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, AlertCircle, UserPlus, LogIn, Shield, CheckCircle, Cpu } from 'lucide-react';
import { authAPI } from '../api';
import { toast } from 'sonner';

export default function Login() {
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [role, setRole] = useState('analyst');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [registrationPending, setRegistrationPending] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      if (isRegisterMode) {
        await authAPI.register({
          username,
          email,
          password,
          first_name: firstName,
          last_name: lastName,
          role
        });

        setRegistrationPending(true);
        setIsRegisterMode(false);

        toast.success('Registration submitted! Awaiting admin approval.');

        setPassword('');
      } else {
        const response = await authAPI.login({ username, password });

        localStorage.setItem('access_token', response.data.access);
        localStorage.setItem('refresh_token', response.data.refresh);
        localStorage.setItem('user', JSON.stringify(response.data.user));

        toast.success(
          `Access granted. Welcome back, ${
            response.data.user.first_name || response.data.user.username
          }!`
        );

        navigate('/dashboard');
      }
    } catch (err) {

      const errorMessage =
        err?.response?.data?.detail ||
        err?.response?.data?.error ||
        err?.response?.data?.message ||
        err?.message ||
        'An error occurred';

      if (
        errorMessage.includes('pending') ||
        errorMessage.includes('deactivated') ||
        err?.response?.status === 403
      ) {
        toast.error('Access Denied: Account is pending administrator approval.');
      } else {
        toast.error(errorMessage);
      }

      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setIsLoading(true);
    setError('');

    try {
      const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

      if (!googleClientId) {
        toast.error('Google OAuth client ID is not configured.');
        setIsLoading(false);
        return;
      }

      const redirectUri = `${window.location.origin}/oauth/callback/google`;
      const scope = 'openid email profile';

      const authUrl =
        `https://accounts.google.com/o/oauth2/v2/auth` +
        `?client_id=${googleClientId}` +
        `&redirect_uri=${encodeURIComponent(redirectUri)}` +
        `&response_type=code` +
        `&scope=${encodeURIComponent(scope)}` +
        `&access_type=offline`;

      window.location.href = authUrl;

    } catch (err) {
      toast.error('Google authentication failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4 relative overflow-hidden font-sans antialiased selection:bg-cyan-500/30 selection:text-cyan-200">

      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-[120px] pointer-events-none" />

      <div className="max-w-md w-full bg-slate-900/60 backdrop-blur-xl rounded-2xl shadow-[0_0_50px_rgba(0,0,0,0.4)] border border-slate-800/80 p-8 relative z-10">

        <div className="absolute top-4 left-6 right-6 flex items-center justify-between pointer-events-none">
          <span className="text-[9px] font-mono text-cyan-500/50 uppercase tracking-widest">
            SYSTEM: AIDFIRS v1.0.2
          </span>
          <span className="flex h-2 w-2 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
          </span>
        </div>

        <div className="text-center mb-8 mt-4">
          <div className="flex items-center justify-center mb-4">
            <div className="p-3 bg-gradient-to-br from-cyan-500/20 to-blue-500/10 rounded-2xl border border-cyan-500/30 shadow-[0_0_20px_rgba(6,182,212,0.15)]">
              <Cpu className="h-10 w-10 text-cyan-400" />
            </div>
          </div>
          <h2 className="text-xl font-bold text-white uppercase tracking-wider font-mono">
            Forensic Portal Access
          </h2>
          <p className="text-slate-400 text-xs mt-1.5 font-sans">
            AI-Powered Digital Forensic Investigation & Recovery System
          </p>
        </div>

        {registrationPending && (
          <div className="mb-6 p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 text-center">
            <CheckCircle className="mx-auto mb-2 text-emerald-400 animate-pulse" size={24} />
            <p className="text-emerald-300 font-semibold text-xs">Registration Received</p>
            <p className="text-emerald-400/80 text-[10px] mt-1 leading-relaxed">
              Your account is pending administrator activation. Access will be unlocked upon review.
            </p>
          </div>
        )}

        <div className="space-y-3 mb-6">
          <button
            type="button"
            onClick={handleGoogleLogin}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-3 bg-slate-800 hover:bg-slate-700/80 border border-slate-700/80 hover:border-cyan-500/50 text-white font-medium py-2.5 px-4 rounded-xl transition-all shadow-[0_4px_12px_rgba(0,0,0,0.1)] focus:outline-none focus:ring-1 focus:ring-cyan-500 disabled:opacity-50"
          >
            Continue with Google
          </button>
        </div>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-slate-800"></div>
          </div>
          <div className="relative flex justify-center text-[10px] uppercase tracking-wider font-mono">
            <span className="px-2 bg-slate-900/60 text-slate-500">
              Secure Internal Auth
            </span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">

          {isRegisterMode && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <input
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    placeholder="First Name"
                    className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-xs text-white"
                  />
                </div>
                <div>
                  <input
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    placeholder="Last Name"
                    className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-xs text-white"
                  />
                </div>
              </div>

              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email"
                className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-xs text-white"
              />
            </>
          )}

          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Email / Username"
            className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-xs text-white"
            required
          />

          <div className="relative">
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              className="w-full px-3 py-2 pr-10 bg-slate-950/60 border border-slate-800 rounded-xl text-xs text-white"
              required
            />

            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-2 text-slate-500"
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>

          {error && (
            <div className="flex items-center space-x-2 text-rose-400 bg-rose-950/20 border border-rose-800/30 rounded-xl p-3">
              <AlertCircle size={16} />
              <span className="text-xs">{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-gradient-to-r from-cyan-600 to-blue-600 text-white font-semibold py-2.5 px-4 rounded-xl text-xs uppercase"
          >
            {isLoading
              ? isRegisterMode
                ? 'Creating Record...'
                : 'Authenticating...'
              : isRegisterMode
              ? 'Create Investigator'
              : 'Authenticate'}
          </button>

          <div className="text-center pt-2">
            <button
              type="button"
              onClick={() => {
                setIsRegisterMode(!isRegisterMode);
                setError('');
              }}
              className="text-cyan-400 text-xs flex justify-center gap-2 w-full"
            >
              {isRegisterMode ? (
                <>
                  <LogIn size={14} />
                  Already registered? Gateway login
                </>
              ) : (
                <>
                  <UserPlus size={14} />
                  Register investigator account
                </>
              )}
            </button>
          </div>

        </form>

      </div>
    </div>
  );
}
