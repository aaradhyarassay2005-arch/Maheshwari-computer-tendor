"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { 
  Search, 
  ArrowUpDown, 
  ChevronLeft, 
  ChevronRight, 
  Loader2,
  FileText,
  Building,
  SlidersHorizontal,
  ChevronDown,
  Percent,
  Database
} from "lucide-react";

export default function TendersList() {
  const [tenders, setTenders] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  
  // Search & Filter state
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [deptFilter, setDeptFilter] = useState("ALL");
  
  // Pagination
  const [page, setPage] = useState(1);
  const limit = 15;

  // Sorting
  const [sortField, setSortField] = useState("created_at");
  const [sortOrder, setSortOrder] = useState("desc");

  // Bidder profile synced via localStorage
  const [bidderProfile, setBidderProfile] = useState({
    turnovers: [150000000, 180000000, 220000000],
    netWorth: 80000000,
    eligibilityRules: ["Must have executed 1 railway signaling project of 50M INR"]
  });

  // Cached recommendation status
  const [recs, setRecs] = useState({});
  const [recsLoading, setRecsLoading] = useState(false);

  // Load bidder profile from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem("tender_bidder_profile");
    if (saved) {
      try {
        setBidderProfile(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to parse saved bidder profile", e);
      }
    }
  }, []);

  // Debounce search query
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 400);
    return () => clearTimeout(handler);
  }, [search]);

  // Fetch Tenders
  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const skip = (page - 1) * limit;
        const data = await api.getTenders(skip, limit, debouncedSearch);
        setTenders(data.items || []);
        setTotal(data.total || 0);
      } catch (err) {
        console.error("Failed to fetch tenders", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [debouncedSearch, page]);

  // Evaluate recommendations
  useEffect(() => {
    async function evaluateVisible() {
      const completed = tenders.filter(t => t.status === "PARSED" || t.status === "APPROVED" || t.status === "REJECTED");
      if (completed.length === 0) return;

      setRecsLoading(true);
      const updatedRecs = { ...recs };
      let changed = false;

      for (const tender of completed) {
        const cacheKey = `${tender.id}_${JSON.stringify(bidderProfile)}`;
        if (updatedRecs[tender.id] && updatedRecs[tender.id].cacheKey === cacheKey) {
          continue;
        }

        try {
          const res = await api.getRecommendation(
            tender.id,
            bidderProfile.turnovers,
            bidderProfile.netWorth,
            bidderProfile.eligibilityRules
          );
          updatedRecs[tender.id] = {
            recommendation: res.bid_recommendation,
            win_probability: res.win_probability,
            cacheKey: cacheKey
          };
          changed = true;
        } catch (e) {
          console.error(e);
          updatedRecs[tender.id] = { recommendation: "ERROR", win_probability: 0, cacheKey };
          changed = true;
        }
      }

      if (changed) {
        setRecs(updatedRecs);
      }
      setRecsLoading(false);
    }
    
    if (tenders.length > 0) {
      evaluateVisible();
    }
  }, [tenders, bidderProfile]);

  // Unique departments for filter dropdown
  const departments = ["ALL", ...new Set(tenders.map(t => t.department))];

  // Client-side filtering & sorting
  const getProcessedTenders = () => {
    let result = [...tenders];

    if (deptFilter !== "ALL") {
      result = result.filter(t => t.department === deptFilter);
    }

    if (statusFilter !== "ALL") {
      result = result.filter(t => {
        const rec = recs[t.id]?.recommendation;
        return rec === statusFilter;
      });
    }

    result.sort((a, b) => {
      let valA, valB;

      if (sortField === "tender_value") {
        valA = a.tender_value ? parseFloat(a.tender_value) : 0;
        valB = b.tender_value ? parseFloat(b.tender_value) : 0;
      } else if (sortField === "closing_date") {
        valA = a.closing_date ? new Date(a.closing_date).getTime() : 0;
        valB = b.closing_date ? new Date(b.closing_date).getTime() : 0;
      } else if (sortField === "win_probability") {
        valA = recs[a.id]?.win_probability || 0;
        valB = recs[b.id]?.win_probability || 0;
      } else {
        valA = new Date(a.created_at).getTime();
        valB = new Date(b.created_at).getTime();
      }

      if (sortOrder === "asc") {
        return valA > valB ? 1 : -1;
      } else {
        return valA < valB ? 1 : -1;
      }
    });

    return result;
  };

  const processedTenders = getProcessedTenders();

  const handleSort = (field) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white bg-gradient-to-r from-indigo-400 to-slate-200 bg-clip-text text-transparent">
            Tender Explorer
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Search, sort, filter and execute criteria matches against active railway and government tenders.
          </p>
        </div>
      </div>

      {/* Filters & Control Panel */}
      <div className="glass-panel rounded-2xl p-4 shadow-xl">
        <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
          {/* Search bar */}
          <div className="w-full md:max-w-md relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search by tender ID, keywords, core scopes..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-slate-950/60 border border-slate-800 focus:border-indigo-500 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-200 outline-none transition-all duration-200 focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          {/* Selector filters */}
          <div className="w-full md:w-auto flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5 bg-slate-950/50 border border-slate-800 rounded-xl px-2.5 py-1.5 shrink-0">
              <SlidersHorizontal className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Filters:</span>
            </div>
            
            {/* Department */}
            <div className="relative">
              <select
                value={deptFilter}
                onChange={(e) => setDeptFilter(e.target.value)}
                className="appearance-none bg-slate-900 border border-slate-800 hover:border-slate-700 focus:border-indigo-500 rounded-xl pl-3 pr-8 py-1.5 text-xs text-slate-300 outline-none transition cursor-pointer"
              >
                <option value="ALL">All Departments</option>
                {departments.filter(d => d !== "ALL").map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>

            {/* Recommendations */}
            <div className="relative">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="appearance-none bg-slate-900 border border-slate-800 hover:border-slate-700 focus:border-indigo-500 rounded-xl pl-3 pr-8 py-1.5 text-xs text-slate-300 outline-none transition cursor-pointer"
              >
                <option value="ALL">All Recommendations</option>
                <option value="GO">GO Recommendations</option>
                <option value="REVIEW">REVIEW Flagged</option>
                <option value="NO_BID">NO BID Classifications</option>
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>
        </div>
      </div>

      {/* Main Table Ledger */}
      <div className="glass-panel rounded-2xl p-5 shadow-2xl overflow-hidden">
        {loading ? (
          <div className="py-24 flex flex-col items-center justify-center text-slate-400">
            <Loader2 className="w-8 h-8 text-indigo-500 animate-spin mb-3" />
            <span className="text-xs font-semibold">Loading tender repository...</span>
          </div>
        ) : processedTenders.length === 0 ? (
          <div className="py-20 text-center border border-dashed border-slate-800 rounded-2xl bg-slate-950/20 text-slate-500">
            <FileText className="w-10 h-10 mx-auto mb-3 opacity-30 text-indigo-500" />
            <p className="text-xs font-medium">No tenders matching active filter criteria.</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-800/80 text-slate-400 text-[10px] font-bold uppercase tracking-wider">
                    <th className="py-3 px-4">Tender Number</th>
                    <th className="py-3 px-4">Department</th>
                    <th 
                      onClick={() => handleSort("tender_value")}
                      className="py-3 px-4 text-right cursor-pointer hover:text-indigo-400 transition"
                    >
                      <div className="flex items-center justify-end gap-1">
                        Value (INR)
                        <ArrowUpDown className="w-3 h-3 text-slate-500" />
                      </div>
                    </th>
                    <th 
                      onClick={() => handleSort("closing_date")}
                      className="py-3 px-4 cursor-pointer hover:text-indigo-400 transition"
                    >
                      <div className="flex items-center gap-1">
                        Closing Date
                        <ArrowUpDown className="w-3 h-3 text-slate-500" />
                      </div>
                    </th>
                    <th className="py-3 px-4 text-center">Parsing Status</th>
                    <th 
                      onClick={() => handleSort("win_probability")}
                      className="py-3 px-4 text-center cursor-pointer hover:text-indigo-400 transition"
                    >
                      <div className="flex items-center justify-center gap-1">
                        Bidding Recommendation
                        <ArrowUpDown className="w-3 h-3 text-slate-500" />
                      </div>
                    </th>
                    <th className="py-3 px-4"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40">
                  {processedTenders.map((tender) => {
                    const recInfo = recs[tender.id];
                    const statusGlowClass = 
                      tender.status === "APPROVED" ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" :
                      tender.status === "REJECTED" ? "text-rose-400 bg-rose-500/10 border-rose-500/20" :
                      tender.status === "PARSED" ? "text-amber-400 bg-amber-500/10 border-amber-500/20" :
                      tender.status === "FAILED" ? "text-rose-500 bg-rose-500/10 border-rose-500/20" :
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
                          <span className="flex items-center gap-2">
                            <Building className="w-3.5 h-3.5 text-slate-600" />
                            {tender.department}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-right font-semibold text-slate-200 font-mono">
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
                          {!(tender.status === "PARSED" || tender.status === "APPROVED" || tender.status === "REJECTED") ? (
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
                              <Loader2 className="w-3 h-3 animate-spin" />
                              Evaluating...
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <Link
                            key={tender.id}
                            href={`/tenders/${tender.id}`}
                            className="inline-flex items-center justify-center px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-indigo-500/30 hover:bg-slate-850 text-[10px] font-bold text-indigo-400 hover:text-indigo-300 transition-all gap-1"
                          >
                            Analyze
                            <ChevronRight className="w-3.5 h-3.5" />
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <div className="flex items-center justify-between border-t border-slate-800/80 pt-4 text-xs text-slate-400">
              <span>
                Showing <span className="font-semibold text-slate-200 font-mono">{(page-1)*limit + 1}</span> to{" "}
                <span className="font-semibold text-slate-200 font-mono">{Math.min(page*limit, total)}</span> of{" "}
                <span className="font-semibold text-slate-200 font-mono">{total}</span> entries
              </span>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(p => Math.max(p - 1, 1))}
                  disabled={page === 1}
                  className="p-1.5 border border-slate-800 rounded-lg hover:bg-slate-900 text-slate-400 hover:text-slate-200 disabled:opacity-40 disabled:hover:bg-transparent transition cursor-pointer"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="px-2 font-semibold text-slate-350 font-mono">Page {page}</span>
                <button
                  onClick={() => setPage(p => (p * limit < total ? p + 1 : p))}
                  disabled={page * limit >= total}
                  className="p-1.5 border border-slate-800 rounded-lg hover:bg-slate-900 text-slate-400 hover:text-slate-200 disabled:opacity-40 disabled:hover:bg-transparent transition cursor-pointer"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
