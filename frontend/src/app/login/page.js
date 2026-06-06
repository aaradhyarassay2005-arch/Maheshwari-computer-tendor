"use client";

import React, { useState } from "react";
import Link from "next/link";
import { KeyRound, Mail, Layers, Loader2, ArrowRight } from "lucide-react";
import { api } from "../../lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      setError("Please fill in all credentials");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const data = await api.login(email, password);
      // Store session
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      localStorage.setItem("user", JSON.stringify(data.user));
      // Redirect
      window.location.href = "/";
    } catch (err) {
      setError(err.message || "Failed to log in. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setLoading(true);
    setError("");
    try {
      // For MVP/Dev local environments, we pass a mock Google id_token starting with 'mock_'
      const mockEmail = email ? email : "google_operator@example.com";
      const data = await api.googleLogin(`mock_${mockEmail}`);
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      localStorage.setItem("user", JSON.stringify(data.user));
      window.location.href = "/";
    } catch (err) {
      setError(err.message || "Google Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-600/20 border border-blue-500/20 text-blue-500 mb-4 shadow-lg shadow-blue-500/10">
          <Layers className="w-6 h-6" />
        </div>
        <h1 className="text-2xl font-bold bg-gradient-to-r from-slate-100 to-slate-400 bg-clip-text text-transparent">
          Welcome to TenderIntel
        </h1>
        <p className="text-sm text-slate-400 mt-1.5">
          Tender Intelligence Platform Security Perimeter
        </p>
      </div>

      <div className="glass-panel p-8 rounded-2xl border border-border-dark shadow-2xl relative">
        <div className="absolute top-0 right-0 w-16 h-16 bg-blue-500/5 blur-[25px] rounded-full" />
        
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-semibold">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full pl-10 pr-4 py-3 bg-slate-900/60 border border-border-dark rounded-xl text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Password
              </label>
              <Link 
                href="/forgot-password"
                className="text-xs text-blue-400 hover:text-blue-300 font-medium transition-colors"
              >
                Forgot?
              </Link>
            </div>
            <div className="relative">
              <KeyRound className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-10 pr-4 py-3 bg-slate-900/60 border border-border-dark rounded-xl text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:text-slate-400 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 hover:shadow-blue-500/30 flex items-center justify-center gap-2 transition-all cursor-pointer"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                Sign In <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="relative my-6 text-center">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-border-dark" />
          </div>
          <span className="relative px-3 bg-background-dark/80 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
            Or continue with
          </span>
        </div>

        <button
          type="button"
          onClick={handleGoogleLogin}
          disabled={loading}
          className="w-full py-3 px-4 rounded-xl bg-slate-900 border border-border-dark hover:bg-slate-800/60 text-sm font-semibold text-slate-200 flex items-center justify-center gap-2.5 transition-all cursor-pointer"
        >
          {/* Mock Google Icon using SVG */}
          <svg className="w-4 h-4" viewBox="0 0 24 24">
            <path
              fill="#EA4335"
              d="M12.24 10.285V14.4h6.887c-.648 2.41-2.519 4.2-5.136 4.2A5.73 5.73 0 0 1 8.24 12.87a5.73 5.73 0 0 1 5.75-5.73c2.463 0 4.148 1.03 4.975 1.777l3.293-3.29C20.24 3.73 17.36 2 13.99 2C8.36 2 3.8 6.56 3.8 12.19s4.56 10.19 10.19 10.19c5.814 0 9.68-4.086 9.68-9.856c0-.62-.066-1.127-.146-1.637z"
            />
          </svg>
          Google OAuth
        </button>

        <p className="text-center text-xs text-slate-500 mt-8">
          Don&apos;t have an account?{" "}
          <Link 
            href="/register" 
            className="text-blue-400 hover:text-blue-300 font-semibold transition-colors"
          >
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
