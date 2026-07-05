import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Eye,
  EyeOff,
  AlertCircle,
  UserPlus,
  LogIn,
  Shield,
  CheckCircle,
  Cpu,
} from "lucide-react";
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

  // =========================
  // LOGIN + REGISTER
  // =========================
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

        toast.success("Registration submitted! Awaiting admin approval.");

        setRegistrationPending(true);
        setIsRegisterMode(false);

        setPassword("");
        setEmail("");
        setFirstName("");
        setLastName("");
      } else {
        const response = await authAPI.login({ username, password });

        console.log("LOGIN RESPONSE:", response.data);

        if (!response.data?.access) {
          throw new Error("Invalid login response from server");
        }

        localStorage.setItem("access_token", response.data.access);
        localStorage.setItem("refresh_token", response.data.refresh);

        toast.success(
          `Welcome back ${
            response.data.user?.first_name ||
            response.data.user?.username ||
            "User"
          }`
        );

        navigate("/dashboard");
      }
    } catch (err) {
      console.log("LOGIN ERROR FULL:", err);

      // 🔥 IMPORTANT: show REAL backend error
      const backendError =
        err?.response?.data?.detail ||
        err?.response?.data?.error ||
        err?.response?.data?.message ||
        err?.message ||
        "Login failed. Please check your credentials.";

      setError(backendError);
      toast.error(backendError);
    } finally {
      setIsLoading(false);
    }
  };

  // =========================
  // GOOGLE LOGIN (BACKEND FLOW)
  // =========================
  const handleGoogleLogin = () => {
    try {
      setIsLoading(true);

      // backend handles OAuth fully
      window.location.href =
        "http://localhost:8000/accounts/google/login/";
    } catch (err) {
      toast.error("Google login failed");
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
      <div className="max-w-md w-full bg-slate-900/60 backdrop-blur-xl rounded-2xl border border-slate-800 p-8">

        {/* Header */}
        <div className="text-center mb-6">
          <Cpu className="h-10 w-10 text-cyan-400 mx-auto mb-2" />
          <h2 className="text-white font-bold">Forensic Portal Access</h2>
        </div>

        {/* Google Login */}
        <button
          onClick={handleGoogleLogin}
          disabled={isLoading}
          className="w-full bg-slate-800 text-white py-2 rounded-xl mb-4"
        >
          Continue with Google
        </button>

        {/* FORM */}
        <form onSubmit={handleSubmit} className="space-y-4">

          {/* Register fields */}
          {isRegisterMode && (
            <>
              <input
                placeholder="First Name"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                className="w-full p-2 rounded bg-slate-950 text-white"
              />
              <input
                placeholder="Last Name"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                className="w-full p-2 rounded bg-slate-950 text-white"
              />
              <input
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full p-2 rounded bg-slate-950 text-white"
              />
            </>
          )}

          {/* Username */}
          <input
            placeholder="Username / Email"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full p-2 rounded bg-slate-950 text-white"
            required
          />

          {/* Password */}
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full p-2 rounded bg-slate-950 text-white"
              required
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-2 text-gray-400"
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>

          {/* ERROR DISPLAY (FIXED) */}
          {error && (
            <div className="flex items-center gap-2 text-red-400 text-xs">
              <AlertCircle size={14} />
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-cyan-600 text-white py-2 rounded-xl"
          >
            {isLoading
              ? isRegisterMode
                ? "Creating..."
                : "Logging in..."
              : isRegisterMode
              ? "Create Account"
              : "Login"}
          </button>

          {/* Toggle */}
          <button
            type="button"
            onClick={() => {
              setIsRegisterMode(!isRegisterMode);
              setError("");
              setRegistrationPending(false);
            }}
            className="w-full text-cyan-400 text-sm"
          >
            {isRegisterMode ? "Back to Login" : "Create Account"}
          </button>
        </form>

        {/* Footer */}
        <div className="mt-4 text-center text-xs text-gray-500">
          Secure forensic environment
        </div>
      </div>
    </div>
  );
}
