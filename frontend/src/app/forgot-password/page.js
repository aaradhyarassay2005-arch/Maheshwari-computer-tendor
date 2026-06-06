"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Mail, Loader2, ArrowRight, Layers, KeyRound } from "lucide-react";
import { api } from "../../lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [resetToken, setResetToken] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email) {
      setError("Please specify your email");
      return;
    }

    setLoading(true);
    setError("");
    setSuccess("");
    setResetToken("");

    try {
      const data = await api.forgotPassword(email);
      setSuccess("Reset request dispatched successfully!");
      if (data.reset_token) {
        setResetToken(data.reset_token);
      }
    } catch (err) {
      setError(err.message || "Failed to dispatch reset request");
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
          Reset Password
        </h1>
        <p className="text-sm text-slate-400 mt-1.5">
          Request password recovery credentials
        </p>
      </div>

      <div className="glass-panel p-8 rounded-2xl border border-border-dark shadow-2xl relative">
        <div className="absolute top-0 right-0 w-16 h-16 bg-blue-500/5 blur-[25px] rounded-full" />

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-semibold">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
            {success}
          </div>
        )}

        {resetToken && (
          <div className="mb-6 p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 text-slate-200 text-xs break-all">
            <span className="block font-semibold text-blue-400 mb-1">Developer Recovery Token:</span>
            <code className="bg-slate-950/60 p-2 rounded block select-all font-mono tracking-wider">{resetToken}</code>
            <Link 
              href={`/reset-password?token=${resetToken}`}
              className="mt-3 inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 font-bold transition-colors"
            >
              Proceed to Reset Form <ArrowRight className="w-3.5 h-3.5" />
            </Link>
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

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:text-slate-400 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 hover:shadow-blue-500/30 flex items-center justify-center gap-2 transition-all cursor-pointer"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                Send Recovery Token <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <p className="text-center text-xs text-slate-500 mt-8">
          Remember your password?{" "}
          <Link 
            href="/login" 
            className="text-blue-400 hover:text-blue-300 font-semibold transition-colors"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
