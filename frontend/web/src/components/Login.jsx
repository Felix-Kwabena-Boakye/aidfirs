import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, AlertCircle, UserPlus, LogIn, Shield, CheckCircle, Cpu } from "lucide-react";
import { authAPI } from "../api";
import { toast } from "sonner";

export default function Login() {
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [role, setRole] = useState("analyst");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [registrationPending, setRegistrationPending] = useState(false);

  const navigate = useNavigate();

  /* =========================================================
     🔐 EMAIL / PASSWORD LOGIN + REGISTER
  ========================================================= */
  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      if (isRegisterMode) {
        await authAPI.register({
          username,
          email,
          password,
          first_name: firstName,
          last_name: lastName,
          role,
        });

        setRegistrationPending(true);
        setIsRegisterMode(false);
        setPassword("");

        toast.success("Registration submitted! Awaiting admin approval.");
      } else {
        const response = await authAPI.login({ username, password });

        localStorage.setItem("access_token", response.data.access);
        localStorage.setItem("refresh_token", response.data.refresh);
        localStorage.setItem("user", JSON.stringify(response.data.user));

        toast.success(
          `Welcome back, ${response.data.user.first_name || response.data.user.username}`
        );

        navigate("/dashboard");
      }
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.response?.data?.error ||
        "Login failed";

      setError(msg);
      toast.error(msg);
    } finally {
      setIsLoading(false);
    }
  };

  /* =========================================================
     🔥 GOOGLE LOGIN (FIXED - NO REDIRECT FLOW)
  ========================================================= */
  const handleGoogleLogin = async () => {
    setIsLoading(true);
    setError("");

    try {
      if (!window.google) {
        toast.error("Google SDK not loaded. Add Google script in index.html");
        setIsLoading(false);
        return;
      }

      window.google.accounts.id.initialize({
        client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
        callback: async (response) => {
          try {
            const res = await authAPI.googleOAuth({
              credential: response.credential,
            });

            localStorage.setItem("access_token", res.data.access);
            localStorage.setItem("refresh_token", res.data.refresh);
            localStorage.setItem("user", JSON.stringify(res.data.user));

            toast.success("Google login successful");
            navigate("/dashboard");
          } catch (err) {
            console.log("Google OAuth ERROR:", err.response?.data || err);

            const msg =
              err.response?.data?.message ||
              err.response?.data?.error ||
              "Google login failed";

            setError(msg);
            toast.error(msg);
          }
        },
      });

      window.google.accounts.id.prompt();
    } catch (err) {
      toast.error("Google authentication failed");
    } finally {
      setIsLoading(false);
    }
  };

  /* =========================================================
     🧠 LOAD GOOGLE SCRIPT SAFELY
  ========================================================= */
  useEffect(() => {
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    document.body.appendChild(script);
  }, []);

  /* =========================================================
     🎨 UI
  ========================================================= */
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
      
      <div className="max-w-md w-full bg-slate-900/60 backdrop-blur-xl rounded-2xl border border-slate-800 p-8">

        {/* HEADER */}
        <div className="text-center mb-6">
          <Cpu className="mx-auto text-cyan-400" size={40} />
          <h2 className="text-white font-bold mt-2">Forensic Portal Access</h2>
        </div>

        {/* REGISTRATION STATUS */}
        {registrationPending && (
          <div className="mb-4 p-3 bg-green-900/20 border border-green-500 rounded">
            <CheckCircle className="text-green-400" />
            <p className="text-green-300 text-xs">
              Awaiting admin approval
            </p>
          </div>
        )}

        {/* GOOGLE LOGIN */}
        <button
          onClick={handleGoogleLogin}
          disabled={isLoading}
          className="w-full bg-slate-800 text-white py-2 rounded mb-4"
        >
          Continue with Google
        </button>

        {/* FORM */}
        <form onSubmit={handleSubmit} className="space-y-3">

          {isRegisterMode && (
            <>
              <input
                placeholder="First Name"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                className="w-full p-2 bg-slate-800 text-white"
              />

              <input
                placeholder="Last Name"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                className="w-full p-2 bg-slate-800 text-white"
              />

              <input
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full p-2 bg-slate-800 text-white"
              />

              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full p-2 bg-slate-800 text-white"
              >
                <option value="analyst">Analyst</option>
                <option value="investigator">Investigator</option>
              </select>
            </>
          )}

          {/* USERNAME */}
          <input
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full p-2 bg-slate-800 text-white"
          />

          {/* PASSWORD */}
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full p-2 bg-slate-800 text-white"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-2 top-2 text-white"
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>

          {/* ERROR */}
          {error && (
            <div className="text-red-400 text-xs flex items-center gap-2">
              <AlertCircle size={14} />
              {error}
            </div>
          )}

          {/* SUBMIT */}
          <button
            disabled={isLoading}
            className="w-full bg-cyan-600 text-white py-2 rounded"
          >
            {isRegisterMode ? "Register" : "Login"}
          </button>

        </form>

        {/* TOGGLE */}
        <p className="text-center text-xs text-gray-400 mt-4">
          <button
            onClick={() => setIsRegisterMode(!isRegisterMode)}
            className="text-cyan-400"
          >
            {isRegisterMode ? "Switch to Login" : "Create account"}
          </button>
        </p>

      </div>
    </div>
  );
}
