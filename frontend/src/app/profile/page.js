"use client";

import React, { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { 
  User, 
  Shield, 
  Key, 
  Mail, 
  Calendar, 
  Smartphone, 
  Lock, 
  AlertCircle, 
  CheckCircle,
  ExternalLink,
  Laptop,
  Loader2
} from "lucide-react";

export default function ProfilePage() {
  const [currentUser, setCurrentUser] = useState(null);
  const [resetSending, setResetSending] = useState(false);
  const [resetMessage, setResetMessage] = useState("");
  const [resetError, setResetError] = useState("");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const userStr = localStorage.getItem("user");
      if (userStr) {
        try {
          setCurrentUser(JSON.parse(userStr));
        } catch (e) {
          console.error("Failed to parse user session info", e);
        }
      }
    }
  }, []);

  const handlePasswordResetRequest = async () => {
    if (!currentUser || !currentUser.email) return;
    setResetSending(true);
    setResetMessage("");
    setResetError("");
    try {
      const res = await api.forgotPassword(currentUser.email);
      setResetMessage(res.detail || "Password recovery instructions generated.");
    } catch (err) {
      setResetError(err.message || "Failed to trigger recovery flow.");
    } finally {
      setResetSending(false);
    }
  };

  if (!currentUser) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500 mb-2" />
        <span className="text-xs">Loading user session...</span>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-white bg-gradient-to-r from-indigo-400 to-slate-200 bg-clip-text text-transparent flex items-center gap-2">
          <User className="w-6 h-6 text-indigo-500" />
          Account Diagnostics
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Review your authorization credentials, Active JWT sessions, and linked OAuth identity platforms.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
        {/* Profile Details Card */}
        <div className="glass-panel rounded-2xl p-6 space-y-4 flex flex-col items-center text-center relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-600/5 rounded-full blur-2xl" />
          
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-600 to-blue-500 flex items-center justify-center font-bold text-xl text-white shadow-inner shadow-white/20">
            {currentUser.full_name ? currentUser.full_name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2) : "U"}
          </div>

          <div className="space-y-1">
            <h3 className="text-base font-bold text-slate-100">{currentUser.full_name}</h3>
            <span className="inline-flex px-2 py-0.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[9px] font-bold uppercase tracking-wider">
              {currentUser.role}
            </span>
          </div>

          <div className="w-full border-t border-slate-850 pt-4 space-y-2.5 text-xs text-slate-400 text-left">
            <div className="flex items-center gap-2">
              <Mail className="w-4 h-4 text-slate-600" />
              <span className="truncate">{currentUser.email}</span>
            </div>
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-slate-600" />
              <span>Permission Level: {currentUser.role === "SUPER_ADMIN" ? "SuperUser" : currentUser.role === "ADMIN" ? "Elevated" : "Standard"}</span>
            </div>
          </div>
        </div>

        {/* Security Reset & OAuth Integrations */}
        <div className="md:col-span-2 space-y-6">
          {/* Recovery Tools Card */}
          <div className="glass-panel rounded-2xl p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2 border-b border-slate-850 pb-3">
              <Lock className="w-4.5 h-4.5 text-indigo-400" />
              Credential Verification
            </h3>
            
            <div className="space-y-4">
              <p className="text-xs text-slate-400 leading-relaxed">
                Need to change or rotate your system password? Trigger a secure reset token link. The recovery payload will be processed for your account email.
              </p>

              <button
                onClick={handlePasswordResetRequest}
                disabled={resetSending}
                className="px-4 py-2 bg-slate-900 border border-slate-800 hover:border-slate-600 text-xs font-bold text-slate-350 hover:text-white rounded-xl transition-all flex items-center gap-1.5 cursor-pointer shadow-sm"
              >
                <Key className="w-3.5 h-3.5 text-indigo-400" />
                {resetSending ? "Requesting Link..." : "Generate Password Reset"}
              </button>

              {resetMessage && (
                <div className="text-[10px] text-emerald-400 bg-emerald-500/10 p-2.5 rounded-xl border border-emerald-500/20 flex gap-2">
                  <CheckCircle className="w-4 h-4 shrink-0" />
                  <span>{resetMessage}</span>
                </div>
              )}
              {resetError && (
                <div className="text-[10px] text-rose-400 bg-rose-500/10 p-2.5 rounded-xl border border-rose-500/20 flex gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{resetError}</span>
                </div>
              )}
            </div>
          </div>

          {/* Third-Party Integrations Card */}
          <div className="glass-panel rounded-2xl p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2 border-b border-slate-850 pb-3">
              <ExternalLink className="w-4.5 h-4.5 text-indigo-400" />
              OAuth Identity Connectors
            </h3>

            <div className="flex items-center justify-between p-3.5 bg-slate-950/20 border border-slate-850 rounded-xl">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-500 text-xs font-black">
                  G
                </div>
                <div>
                  <span className="block text-xs font-bold text-slate-200">Google Credentials</span>
                  <span className="block text-[9.5px] text-slate-500">Sign in with one-click Google identity</span>
                </div>
              </div>

              {currentUser.google_id ? (
                <span className="px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-bold">
                  Connected
                </span>
              ) : (
                <span className="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-slate-400 text-[10px] font-bold">
                  Not Linked
                </span>
              )}
            </div>
          </div>

          {/* Device Footprints */}
          <div className="glass-panel rounded-2xl p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2 border-b border-slate-850 pb-3">
              <Laptop className="w-4.5 h-4.5 text-indigo-400" />
              Active Browser footprint
            </h3>
            
            <div className="p-3 bg-slate-950/40 border border-slate-850 rounded-xl space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500">Host IP:</span>
                <span className="text-slate-350 font-mono">127.0.0.1 (Local Session)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">User Agent:</span>
                <span className="text-slate-350 font-sans truncate max-w-[200px] sm:max-w-xs" title={typeof window !== "undefined" ? navigator.userAgent : ""}>
                  {typeof window !== "undefined" ? navigator.userAgent : "Node.js Core"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
