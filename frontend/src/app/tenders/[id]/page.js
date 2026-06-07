"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { 
  ArrowLeft, 
  Loader2, 
  Sliders, 
  FileText, 
  Layers, 
  Award, 
  Activity, 
  ShieldAlert, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  Search, 
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  Download,
  Info,
  DollarSign,
  ClipboardCheck
} from "lucide-react";
import { 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip 
} from "recharts";

export default function TenderDetails() {
  const router = useRouter();
  const { id } = useParams();
  
  const searchParams = useSearchParams();
  const isReviewParam = searchParams && searchParams.get("review") === "true";

  // Tab control
  const [activeTab, setActiveTab] = useState("analyst"); // analyst, boq, matching, financial, risk, review
  
  // Data states
  const [tender, setTender] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const [boqSummary, setBoqSummary] = useState(null);
  const [boqCategories, setBoqCategories] = useState([]);
  const [boqItems, setBoqItems] = useState([]);
  const [riskAnalysis, setRiskAnalysis] = useState(null);
  const [recommendation, setRecommendation] = useState(null);
  const [analystReport, setAnalystReport] = useState(null);
  const [matchingResults, setMatchingResults] = useState([]);

  // Human Review Board corrections & history states
  const [corrections, setCorrections] = useState({
    tender_number: "",
    department: "",
    tender_value: "",
    closing_date: "",
    emd: "",
    completion_period: "",
    tender_type: "",
    zone: "",
    bid_system: "",
    contract_type: ""
  });
  const [reviewerId, setReviewerId] = useState("operator-1");
  const [comments, setComments] = useState("");
  const [reviewHistory, setReviewHistory] = useState([]);
  
  // General UI states
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  
  // Bidder profile synced with localStorage
  const [bidderProfile, setBidderProfile] = useState({
    turnovers: [150000000, 180000000, 220000000],
    netWorth: 80000000,
    eligibilityRules: ["Must have executed 1 railway signaling project of 50M INR"]
  });
  const [profileInput, setProfileInput] = useState({
    turnover1: "150000000",
    turnover2: "180000000",
    turnover3: "220000000",
    netWorth: "80000000",
    rules: "Must have executed 1 railway signaling project of 50M INR"
  });

  // BOQ pagination
  const [boqSearch, setBoqSearch] = useState("");
  const [boqPage, setBoqPage] = useState(1);
  const boqLimit = 10;

  useEffect(() => {
    setIsMounted(true);
    if (isReviewParam) {
      setActiveTab("review");
    }
    // Load bidder profile from localStorage on mount
    const saved = localStorage.getItem("tender_bidder_profile");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setBidderProfile(parsed);
        setProfileInput({
          turnover1: String(parsed.turnovers[0] || ""),
          turnover2: String(parsed.turnovers[1] || ""),
          turnover3: String(parsed.turnovers[2] || ""),
          netWorth: String(parsed.netWorth || ""),
          rules: parsed.eligibilityRules.join("\n")
        });
      } catch (e) {
        console.error(e);
      }
    }
  }, [isReviewParam]);

  // Pre-populate manual review corrections form once metadata loads
  useEffect(() => {
    if (metadata) {
      setCorrections({
        tender_number: metadata.tender_number || "",
        department: metadata.department || "",
        tender_value: metadata.tender_value || "",
        closing_date: metadata.closing_date || "",
        emd: metadata.emd || "",
        completion_period: metadata.completion_period || "",
        tender_type: metadata.tender_type || "",
        zone: metadata.zone || "",
        bid_system: metadata.bid_system || "",
        contract_type: metadata.contract_type || ""
      });

      // Auto-populate similar work rule from Excel if experience rules is empty or default
      if (metadata.raw_text) {
        setProfileInput(prev => {
          if (!prev.rules || prev.rules === "Must have executed 1 railway signaling project of 50M INR") {
            return { ...prev, rules: metadata.raw_text };
          }
          return prev;
        });
      }
    }
  }, [metadata]);

  // Fetch basic tender details and BOQ / Risk on page mount
  useEffect(() => {
    if (id) {
      fetchCoreTenderData();
    }
  }, [id]);

  const fetchCoreTenderData = async () => {
    setLoading(true);
    try {
      // Fetch basic tender record
      const t = await api.getTender(id);
      setTender(t);

      const isProcessed = t.status === "PARSED" || t.status === "APPROVED" || t.status === "REJECTED";

      if (isProcessed) {
        // Fetch metadata
        try {
          const m = await api.getTenderMetadata(id);
          setMetadata(m);
        } catch (_) {}

        // Fetch BOQ Items
        try {
          const b = await api.getBOQ(id);
          setBoqItems(b.items || []);
        } catch (_) {}

        // Fetch BOQ Summary
        try {
          const bs = await api.getBOQSummary(id);
          setBoqSummary(bs);
        } catch (_) {}

        // Fetch BOQ categories
        try {
          const bc = await api.getBOQCategories(id);
          setBoqCategories(bc.categories || []);
        } catch (_) {}

        // Fetch initial risk analysis
        try {
          const r = await api.getRiskAnalysis(id);
          setRiskAnalysis(r);
        } catch (_) {}

        // Fetch manual review log history
        try {
          const hist = await api.getReviewHistory(id);
          setReviewHistory(hist);
        } catch (_) {}
      }
    } catch (err) {
      console.error("Failed to fetch tender details", err);
    } finally {
      setLoading(false);
    }
  };

  // Submit manual correction & approval verdict
  const handleSubmitReview = async (verdict) => {
    try {
      setEvaluating(true);
      const payload = {
        verdict: verdict,
        reviewer_id: reviewerId,
        comments: comments || "",
        corrections: {
          tender_number: corrections.tender_number || null,
          department: corrections.department || null,
          tender_value: corrections.tender_value ? parseFloat(corrections.tender_value) : null,
          closing_date: corrections.closing_date || null,
          emd: corrections.emd ? parseFloat(corrections.emd) : null,
          completion_period: corrections.completion_period || null,
          tender_type: corrections.tender_type || null,
          zone: corrections.zone || null,
          bid_system: corrections.bid_system || null,
          contract_type: corrections.contract_type || null
        }
      };

      await api.submitReview(id, payload);
      
      // Clear comments box
      setComments("");

      // Reload tender status and updated fields
      await fetchCoreTenderData();
      
      // Default switch back to evaluation workspace tab
      setActiveTab("analyst");
      alert(`Manual review submitted successfully with verdict: ${verdict}`);
    } catch (err) {
      console.error("Failed to submit review", err);
      alert(`Error submitting review corrections: ${err.message}`);
    } finally {
      setEvaluating(false);
    }
  };

  // Run Recommendation & AI Narrative
  const runEvaluation = async (e) => {
    if (e) e.preventDefault();
    setEvaluating(true);

    // Save profile input
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

    const activeProfile = { turnovers, netWorth, eligibilityRules };
    setBidderProfile(activeProfile);
    localStorage.setItem("tender_bidder_profile", JSON.stringify(activeProfile));

    try {
      // Trigger project matching for each rule
      const matchingPromises = eligibilityRules.map(async (rule) => {
        try {
          const matchResult = await api.matchEligibility(rule);
          return matchResult;
        } catch (_) {
          return { rule, matches: [] };
        }
      });
      const matchData = await Promise.all(matchingPromises);
      setMatchingResults(matchData);

      // Trigger recommendation rules engine
      const recResult = await api.getRecommendation(id, turnovers, netWorth, eligibilityRules);
      setRecommendation(recResult);

      // Trigger AI Analyst summary
      const aiResult = await api.getAIAnalystReport(id, turnovers, netWorth, eligibilityRules);
      setAnalystReport(aiResult);
    } catch (err) {
      console.error("Failed to run evaluation", err);
    } finally {
      setEvaluating(false);
    }
  };

  if (loading) {
    return (
      <div className="py-32 flex flex-col items-center justify-center text-slate-400">
        <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-3" />
        <span className="text-sm font-semibold text-slate-200">Loading tender analytics...</span>
      </div>
    );
  }

  if (!tender) {
    return (
      <div className="py-24 text-center glass-panel rounded-3xl p-8 border-rose-500/20 max-w-xl mx-auto">
        <AlertTriangle className="w-12 h-12 text-rose-500 mx-auto mb-3" />
        <h2 className="text-lg font-bold text-white mb-1">Tender Not Found</h2>
        <p className="text-sm text-slate-400 mb-4">The requested tender UUID does not exist or has been deleted.</p>
        <Link 
          href="/tenders"
          className="inline-flex items-center gap-2 px-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-sm font-semibold text-slate-200 hover:text-white"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to repository
        </Link>
      </div>
    );
  }

  const isProcessed = tender.status === "PARSED" || tender.status === "APPROVED" || tender.status === "REJECTED";

  // Handle processing / downloading states
  if (!isProcessed) {
    return (
      <div className="max-w-2xl mx-auto py-16 animate-fadeIn">
        <div className="glass-panel rounded-3xl p-8 text-center space-y-6">
          <div className="w-16 h-16 bg-blue-500/10 border border-blue-500/20 rounded-2xl flex items-center justify-center mx-auto">
            <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-100 uppercase tracking-wide">
              Ingesting and Extracting Tender
            </h2>
            <span className="inline-block mt-2 text-xs font-semibold text-blue-400 border border-blue-500/20 bg-blue-500/10 px-2.5 py-0.5 rounded-full">
              Status: {tender.status}
            </span>
            <p className="mt-4 text-sm text-slate-400 leading-relaxed max-w-md mx-auto">
              Our backend worker is currently downloading the tender PDF, generating text blocks, and running NLP extractions. This page will unlock once completed.
            </p>
          </div>
          <div className="pt-4 border-t border-border-dark flex items-center justify-center gap-4">
            <Link 
              href="/tenders"
              className="px-4 py-2 border border-slate-800 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 transition"
            >
              Back to repository
            </Link>
            <button
              onClick={fetchCoreTenderData}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-xl text-xs font-bold text-white transition"
            >
              Refresh Ingestion Status
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Filtered BOQ items
  const filteredBOQ = boqItems.filter(item => 
    item.item_name.toLowerCase().includes(boqSearch.toLowerCase()) ||
    item.item_code.toLowerCase().includes(boqSearch.toLowerCase())
  );
  
  const paginatedBOQ = filteredBOQ.slice((boqPage - 1) * boqLimit, boqPage * boqLimit);

  // Formatting utility
  const formatINR = (value) => {
    if (!value || value === "UNKNOWN" || value === "None") return "UNKNOWN";
    return parseFloat(value).toLocaleString("en-IN");
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Breadcrumb & Actions */}
      <div className="flex items-center justify-between border-b border-border-dark pb-4">
        <Link 
          href="/tenders"
          className="inline-flex items-center gap-2 text-xs font-bold text-slate-400 hover:text-slate-200 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Tender Database
        </Link>
        <a 
          href={tender.source_url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 border border-slate-800 hover:border-slate-600 rounded-xl text-xs font-bold text-slate-300 hover:text-white transition"
        >
          View original PDF
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </div>

      {/* Tender Header Summary Card */}
      <div className="glass-panel rounded-3xl p-6 grid grid-cols-1 lg:grid-cols-4 gap-6 relative overflow-hidden">
        {/* Glow indicator decoration */}
        <div className="absolute right-0 top-0 w-32 h-32 bg-blue-600/10 rounded-full blur-3xl" />
        
        <div className="lg:col-span-2 space-y-2">
          <span className="text-[10px] text-blue-400 font-bold uppercase tracking-widest">Tender Identification</span>
          <h1 className="text-2xl font-black text-slate-100 font-mono tracking-tight">{tender.tender_number}</h1>
          <div className="flex flex-wrap items-center gap-3 pt-1 text-xs text-slate-400 font-semibold">
            <span className="px-2 py-0.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
              {tender.department}
            </span>
            <span>•</span>
            <span>Closing: {tender.closing_date ? new Date(tender.closing_date).toLocaleDateString() : "UNKNOWN"}</span>
          </div>
        </div>

        <div className="flex flex-col justify-center">
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Estimated Value</span>
          <div className="text-xl font-extrabold text-slate-200 flex items-center gap-1 mt-1 font-mono">
            <span className="text-blue-400 text-xs">₹</span>
            {formatINR(tender.tender_value)}
          </div>
        </div>

        <div className="flex flex-col justify-center lg:items-end">
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest lg:text-right">Extraction Status</span>
          <span className={`inline-flex items-center px-3 py-1 rounded-xl text-xs font-bold border mt-1 w-fit ${
            tender.status === "PARSED" ? "bg-amber-500/10 border-amber-500/30 text-amber-400" :
            tender.status === "APPROVED" ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.15)]" :
            tender.status === "REJECTED" ? "bg-rose-500/10 border-rose-500/30 text-rose-400 shadow-[0_0_10px_rgba(239,68,68,0.15)]" :
            "bg-blue-500/10 border-blue-500/30 text-blue-400"
          }`}>
            {tender.status === "PARSED" && <AlertTriangle className="w-3.5 h-3.5 mr-1" />}
            {tender.status === "APPROVED" && <CheckCircle className="w-3.5 h-3.5 mr-1" />}
            {tender.status === "REJECTED" && <XCircle className="w-3.5 h-3.5 mr-1" />}
            {tender.status}
          </span>
        </div>
      </div>

      {/* Page Content: Left side Profile Form, Right Side Tabs */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 items-start">
        
        {/* Bidder Profile Column */}
        <div className="glass-panel rounded-3xl p-6 space-y-6">
          <div className="border-b border-border-dark pb-3">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Sliders className="w-5 h-5 text-blue-400" />
              Bidder Configuration
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Provide turnovers, net worth, and technical criteria to evaluate this tender.
            </p>
          </div>

          <form onSubmit={runEvaluation} className="space-y-4">
            <div className="space-y-3">
              <label className="block text-xs font-semibold text-slate-300">Turnovers (Last 3 years - INR)</label>
              <div className="grid grid-cols-3 gap-2">
                <input
                  type="number"
                  placeholder="Y1"
                  required
                  value={profileInput.turnover1}
                  onChange={(e) => setProfileInput({ ...profileInput, turnover1: e.target.value })}
                  className="w-full bg-slate-950/80 border border-slate-800 focus:border-blue-500 rounded-xl px-2.5 py-2 text-xs text-slate-200 outline-none transition"
                />
                <input
                  type="number"
                  placeholder="Y2"
                  required
                  value={profileInput.turnover2}
                  onChange={(e) => setProfileInput({ ...profileInput, turnover2: e.target.value })}
                  className="w-full bg-slate-950/80 border border-slate-800 focus:border-blue-500 rounded-xl px-2.5 py-2 text-xs text-slate-200 outline-none transition"
                />
                <input
                  type="number"
                  placeholder="Y3"
                  required
                  value={profileInput.turnover3}
                  onChange={(e) => setProfileInput({ ...profileInput, turnover3: e.target.value })}
                  className="w-full bg-slate-950/80 border border-slate-800 focus:border-blue-500 rounded-xl px-2.5 py-2 text-xs text-slate-200 outline-none transition"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Net Worth (INR)</label>
              <input
                type="number"
                placeholder="Bidder Net Worth"
                required
                value={profileInput.netWorth}
                onChange={(e) => setProfileInput({ ...profileInput, netWorth: e.target.value })}
                className="w-full bg-slate-950/80 border border-slate-800 focus:border-blue-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none transition"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Technical Experience Rules (one per line)</label>
              <textarea
                rows={3}
                placeholder="e.g. Executed railway signaling project of value 50M INR"
                required
                value={profileInput.rules}
                onChange={(e) => setProfileInput({ ...profileInput, rules: e.target.value })}
                className="w-full bg-slate-950/80 border border-slate-800 focus:border-blue-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none transition font-sans"
              />
            </div>

            <button
              type="submit"
              disabled={evaluating}
              className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 text-white rounded-xl text-xs font-bold shadow-lg shadow-blue-500/20 transition flex items-center justify-center gap-2"
            >
              {evaluating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Running LLM & Rules Engines...
                </>
              ) : (
                "Run Recommendation Engine"
              )}
            </button>
          </form>

          {/* Metadata Sidebar Helper */}
          {metadata && (
            <div className="pt-4 border-t border-slate-800 space-y-3">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest flex items-center gap-1">
                <Info className="w-3.5 h-3.5" />
                Parsed Metadata Context
              </span>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">Tender Authority:</span>
                  <span className="text-slate-300 font-medium">{metadata.tender_authority || "UNKNOWN"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">EMD Value:</span>
                  <span className="text-slate-300 font-medium">{metadata.emd_amount ? `₹${formatINR(metadata.emd_amount)}` : "UNKNOWN"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Work Duration:</span>
                  <span className="text-slate-300 font-medium">{metadata.work_duration || "UNKNOWN"}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Evaluation Details & Tabs Column */}
        <div className="xl:col-span-2 space-y-6">
          {/* Tab Selection */}
          <div className="flex border-b border-slate-800 gap-2 overflow-x-auto scrollbar-none pb-0.5">
            {(tender.status === "PARSED" || isReviewParam || reviewHistory.length > 0) && (
              <button
                onClick={() => setActiveTab("review")}
                className={`pb-3 px-4 text-xs font-bold transition-all border-b-2 flex items-center gap-1.5 ${
                  activeTab === "review" 
                    ? "border-indigo-500 text-indigo-400" 
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Verification Board
                {tender.status === "PARSED" && <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />}
              </button>
            )}
            <button
              onClick={() => setActiveTab("analyst")}
              className={`pb-3 px-4 text-xs font-bold transition-all border-b-2 ${
                activeTab === "analyst" 
                  ? "border-blue-500 text-blue-400" 
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              AI Analyst Report
            </button>
            <button
              onClick={() => setActiveTab("boq")}
              className={`pb-3 px-4 text-xs font-bold transition-all border-b-2 ${
                activeTab === "boq" 
                  ? "border-blue-500 text-blue-400" 
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              BOQ Summary
            </button>
            <button
              onClick={() => setActiveTab("matching")}
              className={`pb-3 px-4 text-xs font-bold transition-all border-b-2 ${
                activeTab === "matching" 
                  ? "border-blue-500 text-blue-400" 
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              Technical Matching
            </button>
            <button
              onClick={() => setActiveTab("financial")}
              className={`pb-3 px-4 text-xs font-bold transition-all border-b-2 ${
                activeTab === "financial" 
                  ? "border-blue-500 text-blue-400" 
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              Financial Checks
            </button>
            <button
              onClick={() => setActiveTab("risk")}
              className={`pb-3 px-4 text-xs font-bold transition-all border-b-2 ${
                activeTab === "risk" 
                  ? "border-blue-500 text-blue-400" 
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              Compliance Risks
            </button>
          </div>

          {/* TAB CONTENT panels */}

          {/* TAB 0: HUMAN REVIEW BOARD */}
          {activeTab === "review" && (
            <div className="space-y-6">
              {/* If pending review or isReviewParam, show form */}
              {tender.status === "PARSED" ? (
                <div className="glass-panel rounded-3xl p-6 space-y-6">
                  <div className="border-b border-border-dark pb-3">
                    <h4 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                      <ClipboardCheck className="w-5 h-5 text-indigo-400" />
                      Ingestion Verification & Corrections
                    </h4>
                    <p className="text-xs text-slate-400 mt-1">
                      Validate and edit the extracted parameters below. Approving commits values and unlocks downstream analytics.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1.5">Tender Number</label>
                      <input
                        type="text"
                        value={corrections.tender_number}
                        onChange={(e) => setCorrections({ ...corrections, tender_number: e.target.value })}
                        className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none transition"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1.5">Department</label>
                      <input
                        type="text"
                        value={corrections.department}
                        onChange={(e) => setCorrections({ ...corrections, department: e.target.value })}
                        className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none transition"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1.5">Tender Value (INR)</label>
                      <input
                        type="number"
                        value={corrections.tender_value}
                        onChange={(e) => setCorrections({ ...corrections, tender_value: e.target.value })}
                        className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none transition font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1.5">Closing Date (YYYY-MM-DD)</label>
                      <input
                        type="date"
                        value={corrections.closing_date}
                        onChange={(e) => setCorrections({ ...corrections, closing_date: e.target.value })}
                        className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none transition font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1.5">EMD Value (INR)</label>
                      <input
                        type="number"
                        value={corrections.emd}
                        onChange={(e) => setCorrections({ ...corrections, emd: e.target.value })}
                        className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none transition font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1.5">Completion Period</label>
                      <input
                        type="text"
                        value={corrections.completion_period}
                        onChange={(e) => setCorrections({ ...corrections, completion_period: e.target.value })}
                        className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none transition"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1.5">Tender Type</label>
                      <input
                        type="text"
                        value={corrections.tender_type}
                        onChange={(e) => setCorrections({ ...corrections, tender_type: e.target.value })}
                        className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none transition"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1.5">Zone</label>
                      <input
                        type="text"
                        value={corrections.zone}
                        onChange={(e) => setCorrections({ ...corrections, zone: e.target.value })}
                        className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none transition"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1.5">Bid System</label>
                      <input
                        type="text"
                        value={corrections.bid_system}
                        onChange={(e) => setCorrections({ ...corrections, bid_system: e.target.value })}
                        className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none transition"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1.5">Contract Type</label>
                      <input
                        type="text"
                        value={corrections.contract_type}
                        onChange={(e) => setCorrections({ ...corrections, contract_type: e.target.value })}
                        className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none transition"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 border-t border-slate-800 pt-4">
                    <div className="md:col-span-2">
                      <label className="block text-xs font-semibold text-slate-300 mb-1.5">Reviewer Comments</label>
                      <textarea
                        rows={2}
                        placeholder="Provide details on the corrections or reasons for rejection..."
                        value={comments}
                        onChange={(e) => setComments(e.target.value)}
                        className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none transition"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1.5">Reviewer ID</label>
                      <input
                        type="text"
                        value={reviewerId}
                        onChange={(e) => setReviewerId(e.target.value)}
                        className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none transition"
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-end gap-3 pt-2">
                    <button
                      onClick={() => handleSubmitReview("REJECTED")}
                      disabled={evaluating}
                      className="px-5 py-2.5 bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/30 hover:border-rose-500/50 text-rose-400 rounded-xl text-xs font-bold transition flex items-center gap-1.5"
                    >
                      <XCircle className="w-4 h-4" />
                      Reject Bid
                    </button>
                    <button
                      onClick={() => handleSubmitReview("APPROVED")}
                      disabled={evaluating}
                      className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5 shadow-lg shadow-indigo-600/20"
                    >
                      <CheckCircle className="w-4 h-4" />
                      Approve & Lock
                    </button>
                  </div>
                </div>
              ) : (
                <div className="glass-panel rounded-3xl p-6 border border-indigo-500/10 bg-indigo-500/5 text-center space-y-2">
                  <CheckCircle className="w-10 h-10 mx-auto text-emerald-400 opacity-80 animate-bounce" />
                  <h4 className="text-sm font-bold text-white">Verification Status: reviewed</h4>
                  <p className="text-xs text-slate-400">This tender has already been manually verified and transitioned to {tender.status}. Downstream analytics are active.</p>
                </div>
              )}

              {/* Review History Logs */}
              {reviewHistory.length > 0 && (
                <div className="space-y-4">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Verification Audit Logs</h4>
                  <div className="space-y-4">
                    {reviewHistory.map((rev) => (
                      <div key={rev.id} className="glass-panel rounded-3xl p-5 space-y-3 border border-slate-800 hover:border-slate-700 transition">
                        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-slate-200">Reviewer: {rev.reviewer_id}</span>
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-lg text-[9px] font-bold border ${
                              rev.verdict === "APPROVED" 
                                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" 
                                : "bg-rose-500/10 border-rose-500/30 text-rose-400"
                            }`}>
                              {rev.verdict}
                            </span>
                          </div>
                          <span className="text-[10px] text-slate-500">
                            {new Date(rev.reviewed_at).toLocaleString()}
                          </span>
                        </div>
                        {rev.comments && (
                          <p className="text-xs text-slate-400 bg-slate-950/20 p-2.5 border border-slate-900 rounded-xl leading-relaxed">
                            <span className="font-semibold text-slate-300 block mb-0.5">Comments:</span>
                            {rev.comments}
                          </p>
                        )}
                        {Object.keys(rev.corrected_values).length > 0 && (
                          <div className="text-xs text-slate-400 space-y-1.5">
                            <span className="font-semibold text-slate-300">Corrections Applied:</span>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono mt-1">
                              {Object.entries(rev.corrected_values).map(([field, newVal]) => {
                                const origVal = rev.original_values[field];
                                return (
                                  <div key={field} className="p-2 bg-slate-950/30 rounded-lg border border-slate-900">
                                    <span className="text-slate-500 block text-[9px] uppercase tracking-wider">{field}</span>
                                    <div className="flex items-center gap-2 mt-0.5">
                                      <span className="line-through text-rose-500/70">{origVal || "empty"}</span>
                                      <span className="text-slate-500">→</span>
                                      <span className="text-emerald-400 font-bold">{newVal || "empty"}</span>
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 1: AI ANALYST & DECISION */}
          {activeTab === "analyst" && (
            <div className="space-y-6">
              {!recommendation ? (
                <div className="glass-panel rounded-3xl p-8 text-center text-slate-500 space-y-2">
                  <Award className="w-10 h-10 mx-auto opacity-30 text-blue-400" />
                  <p className="text-sm">Recommendation engines not run yet.</p>
                  <p className="text-xs text-slate-500">Configure bidder parameters on the left and click "Run Recommendation Engine".</p>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Decision summary panel */}
                  <div className={`glass-panel rounded-3xl p-6 border-l-8 ${
                    recommendation.recommendation === "GO" ? "border-l-emerald-500 glow-go" :
                    recommendation.recommendation === "REVIEW" ? "border-l-amber-500 glow-review" :
                    "border-l-rose-500 glow-nobid"
                  } flex flex-col md:flex-row items-center justify-between gap-6`}>
                    
                    <div className="space-y-2">
                      <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Engine Verdict</span>
                      <div className="flex items-center gap-3">
                        <span className={`px-4 py-1.5 rounded-xl text-lg font-black tracking-widest border ${
                          recommendation.recommendation === "GO" ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" :
                          recommendation.recommendation === "REVIEW" ? "bg-amber-500/10 border-amber-500/30 text-amber-400" :
                          "bg-rose-500/10 border-rose-500/30 text-rose-400"
                        }`}>
                          {recommendation.recommendation}
                        </span>
                        <div className="text-xs text-slate-400">
                          Confidence: <span className="font-semibold text-slate-200">{(recommendation.confidence_score * 100).toFixed(0)}%</span>
                        </div>
                      </div>
                      <p className="text-xs text-slate-400 font-medium leading-relaxed mt-2">
                        {recommendation.decision_explanation}
                      </p>
                    </div>

                    {/* Radial SVG Gauge */}
                    <div className="flex flex-col items-center">
                      <div className="relative w-24 h-24 flex items-center justify-center">
                        <svg className="w-full h-full transform -rotate-90">
                          <circle cx="48" cy="48" r="40" stroke="rgba(255,255,255,0.05)" strokeWidth="6" fill="transparent" />
                          <circle 
                            cx="48" 
                            cy="48" 
                            r="40" 
                            stroke={
                              recommendation.recommendation === "GO" ? "#10b981" :
                              recommendation.recommendation === "REVIEW" ? "#f59e0b" :
                              "#ef4444"
                            } 
                            strokeWidth="6" 
                            fill="transparent" 
                            strokeDasharray={251.2}
                            strokeDashoffset={251.2 - (251.2 * recommendation.win_probability) / 100}
                          />
                        </svg>
                        <div className="absolute flex flex-col items-center">
                          <span className="text-lg font-black text-slate-100">{Math.round(recommendation.win_probability)}%</span>
                          <span className="text-[8px] text-slate-400 uppercase tracking-widest font-bold">Win Prob</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Consolidate Pros/Cons */}
                  {recommendation.key_reasons && (
                    <div className="glass-panel rounded-3xl p-6 space-y-3">
                      <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Evaluation Pros & Cons</h4>
                      <ul className="space-y-2 text-xs">
                        {recommendation.key_reasons.map((reason, i) => {
                          const isNegative = reason.toLowerCase().includes("fail") || reason.toLowerCase().includes("risk") || reason.toLowerCase().includes("not qualified") || reason.toLowerCase().includes("penalty");
                          return (
                            <li key={i} className="flex gap-2 items-start">
                              {isNegative ? (
                                <XCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                              ) : (
                                <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                              )}
                              <span className="text-slate-300 font-medium">{reason}</span>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  )}

                  {/* Dynamic Document Checklist */}
                  {recommendation.required_documents && (
                    <div className="glass-panel rounded-3xl p-6 space-y-3">
                      <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                        <FileText className="w-4 h-4 text-blue-400" />
                        Required Submission Checklist
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                        {recommendation.required_documents.map((doc, idx) => (
                          <div key={idx} className="flex items-center gap-2 p-2 bg-slate-950/20 border border-slate-800 rounded-xl">
                            <span className="w-5 h-5 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-[10px] font-bold text-blue-400">
                              {idx + 1}
                            </span>
                            <span className="text-slate-300 font-medium">{doc}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Gemini Generative Narratives */}
                  {analystReport && (
                    <div className="space-y-6">
                      <div className="border-t border-slate-800 pt-4">
                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Gemini Analyst Explanations</h4>
                      </div>

                      {/* Executive Summary */}
                      <div className="glass-panel rounded-3xl p-6 space-y-2 border-l-4 border-l-blue-500">
                        <h5 className="text-xs font-bold text-blue-400 uppercase">Executive Summary</h5>
                        <p className="text-xs text-slate-300 leading-relaxed font-medium whitespace-pre-line">{analystReport.executive_summary}</p>
                      </div>

                      {/* Management Brief */}
                      <div className="glass-panel rounded-3xl p-6 space-y-2">
                        <h5 className="text-xs font-bold text-slate-300 uppercase">Management Briefing</h5>
                        <p className="text-xs text-slate-400 leading-relaxed whitespace-pre-line">{analystReport.management_brief}</p>
                      </div>

                      {/* Technical Narrative */}
                      <div className="glass-panel rounded-3xl p-6 space-y-2">
                        <h5 className="text-xs font-bold text-slate-300 uppercase">Eligibility Explanation</h5>
                        <p className="text-xs text-slate-400 leading-relaxed whitespace-pre-line">{analystReport.eligibility_explanation}</p>
                      </div>

                      {/* Risks mitigations */}
                      <div className="glass-panel rounded-3xl p-6 space-y-2 border-l-4 border-l-amber-500">
                        <h5 className="text-xs font-bold text-amber-400 uppercase">Risk Narrative & Mitigation</h5>
                        <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-line">{analystReport.risk_explanation}</p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: BOQ TAB */}
          {activeTab === "boq" && (
            <div className="space-y-6">
              {/* Stats overview */}
              {boqSummary && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="glass-panel rounded-2xl p-4">
                    <span className="block text-[10px] text-slate-400 uppercase font-bold">Total Items</span>
                    <span className="block text-xl font-bold text-slate-200 mt-1 font-mono">{boqSummary.total_items}</span>
                  </div>
                  <div className="glass-panel rounded-2xl p-4">
                    <span className="block text-[10px] text-slate-400 uppercase font-bold">Estimated Cost</span>
                    <span className="block text-xl font-bold text-slate-200 mt-1 font-mono">₹{formatINR(boqSummary.total_estimated_amount)}</span>
                  </div>
                  <div className="glass-panel rounded-2xl p-4">
                    <span className="block text-[10px] text-slate-400 uppercase font-bold">NLP Confidence</span>
                    <span className="block text-xl font-bold text-slate-200 mt-1 font-mono">{Math.round(boqSummary.average_confidence * 100)}%</span>
                  </div>
                </div>
              )}

              {/* Categories chart if exists */}
              {isMounted && boqCategories.length > 0 && (
                <div className="glass-panel rounded-3xl p-5">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">Material Cost Distribution</h4>
                  <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={boqCategories.map(c => ({ category: c.category.substring(0, 20), amount: parseFloat(c.total_amount) / 100000 }))}>
                        <XAxis dataKey="category" stroke="#64748b" fontSize={9} tickLine={false} />
                        <YAxis stroke="#64748b" fontSize={9} label={{ value: "Lakhs (INR)", angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 9 }} tickLine={false} />
                        <Tooltip contentStyle={{ backgroundColor: "#1e293b", borderColor: "rgba(255,255,255,0.08)", color: "#fff" }} />
                        <Bar dataKey="amount" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* BOQ items grid list */}
              <div className="glass-panel rounded-3xl p-6 space-y-4">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 border-b border-border-dark pb-3">
                  <h4 className="text-xs font-bold text-slate-200 uppercase">Extracted Schedule of Items</h4>
                  <div className="relative w-full sm:w-64">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                      type="text"
                      placeholder="Search BOQ items..."
                      value={boqSearch}
                      onChange={(e) => {
                        setBoqSearch(e.target.value);
                        setBoqPage(1);
                      }}
                      className="w-full bg-slate-950/80 border border-slate-800 focus:border-blue-500 rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-200 outline-none transition"
                    />
                  </div>
                </div>

                {paginatedBOQ.length === 0 ? (
                  <div className="py-12 text-center text-slate-500 text-xs">
                    No matching BOQ schedule items found.
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="border-b border-slate-800 text-slate-400 font-semibold uppercase">
                            <th className="py-2.5 px-3">Code</th>
                            <th className="py-2.5 px-3">Item Name / Scope</th>
                            <th className="py-2.5 px-3 text-right">Quantity</th>
                            <th className="py-2.5 px-3">Unit</th>
                            <th className="py-2.5 px-3 text-right">Unit Rate (₹)</th>
                            <th className="py-2.5 px-3 text-right font-bold">Amount (₹)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/40 text-slate-300">
                          {paginatedBOQ.map((item) => (
                            <tr key={item.id} className="hover:bg-slate-800/20">
                              <td className="py-3 px-3 font-mono text-slate-400">{item.item_code}</td>
                              <td className="py-3 px-3 font-medium max-w-xs truncate" title={item.item_name}>
                                {item.item_name}
                              </td>
                              <td className="py-3 px-3 text-right font-mono">{formatINR(item.quantity)}</td>
                              <td className="py-3 px-3 text-slate-400">{item.unit || "NOS"}</td>
                              <td className="py-3 px-3 text-right font-mono">{formatINR(item.unit_rate)}</td>
                              <td className="py-3 px-3 text-right font-bold font-mono text-slate-200">{formatINR(item.amount)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Pagination */}
                    <div className="flex items-center justify-between pt-2 border-t border-slate-800/50 text-slate-500 text-[11px]">
                      <span>
                        Showing {Math.min((boqPage-1)*boqLimit + 1, filteredBOQ.length)} to {Math.min(boqPage*boqLimit, filteredBOQ.length)} of {filteredBOQ.length} items
                      </span>
                      <div className="flex items-center gap-1.5">
                        <button
                          disabled={boqPage === 1}
                          onClick={() => setBoqPage(p => p - 1)}
                          className="p-1.5 border border-slate-800 hover:border-slate-700 disabled:opacity-40 rounded-lg text-slate-400"
                        >
                          <ChevronLeft className="w-3.5 h-3.5" />
                        </button>
                        <span>{boqPage}</span>
                        <button
                          disabled={boqPage * boqLimit >= filteredBOQ.length}
                          onClick={() => setBoqPage(p => p + 1)}
                          className="p-1.5 border border-slate-800 hover:border-slate-700 disabled:opacity-40 rounded-lg text-slate-400"
                        >
                          <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: PROJECT MATCHING TAB */}
          {activeTab === "matching" && (
            <div className="space-y-6">
              {matchingResults.length === 0 ? (
                <div className="glass-panel rounded-3xl p-8 text-center text-slate-500 space-y-2">
                  <Layers className="w-10 h-10 mx-auto opacity-30 text-blue-500" />
                  <p className="text-sm">Semantic matching not run yet.</p>
                  <p className="text-xs text-slate-500">Click "Run Recommendation Engine" on the left to compute matches.</p>
                </div>
              ) : (
                <div className="space-y-6">
                  {matchingResults.map((result, idx) => (
                    <div key={idx} className="glass-panel rounded-3xl p-6 space-y-4">
                      <div className="border-b border-slate-800 pb-2">
                        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Eligibility Check rule</span>
                        <h4 className="text-sm font-semibold text-slate-200 mt-0.5 italic">
                          "{result.rule}"
                        </h4>
                      </div>

                      {result.matches.length === 0 ? (
                        <div className="text-xs text-rose-400 border border-rose-500/10 bg-rose-500/5 p-3 rounded-xl flex gap-2">
                          <XCircle className="w-4 h-4 shrink-0 mt-0.5" />
                          <span>No past capability matches found in the vector database. Technical matching score fails.</span>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest block">Matched Past Projects</span>
                          <div className="space-y-3">
                            {result.matches.map((match, matchIdx) => (
                              <div 
                                key={matchIdx} 
                                className={`p-4 border rounded-2xl flex flex-col md:flex-row items-center justify-between gap-4 transition ${
                                  match.eligible 
                                    ? "bg-slate-950/20 border-emerald-500/20 hover:border-emerald-500/40" 
                                    : "bg-slate-950/20 border-amber-500/20 hover:border-amber-500/40"
                                }`}
                              >
                                <div className="space-y-1">
                                  <div className="flex items-center gap-2">
                                    <span className="text-xs font-bold text-slate-200">{match.project.project_name}</span>
                                    <span className="text-[10px] text-slate-500">({match.project.client})</span>
                                  </div>
                                  <div className="flex flex-wrap items-center gap-3 text-[10px] text-slate-400 font-medium">
                                    <span>Value: ₹{formatINR(match.project.project_value)}</span>
                                    <span>•</span>
                                    <span>Date: {match.project.completion_date ? new Date(match.project.completion_date).toLocaleDateString() : "UNKNOWN"}</span>
                                    <span>•</span>
                                    <span>Domain: {match.project.domain}</span>
                                  </div>
                                  <div className="pt-2 text-[10.5px] text-slate-400">
                                    <span className="font-semibold text-slate-300">Explanation: </span>
                                    {match.reasons.join(", ")}
                                  </div>
                                </div>

                                <div className="text-right shrink-0">
                                  <span className={`inline-block text-xs font-extrabold px-2.5 py-1 rounded-lg border ${
                                    match.eligible 
                                      ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" 
                                      : "bg-amber-500/10 border-amber-500/30 text-amber-400"
                                  }`}>
                                    {Math.round(match.score * 100)}% Similarity
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 4: FINANCIAL QUALIFICATION TAB */}
          {activeTab === "financial" && (
            <div className="space-y-6">
              {!recommendation ? (
                <div className="glass-panel rounded-3xl p-8 text-center text-slate-500 space-y-2">
                  <DollarSign className="w-10 h-10 mx-auto opacity-30 text-emerald-500" />
                  <p className="text-sm">Financial validation results not computed yet.</p>
                  <p className="text-xs text-slate-500">Configure bidder parameters on the left and click "Run Recommendation Engine".</p>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Financial status summary card */}
                  <div className={`glass-panel rounded-3xl p-6 border-l-8 ${
                    recommendation.financial_qualification.qualified 
                      ? "border-l-emerald-500 bg-slate-950/20" 
                      : "border-l-rose-500 bg-slate-950/20"
                  } flex items-center justify-between`}>
                    <div>
                      <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Financial qualification</span>
                      <h4 className="text-lg font-black mt-1 flex items-center gap-2">
                        {recommendation.financial_qualification.qualified ? (
                          <>
                            <CheckCircle className="w-5 h-5 text-emerald-400" />
                            <span className="text-emerald-400">QUALIFIED</span>
                          </>
                        ) : (
                          <>
                            <XCircle className="w-5 h-5 text-rose-400" />
                            <span className="text-rose-400">DISQUALIFIED</span>
                          </>
                        )}
                      </h4>
                    </div>
                  </div>

                  {/* Turnover rule explanation */}
                  <div className="glass-panel rounded-3xl p-6 space-y-4">
                    <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Turnover Multiplier check</h4>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Bidder turnovers for the preceding 3 financial years must average at least <span className="font-semibold text-slate-200">150%</span> of the estimated tender value.
                    </p>

                    <div className="space-y-3 pt-2">
                      <div className="flex justify-between text-xs border-b border-slate-800 pb-2">
                        <span className="text-slate-400">Estimated Tender Value:</span>
                        <span className="font-mono text-slate-200">₹{formatINR(tender.tender_value)}</span>
                      </div>
                      <div className="flex justify-between text-xs border-b border-slate-800 pb-2">
                        <span className="text-slate-400">Required Minimum Average:</span>
                        <span className="font-mono text-slate-200">₹{formatINR(parseFloat(tender.tender_value || 0) * 1.5)}</span>
                      </div>
                      <div className="flex justify-between text-xs border-b border-slate-800 pb-2">
                        <span className="text-slate-400">Bidder Average Turnover:</span>
                        <span className={`font-mono font-semibold ${
                          recommendation.financial_qualification.qualified ? "text-emerald-400" : "text-rose-400"
                        }`}>
                          ₹{formatINR(recommendation.financial_qualification.average_turnover)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Net Worth check */}
                  <div className="glass-panel rounded-3xl p-6 space-y-3">
                    <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Net Worth check</h4>
                    <p className="text-xs text-slate-400">
                      The bidder must demonstrate a positive net worth in the current reporting period.
                    </p>
                    <div className="flex items-center justify-between text-xs p-3 bg-slate-950/20 border border-slate-800 rounded-xl mt-2">
                      <span className="text-slate-400">Bidder Declared Net Worth:</span>
                      <span className={`font-mono font-bold ${
                        parseFloat(bidderProfile.netWorth) > 0 ? "text-emerald-400" : "text-rose-400"
                      }`}>
                        ₹{formatINR(bidderProfile.netWorth)}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 5: COMPLIANCE RISK TAB */}
          {activeTab === "risk" && (
            <div className="space-y-6">
              {!riskAnalysis ? (
                <div className="glass-panel rounded-3xl p-8 text-center text-slate-500 space-y-2">
                  <ShieldAlert className="w-10 h-10 mx-auto opacity-30 text-rose-500" />
                  <p className="text-sm">Risk analysis results not parsed yet.</p>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Overall risk score badge */}
                  <div className={`glass-panel rounded-3xl p-6 border-l-8 ${
                    riskAnalysis.overall_risk_category === "LOW" ? "border-l-emerald-500 bg-slate-950/20 glow-go" :
                    riskAnalysis.overall_risk_category === "MEDIUM" ? "border-l-amber-500 bg-slate-950/20 glow-review" :
                    "border-l-rose-500 bg-slate-950/20 glow-nobid"
                  } flex items-center justify-between gap-4`}>
                    <div>
                      <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Compliance risk index</span>
                      <h4 className="text-lg font-black mt-1 flex items-center gap-2">
                        <span className={
                          riskAnalysis.overall_risk_category === "LOW" ? "text-emerald-400" :
                          riskAnalysis.overall_risk_category === "MEDIUM" ? "text-amber-400" :
                          "text-rose-400"
                        }>
                          {riskAnalysis.overall_risk_category} RISK
                        </span>
                        <span className="text-xs text-slate-500 font-normal">
                          (Score: {Math.round(riskAnalysis.overall_risk_score * 10)} / 100)
                        </span>
                      </h4>
                    </div>
                  </div>

                  {/* Risks detected list */}
                  <div className="space-y-4">
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Detected Risk Clauses</h4>
                    
                    {riskAnalysis.risks_detected.length === 0 ? (
                      <div className="text-xs text-slate-500 text-center py-6 border border-dashed border-slate-800 rounded-2xl">
                        No critical risk clauses extracted by compliance engine.
                      </div>
                    ) : (
                      riskAnalysis.risks_detected.map((risk, idx) => {
                        const sevColor = 
                          risk.severity === "HIGH" ? "text-rose-400 bg-rose-500/10 border-rose-500/20" :
                          risk.severity === "MEDIUM" ? "text-amber-400 bg-amber-500/10 border-amber-500/20" :
                          "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";

                        return (
                          <div key={idx} className="glass-panel rounded-3xl p-6 space-y-3">
                            <div className="flex items-center justify-between border-b border-slate-850 pb-2">
                              <h5 className="text-xs font-bold text-slate-200">{risk.risk_name}</h5>
                              <span className={`inline-flex items-center px-2 py-0.5 rounded-lg text-[10px] font-bold border ${sevColor}`}>
                                {risk.severity} severity
                              </span>
                            </div>
                            {risk.evidence && (
                              <div className="text-xs text-slate-400 leading-relaxed p-3 bg-slate-950/40 border border-slate-900 rounded-2xl italic">
                                <span className="font-semibold text-slate-300 not-italic block mb-1">Contract Evidence:</span>
                                "{risk.evidence}"
                              </div>
                            )}
                            {risk.recommendation && (
                              <div className="text-xs text-slate-400">
                                <span className="font-semibold text-emerald-400 block mb-1">Mitigation Recommendation:</span>
                                {risk.recommendation}
                              </div>
                            )}
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

        </div>

      </div>

    </div>
  );
}
