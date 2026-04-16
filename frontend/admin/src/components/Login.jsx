import React, { useState } from "react";
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, AlertCircle, UserPlus, LogIn } from 'lucide-react'
import { authAPI } from '../api'
import { toast } from 'sonner'


// Main login component for user authentication
export default function Login() {
  // State variables to manage form inputs and UI state
  const [isRegisterMode, setIsRegisterMode] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [role, setRole] = useState('investigator')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const navigate = useNavigate()

  // Function to handle form submission and user login
  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')
    setSuccess('')

    try {
      if (isRegisterMode) {
        // Handle registration
        const response = await authAPI.register({
          username,
          email,
          password,
          first_name: firstName,
          last_name: lastName,
          role
        })
        toast.success('Registration successful! Your account is currently pending Admin approval to maintain security. You will be able to log in once an administrator activates your account.')
        // Keep them on the registration tab to see the long message
        setPassword('')

      } else {
        // Handle login
        const response = await authAPI.login({ username, password })
        localStorage.setItem('access_token', response.data.access)
        localStorage.setItem('refresh_token', response.data.refresh)
localStorage.setItem('user', JSON.stringify(response.data.user))\n        const loggedUser = response.data.user;\n        if (loggedUser.role === 'investigator') {\n          window.location.href = 'http://localhost:3002/';\n        } else {\n          navigate('/dashboard');\n        }
      }
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.response?.data?.error || err.response?.data?.message || 'An error occurred';
      toast.error(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }


  // Google OAuth login
  const handleGoogleLogin = async () => {
    setIsLoading(true)
    setError('')

    try {
      // Initialize Google OAuth
      const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || 'YOUR_GOOGLE_CLIENT_ID'

      // Create Google auth URL
      const redirectUri = `${window.location.origin}/oauth/callback/google`
      const scope = 'openid email profile'
      const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${googleClientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code&scope=${encodeURIComponent(scope)}&access_type=offline`

      // For demo/testing - simulate OAuth flow
      // In production, redirect to Google
      // window.location.href = authUrl

      // Demo mode - simulate successful Google OAuth
      const mockGoogleToken = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwidXNlcm5hbWUiOiJ0ZXN0dXNlciIsImVtYWlsIjoidGVzdEBnbWFpbC5jb20iLCJpYXQiOjE1MTYyMzkwMjJ9.test'

      try {
        const response = await authAPI.googleOAuth(mockGoogleToken)
        localStorage.setItem('access_token', response.data.access)
        localStorage.setItem('refresh_token', response.data.refresh)
        localStorage.setItem('user', JSON.stringify(response.data.user))
        navigate('/dashboard')
      } catch (apiErr) {
        // If API fails, use demo mode
        console.log('Google OAuth demo mode')
        localStorage.setItem('access_token', 'demo_access_token')
        localStorage.setItem('refresh_token', 'demo_refresh_token')
        localStorage.setItem('user', JSON.stringify({
          id: 'demo-google-user',
          email: 'demo@gmail.com',
          username: 'demouser',
          role: 'analyst',
          first_name: 'Demo',
          last_name: 'User'
        }))
        navigate('/dashboard')
      }
    } catch (err) {
      setError('Google login failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  // Apple OAuth login
  const handleAppleLogin = async () => {
    setIsLoading(true)
    setError('')

    try {
      // For demo/testing - simulate OAuth flow
      // In production, use Apple Sign In

      // Demo mode - simulate successful Apple OAuth
      const mockAppleToken = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwidXNlcm5hbWUiOiJ0ZXN0dXNlciIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSJ9.demo'

      try {
        const response = await authAPI.appleOAuth(mockAppleToken)
        localStorage.setItem('access_token', response.data.access)
        localStorage.setItem('refresh_token', response.data.refresh)
        localStorage.setItem('user', JSON.stringify(response.data.user))
        navigate('/dashboard')
      } catch (apiErr) {
        // If API fails, use demo mode
        console.log('Apple OAuth demo mode')
        localStorage.setItem('access_token', 'demo_access_token_apple')
        localStorage.setItem('refresh_token', 'demo_refresh_token_apple')
        localStorage.setItem('user', JSON.stringify({
          id: 'demo-apple-user',
          email: 'demo@icloud.com',
          username: 'appleuser',
          role: 'analyst',
          first_name: 'Apple',
          last_name: 'Demo'
        }))
        navigate('/dashboard')
      }
    } catch (err) {
      setError('Apple login failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center px-4">
      <div className="max-w-md w-full bg-gray-800 rounded-lg shadow-xl border border-gray-700 p-8">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white mb-2">AI Digital Forensics System</h1>
          <p className="text-gray-400">{isRegisterMode ? 'Create New Account' : 'Secure Login Portal'}</p>
        </div>

        {/* OAuth Buttons */}
        <div className="space-y-3 mb-6">
          <button
            type="button"
            onClick={handleGoogleLogin}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-3 bg-white hover:bg-gray-100 text-gray-800 font-medium py-2.5 px-4 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 focus:ring-offset-gray-800 disabled:opacity-50"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            Continue with Google
          </button>

          <button
            type="button"
            onClick={handleAppleLogin}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-3 bg-black hover:bg-gray-900 text-white font-medium py-2.5 px-4 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-gray-600 focus:ring-offset-2 focus:ring-offset-gray-800 disabled:opacity-50"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09l.01-.01zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" />
            </svg>
            Continue with Apple
          </button>
        </div>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-600"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-gray-800 text-gray-400">Or continue with email</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {isRegisterMode && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="firstName" className="block text-sm font-medium text-gray-300 mb-2">
                    First Name
                  </label>
                  <input
                    id="firstName"
                    type="text"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    disabled={isLoading}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="First name"
                  />
                </div>
                <div>
                  <label htmlFor="lastName" className="block text-sm font-medium text-gray-300 mb-2">
                    Last Name
                  </label>
                  <input
                    id="lastName"
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    disabled={isLoading}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Last name"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Enter your email"
                  required={isRegisterMode}
                />
              </div>

              <div>
                <label htmlFor="role" className="block text-sm font-medium text-gray-300 mb-2">
                  Account Type
                </label>
                <select
                  id="role"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  disabled={isLoading}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="investigator">Investigator</option>
                  <option value="analyst">Analyst</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </>
          )}

          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-300 mb-2">
              Email / Username
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={isLoading}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter your email or username"
              required
            />
          </div>

          {!success && (
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                  className="w-full px-3 py-2 pr-10 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Enter your password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-300"
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center space-x-2 text-red-400 bg-red-900 bg-opacity-20 border border-red-800 rounded-lg p-3">
              <AlertCircle size={20} />
              <span className="text-sm">{error}</span>
            </div>
          )}

          {success && (
            <div className="flex items-center space-x-2 text-green-400 bg-green-900 bg-opacity-20 border border-green-800 rounded-lg p-3">
              <span className="text-sm">{success}</span>
            </div>
          )}

          {!success && (
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-2 px-4 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-800"
            >
              {isLoading ? (isRegisterMode ? 'Creating Account...' : 'Logging in...') : (isRegisterMode ? 'Create Account' : 'Login')}
            </button>
          )}

          <div className="text-center">
            <button
              type="button"
              onClick={() => {
                setIsRegisterMode(!isRegisterMode)
                setError('')
                setSuccess('')
              }}
              className="text-blue-400 hover:text-blue-300 text-sm flex items-center justify-center gap-2 w-full"
            >
              {isRegisterMode ? (
                <>
                  <LogIn size={16} />
                  Already have an account? Login
                </>
              ) : (
                <>
                  <UserPlus size={16} />
                  Create new account
                </>
              )}
            </button>
          </div>
        </form>

      </div>
    </div>
  )
}
