"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { 
  UploadCloud, 
  Plus, 
  FileText, 
  DollarSign, 
  AlertTriangle, 
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  Sliders,
  ChevronRight,
  Database,
  RefreshCw,
  Award,
  Layers,
  ArrowUpRight
} from "lucide-react";
import { 
  ResponsiveContainer, 
  PieChart, 
  Pie, 
  Cell, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  Legend 
} from "recharts";

export default function Dashboard() {
  const [tenders, setTenders] = useState([]);
  const [totalTenders, setTotalTenders] = useState(0);
  const [loading, setLoading] = useState(true);
  const [isMounted, setIsMounted] = useState(false);

  // Excel Upload states
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [uploadError, setUploadError] = useState(null);

  // Manual Tender Creation Form states
  const [showManualForm, setShowManualForm] = useState(false);
  const [newTender, setNewTender] = useState({
    tender_number: "",
    department: "",
    source_url: "",
    tender_value: "",
    closing_date: ""
  });
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState(null);

  // Global Bidder Profile
  const [bidderProfile, setBidderProfile] = useState({
    turnovers: [150000000, 180000000, 220000000],
    netWorth: 80000000,
    eligibilityRules: ["Must have executed 1 railway signaling project of 50M INR"]
  });
  const [showProfileEditor, setShowProfileEditor] = useState(false);
  const [profileInput, setProfileInput] = useState({
    turnover1: "150000000",
    turnover2: "180000000",
    turnover3: "220000000",
    netWorth: "80000000",
    rules: "Must have executed 1 railway signaling project of 50M INR"
  });

  // Cached recommendation status for list of tenders
  const [recs, setRecs] = useState({});
  const [recsLoading, setRecsLoading] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    fetchTenders();
  }, []);

  // Evaluate recommendations
  useEffect(() => {
    if (tenders.length > 0) {
      evaluateAllTenders();
    }
  }, [tenders, bidderProfile]);

  const fetchTenders = async () => {
    setLoading(true);
    try {
      const data = await api.getTenders(0, 10);
      setTenders(data.items || []);
      setTotalTenders(data.total || 0);
    } catch (err) {
      console.error("Failed to load tenders", err);
    } finally {
      setLoading(false);
    }
  };

  const evaluateAllTenders = async () => {
    const completed = tenders.filter(t => t.status === "COMPLETED");
    if (completed.length === 0) return;

    setRecsLoading(true);
    const updatedRecs = { ...recs };

    for (const tender of completed) {
      if (updatedRecs[tender.id] && updatedRecs[tender.id].profileKey === JSON.stringify(bidderProfile)) {
        continue;
      }
      try {
        const recommendation = await api.getRecommendation(
          tender.id,
          bidderProfile.turnovers,
          bidderProfile.netWorth,
          bidderProfile.eligibilityRules
        );
        updatedRecs[tender.id] = {
          recommendation: recommendation.bid_recommendation,
          win_probability: recommendation.win_probability,
          profileKey: JSON.stringify(bidderProfile)
        };
      } catch (err) {
        console.error(`Failed to get recommendation for tender ${tender.id}`, err);
        updatedRecs[tender.id] = { recommendation: "ERROR", win_probability: 0 };
      }
    }

    setRecs(updatedRecs);
    setRecsLoading(false);
  };

  // Drag and drop Excel upload
  const handleExcelUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setUploadSuccess(null);
    setUploadError(null);

    try {
      const result = await api.importExcel(file);
      setUploadSuccess(`Successfully imported ${result.imported_count} tenders from spreadsheet.`);
      fetchTenders();
    } catch (err) {
      setUploadError(err.message || "Failed to parse Excel import.");
    } finally {
      setUploading(false);
    }
  };

  // Manual Creation
  const handleCreateTender = async (e) => {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);

    const payload = {
      tender_number: newTender.tender_number,
      department: newTender.department,
      source_url: newTender.source_url,
      tender_value: newTender.tender_value ? parseFloat(newTender.tender_value) : null,
      closing_date: newTender.closing_date || null
    };

    try {
      await api.createTender(payload);
      setShowManualForm(false);
      setNewTender({
        tender_number: "",
        department: "",
        source_url: "",
        tender_value: "",
        closing_date: ""
      });
      fetchTenders();
    } catch (err) {
      setCreateError(err.message || "Failed to create tender.");
    } finally {
      setCreating(false);
    }
  };

  // Save Bidder Profile
  const handleSaveProfile = (e) => {
    e.preventDefault();
    const turnovers = [
      parseFloat(profileInput.turnover1) || 0,
      parseFloat(profileInput.turnover2) || 0,
      parseFloat(profileInput.turnover3) || 0
    ];
    const netWorth = parseFloat(profileInput.netWorth) || 0;
    const eligibilityRules = profileInput.rules
      .split("\n")
      .map(r => r.trim())
      .filter(r => r.length > 0);

    setBidderProfile({ turnovers, netWorth, eligibilityRules });
    setShowProfileEditor(false);
  };

  // Aggregate stats
  const getStats = () => {
    let goCount = 0;
    let reviewCount = 0;
    let noBidCount = 0;
    let processingCount = 0;

    tenders.forEach(t => {
      if (t.status !== "COMPLETED") {
        processingCount++;
        return;
      }
      const rec = recs[t.id]?.recommendation;
      if (rec === "GO") goCount++;
      else if (rec === "REVIEW") reviewCount++;
      else if (rec === "NO_BID" || rec === "NO BID") noBidCount++;
    });

    return { goCount, reviewCount, noBidCount, processingCount };
  };

  const stats = getStats();

  // Pie Data
  const pieData = [
    { name: "GO", value: stats.goCount, color: "#10b981" },
    { name: "REVIEW", value: stats.reviewCount, color: "#f59e0b" },
    { name: "NO BID", value: stats.noBidCount, color: "#ef4444" }
  ].filter(d => d.value > 0);

  // Bar Data: Tender Value by Department
  const barData = tenders.reduce((acc, t) => {
    if (!t.tender_value) return acc;
    const valueCr = parseFloat(t.tender_value) / 10000000;
    const existing = acc.find(item => item.department === t.department);
    if (existing) {
      existing.value += valueCr;
    } else {
      acc.push({ department: t.department.substring(0, 12), value: valueCr });
    }
    return acc;
  }, []);

  // Variants for Framer Motion animation
  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08
      }
    }
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 15 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 100 } }
  };

  return (
    <div className="space-y-8">
      {/* Page Title & Action Headers */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl bg-gradient-to-r from-indigo-400 via-indigo-200 to-slate-200 bg-clip-text text-transparent">
            Executive Summary
          </h1>
          <p className="mt-1 text-slate-400 text-xs font-medium">
            Evaluate bidding opportunities, review company compliance eligibility, and assess OEMs and BOQ scopes.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setShowProfileEditor(!showProfileEditor)}
            className="flex items-center gap-2 px-4 py-2 bg-slate-900 border border-slate-800 hover:border-slate-700 hover:bg-slate-800/50 rounded-xl text-xs font-bold text-slate-200 transition-all duration-200 shadow-sm"
          >
            <Sliders className="w-4 h-4 text-indigo-400" />
            Bidder Profile
          </button>
          
          <button
            onClick={() => setShowManualForm(!showManualForm)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-xl text-xs font-bold text-white shadow-md shadow-indigo-500/20 transition-all duration-200 hover:-translate-y-0.5"
          >
            <Plus className="w-4 h-4" />
            Add Single Tender
          </button>
        </div>
      </div>

      {/* Bidder Profile Editor Card */}
      {showProfileEditor && (
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel rounded-2xl p-6 border border-indigo-500/20 shadow-2xl relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-600/5 rounded-full blur-[80px] pointer-events-none" />
          <div className="flex items-center justify-between mb-4 border-b border-slate-800/80 pb-3">
            <h3 className="text-sm font-bold text-indigo-400 flex items-center gap-2">
              <Sliders className="w-4.5 h-4.5" />
              Configure Company Qualification Profile
            </h3>
            <button
              onClick={() => setShowProfileEditor(false)}
              className="text-slate-400 hover:text-slate-200 text-xs font-medium"
            >
              Close
            </button>
          </div>
          <form onSubmit={handleSaveProfile} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Turnover Year 1 (INR)</label>
                <input
                  type="text"
                  value={profileInput.turnover1}
                  onChange={(e) => setProfileInput({ ...profileInput, turnover1: e.target.value })}
                  className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-100 outline-none transition"
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Turnover Year 2 (INR)</label>
                <input
                  type="text"
                  value={profileInput.turnover2}
                  onChange={(e) => setProfileInput({ ...profileInput, turnover2: e.target.value })}
                  className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-100 outline-none transition"
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Turnover Year 3 (INR)</label>
                <input
                  type="text"
                  value={profileInput.turnover3}
                  onChange={(e) => setProfileInput({ ...profileInput, turnover3: e.target.value })}
                  className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-100 outline-none transition"
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Net Worth (INR)</label>
                <input
                  type="text"
                  value={profileInput.netWorth}
                  onChange={(e) => setProfileInput({ ...profileInput, netWorth: e.target.value })}
                  className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-100 outline-none transition"
                />
              </div>
            </div>
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Technical Experience Eligibility Rules (one rule per line)</label>
              <textarea
                rows={2}
                value={profileInput.rules}
                onChange={(e) => setProfileInput({ ...profileInput, rules: e.target.value })}
                className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-100 outline-none transition font-sans"
              />
            </div>
            <div className="flex justify-end">
              <button
                type="submit"
                className="px-4 py-2 bg-indigo-600 text-white rounded-xl text-xs font-bold shadow-md shadow-indigo-500/25 hover:bg-indigo-500 transition-all duration-200"
              >
                Apply Profile Changes
              </button>
            </div>
          </form>
        </motion.div>
      )}

      {/* Manual Tender Creator Card */}
      {showManualForm && (
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel rounded-2xl p-6 border-indigo-500/30 shadow-2xl relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-600/5 rounded-full blur-[80px] pointer-events-none" />
          <div className="flex items-center justify-between mb-4 border-b border-slate-800/80 pb-3">
            <h3 className="text-sm font-bold text-indigo-400 flex items-center gap-2">
              <Plus className="w-4.5 h-4.5" />
              Register New Tender
            </h3>
            <button
              onClick={() => setShowManualForm(false)}
              className="text-slate-400 hover:text-slate-200 text-xs font-medium"
            >
              Discard
            </button>
          </div>
          <form onSubmit={handleCreateTender} className="space-y-4">
            {createError && (
              <div className="flex items-center gap-2 text-rose-400 text-xs bg-rose-500/10 p-3 rounded-lg border border-rose-500/20">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{createError}</span>
              </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Tender Number *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. CORE-EL-SIG-2026-89"
                  value={newTender.tender_number}
                  onChange={(e) => setNewTender({ ...newTender, tender_number: e.target.value })}
                  className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-100 outline-none transition"
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Issuing Department *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Northern Railway"
                  value={newTender.department}
                  onChange={(e) => setNewTender({ ...newTender, department: e.target.value })}
                  className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-100 outline-none transition"
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Tender Document/Source URL *</label>
                <input
                  type="url"
                  required
                  placeholder="e.g. https://ireps.gov.in/tenders/CORE-EL-SIG.pdf"
                  value={newTender.source_url}
                  onChange={(e) => setNewTender({ ...newTender, source_url: e.target.value })}
                  className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-100 outline-none transition"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Value (INR)</label>
                  <input
                    type="number"
                    placeholder="e.g. 120000000"
                    value={newTender.tender_value}
                    onChange={(e) => setNewTender({ ...newTender, tender_value: e.target.value })}
                    className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-100 outline-none transition"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Closing Date</label>
                  <input
                    type="date"
                    value={newTender.closing_date}
                    onChange={(e) => setNewTender({ ...newTender, closing_date: e.target.value })}
                    className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-100 outline-none transition text-slate-300"
                  />
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowManualForm(false)}
                className="px-4 py-2 border border-slate-800 rounded-xl text-xs font-bold text-slate-400 hover:text-slate-200 hover:bg-slate-900 transition"
              >
                Discard
              </button>
              <button
                type="submit"
                disabled={creating}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-xl text-xs font-bold text-white transition flex items-center gap-2 shadow-md shadow-indigo-500/25"
              >
                {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save Tender"}
              </button>
            </div>
          </form>
        </motion.div>
      )}

      {/* KPI Cards Grid */}
      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5"
      >
        {/* Total Tenders Card */}
        <motion.div variants={cardVariants} className="glass-panel-interactive rounded-2xl p-5 flex items-center gap-4 border-t-2 border-indigo-500/30">
          <div className="w-11 h-11 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
            <Layers className="w-5.5 h-5.5" />
          </div>
          <div>
            <span className="block text-2xl font-extrabold text-white leading-tight">
              {loading ? "..." : totalTenders}
            </span>
            <span className="block text-[10px] text-slate-400 font-bold uppercase tracking-wider">Indexed Tenders</span>
          </div>
        </motion.div>

        {/* GO Recommendations Card */}
        <motion.div variants={cardVariants} className="glass-panel-interactive rounded-2xl p-5 flex items-center gap-4 border-t-2 border-emerald-500/30">
          <div className="w-11 h-11 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shrink-0">
            <CheckCircle className="w-5.5 h-5.5" />
          </div>
          <div>
            <span className="block text-2xl font-extrabold text-white leading-tight">
              {recsLoading ? "..." : stats.goCount}
            </span>
            <span className="block text-[10px] text-slate-400 font-bold uppercase tracking-wider">GO Decisions</span>
          </div>
        </motion.div>

        {/* REVIEW Recommendations Card */}
        <motion.div variants={cardVariants} className="glass-panel-interactive rounded-2xl p-5 flex items-center gap-4 border-t-2 border-amber-500/30">
          <div className="w-11 h-11 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 shrink-0">
            <AlertTriangle className="w-5.5 h-5.5" />
          </div>
          <div>
            <span className="block text-2xl font-extrabold text-white leading-tight">
              {recsLoading ? "..." : stats.reviewCount}
            </span>
            <span className="block text-[10px] text-slate-400 font-bold uppercase tracking-wider">Evaluation Queue</span>
          </div>
        </motion.div>

        {/* NO BID Recommendations Card */}
        <motion.div variants={cardVariants} className="glass-panel-interactive rounded-2xl p-5 flex items-center gap-4 border-t-2 border-rose-500/30">
          <div className="w-11 h-11 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 shrink-0">
            <XCircle className="w-5.5 h-5.5" />
          </div>
          <div>
            <span className="block text-2xl font-extrabold text-white leading-tight">
              {recsLoading ? "..." : stats.noBidCount}
            </span>
            <span className="block text-[10px] text-slate-400 font-bold uppercase tracking-wider">NO BID Flagged</span>
          </div>
        </motion.div>
      </motion.div>

      {/* Main Panel Section: Analytics and Excel Upload */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recharts Distribution Visualizations */}
        <div className="lg:col-span-2 glass-panel rounded-2xl p-6 flex flex-col gap-6">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-200">Evaluation Analytics</h3>
              <p className="text-[10px] text-slate-400">Distributions based on semantic matching algorithms.</p>
            </div>
            <button 
              onClick={fetchTenders}
              className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
              title="Refresh statistics"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${recsLoading ? "animate-spin text-indigo-400" : ""}`} />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 min-h-[220px]">
            {/* Recommendation Distribution Ring Chart */}
            <div className="flex flex-col items-center justify-center relative">
              <span className="text-[10px] font-bold text-slate-400 mb-2 uppercase tracking-widest">Decision Breakdown</span>
              {isMounted && pieData.length > 0 ? (
                <div className="w-full h-44">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={65}
                        paddingAngle={3}
                        dataKey="value"
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip 
                        contentStyle={{ backgroundColor: "#0b0f19", borderRadius: "10px", borderColor: "rgba(255,255,255,0.08)", color: "#fff", fontSize: "11px" }}
                      />
                      <Legend verticalAlign="bottom" iconSize={8} wrapperStyle={{ fontSize: "10px" }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center text-xs text-slate-500 h-40 border border-dashed border-slate-800 rounded-2xl w-full">
                  <Database className="w-6 h-6 mb-2 opacity-40 text-slate-500" />
                  <span>No completed evaluation.</span>
                </div>
              )}
            </div>

            {/* Department-wise value distributions */}
            <div className="flex flex-col items-center justify-center">
              <span className="text-[10px] font-bold text-slate-400 mb-2 uppercase tracking-widest">Scope Volume by Entity (Cr)</span>
              {isMounted && barData.length > 0 ? (
                <div className="w-full h-44">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={barData}>
                      <XAxis dataKey="department" stroke="#475569" fontSize={8} tickLine={false} />
                      <YAxis stroke="#475569" fontSize={8} tickLine={false} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: "#0b0f19", borderRadius: "10px", borderColor: "rgba(255,255,255,0.08)", color: "#fff", fontSize: "11px" }}
                      />
                      <Bar dataKey="value" fill="#6366f1" radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center text-xs text-slate-500 h-40 border border-dashed border-slate-800 rounded-2xl w-full">
                  <DollarSign className="w-6 h-6 mb-2 opacity-40 text-slate-500" />
                  <span>No volume values index.</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Drag and Drop Importer Column */}
        <div className="glass-panel rounded-2xl p-6 flex flex-col justify-between gap-6 border-l-2 border-l-indigo-500/80">
          <div>
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <UploadCloud className="w-4.5 h-4.5 text-indigo-400" />
              Spreadsheet Ingestion
            </h3>
            <p className="text-[11px] text-slate-400 mt-1">
              Drop tender registers in Excel format. Our parsing engine automatically downloads PDFs, scans BOQs, and runs AI evaluations.
            </p>
          </div>

          {/* Uploader Box */}
          <div className="flex-1 flex flex-col justify-center">
            <label className="border border-dashed border-slate-800 hover:border-indigo-500/50 rounded-2xl p-5 flex flex-col items-center text-center cursor-pointer transition bg-slate-950/20 hover:bg-slate-950/40">
              <input 
                type="file" 
                accept=".xlsx,.xls" 
                className="hidden" 
                onChange={handleExcelUpload} 
                disabled={uploading} 
              />
              {uploading ? (
                <div className="space-y-2">
                  <Loader2 className="w-7 h-7 text-indigo-500 animate-spin mx-auto" />
                  <span className="block text-xs font-semibold text-slate-200">Parsing sheet details...</span>
                  <span className="block text-[10px] text-slate-500">Worker processes active</span>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="w-9 h-9 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-center mx-auto text-slate-400">
                    <UploadCloud className="w-4.5 h-4.5" />
                  </div>
                  <span className="block text-xs font-semibold text-slate-300">Click to upload spreadsheet</span>
                  <span className="block text-[9px] text-slate-500">Excel formats (.xlsx, .xls)</span>
                </div>
              )}
            </label>
          </div>

          {/* Feedback messages */}
          <div>
            {uploadSuccess && (
              <div className="text-[10px] text-emerald-400 bg-emerald-500/10 p-2.5 rounded-xl border border-emerald-500/20 flex gap-2">
                <CheckCircle className="w-4 h-4 shrink-0" />
                <span>{uploadSuccess}</span>
              </div>
            )}
            {uploadError && (
              <div className="text-[10px] text-rose-400 bg-rose-500/10 p-2.5 rounded-xl border border-rose-500/20 flex gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}
            {!uploadSuccess && !uploadError && (
              <div className="text-slate-500 text-[10px] flex items-center gap-1.5 justify-center font-medium">
                <Clock className="w-3.5 h-3.5" />
                <span>Runs asynchronous AI analysis</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Tenders Section */}
      <div className="glass-panel rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
            <Database className="w-4.5 h-4.5 text-indigo-400" />
            Recently Indexed
          </h3>
          <Link
            href="/tenders"
            className="text-xs font-bold text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
          >
            Database Explorer
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center text-slate-400">
            <Loader2 className="w-7 h-7 text-indigo-500 animate-spin mb-2" />
            <span className="text-xs">Querying database...</span>
          </div>
        ) : tenders.length === 0 ? (
          <div className="py-12 text-center border border-dashed border-slate-800 rounded-2xl bg-slate-950/10 text-slate-500 text-xs">
            No tenders registered yet. Ingest an Excel registry.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800/80 text-slate-400 text-[10px] font-bold uppercase tracking-wider">
                  <th className="py-3 px-4">Tender Number</th>
                  <th className="py-3 px-4">Department</th>
                  <th className="py-3 px-4 text-right">Value (INR)</th>
                  <th className="py-3 px-4">Closing Date</th>
                  <th className="py-3 px-4 text-center">Engine State</th>
                  <th className="py-3 px-4 text-center">Compliance Verdict</th>
                  <th className="py-3 px-4"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40">
                {tenders.map((tender) => {
                  const recInfo = recs[tender.id];
                  const statusGlowClass = 
                    tender.status === "COMPLETED" ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" :
                    tender.status === "FAILED" ? "text-rose-400 bg-rose-500/10 border-rose-500/20" :
                    "text-indigo-400 bg-indigo-500/10 border-indigo-500/20 animate-pulse";

                  return (
                    <tr 
                      key={tender.id} 
                      className="hover:bg-slate-800/20 transition-colors group"
                    >
                      <td className="py-3.5 px-4 font-mono font-bold text-slate-300">
                        {tender.tender_number}
                      </td>
                      <td className="py-3.5 px-4 text-slate-400 font-medium">
                        {tender.department}
                      </td>
                      <td className="py-3.5 px-4 text-right font-semibold text-slate-200">
                        {tender.tender_value ? parseInt(tender.tender_value).toLocaleString("en-IN") : "UNKNOWN"}
                      </td>
                      <td className="py-3.5 px-4 text-slate-400 font-mono">
                        {tender.closing_date ? new Date(tender.closing_date).toLocaleDateString() : "UNKNOWN"}
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-bold border ${statusGlowClass}`}>
                          {tender.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        {tender.status !== "COMPLETED" ? (
                          <span className="text-slate-600 text-xs">—</span>
                        ) : recInfo ? (
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-lg text-[10px] font-bold border ${
                            recInfo.recommendation === "GO" ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" :
                            recInfo.recommendation === "REVIEW" ? "bg-amber-500/10 border-amber-500/30 text-amber-400" :
                            recInfo.recommendation === "NO_BID" || recInfo.recommendation === "NO BID" ? "bg-rose-500/10 border-rose-500/30 text-rose-400" :
                            "bg-slate-800 border-slate-700 text-slate-400"
                          }`}>
                            {recInfo.recommendation}
                            <span className="ml-1 text-[9px] font-medium text-slate-400">
                              ({Math.round(recInfo.win_probability)}%)
                            </span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[10px] text-slate-500">
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            Evaluating...
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <Link
                          href={`/tenders/${tender.id}`}
                          className="inline-flex items-center justify-center p-2 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
                        >
                          <ChevronRight className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
