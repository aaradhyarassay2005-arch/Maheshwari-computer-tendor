"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { 
  ClipboardCheck, 
  Search, 
  Loader2,
  Building,
  Clock,
  ArrowRight,
  ShieldAlert,
  Inbox,
  AlertCircle
} from "lucide-react";

export default function ReviewQueue() {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchQueue() {
      setLoading(true);
      setError("");
      try {
        const data = await api.getReviewQueue();
        setQueue(data || []);
      } catch (err) {
        console.error("Failed to load review queue", err);
        setError("Could not retrieve review queue. Please verify backend connectivity.");
      } finally {
        setLoading(false);
      }
    }
    fetchQueue();
  }, []);

  const filteredQueue = queue.filter(item => 
    item.tender_number.toLowerCase().includes(search.toLowerCase()) ||
    item.department.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <ClipboardCheck className="w-6 h-6 text-indigo-500" />
            Human Review Ingestion Board
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Review and correct extracted tender parameters before approving them for downstream bid engines.
          </p>
        </div>
        
        {/* Count Pill */}
        <div className="flex items-center gap-2 border border-indigo-500/20 bg-indigo-500/10 px-4 py-2 rounded-2xl">
          <AlertCircle className="w-4 h-4 text-indigo-400" />
          <span className="text-xs font-semibold text-indigo-300">
            {queue.length} Pending Verification
          </span>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Card 1 */}
        <div className="glass-panel rounded-2xl p-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <Inbox className="w-6 h-6" />
          </div>
          <div>
            <span className="block text-[10px] uppercase font-bold text-slate-500 tracking-wider">Queue Workload</span>
            <span className="text-xl font-bold text-slate-200">{queue.length} Tenders</span>
          </div>
        </div>

        {/* Card 2 */}
        <div className="glass-panel rounded-2xl p-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <span className="block text-[10px] uppercase font-bold text-slate-500 tracking-wider">Verification Scope</span>
            <span className="text-xl font-bold text-slate-200">10 Critical Fields</span>
          </div>
        </div>

        {/* Card 3 */}
        <div className="glass-panel rounded-2xl p-5 flex items-center gap-4 sm:col-span-2 lg:col-span-1">
          <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <span className="block text-[10px] uppercase font-bold text-slate-500 tracking-wider">Pipeline Flow</span>
            <span className="text-xl font-bold text-slate-200">Continuous Ingestion</span>
          </div>
        </div>
      </div>

      {/* Main Content Container */}
      <div className="glass-panel rounded-3xl p-6 space-y-6">
        {/* Search Panel */}
        <div className="relative max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search queue by tender or department..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-slate-950/80 border border-slate-800 focus:border-indigo-500 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-100 outline-none transition"
          />
        </div>

        {/* Ingestion Table */}
        {loading ? (
          <div className="py-24 flex flex-col items-center justify-center text-slate-400">
            <Loader2 className="w-10 h-10 text-indigo-500 animate-spin mb-3" />
            <span className="text-sm font-medium">Retrieving verification queue...</span>
          </div>
        ) : error ? (
          <div className="py-16 text-center border border-slate-800/80 rounded-2xl bg-rose-500/5 text-rose-400 px-4">
            <AlertCircle className="w-12 h-12 mx-auto mb-3 text-rose-500 opacity-60" />
            <p className="text-sm font-medium">{error}</p>
          </div>
        ) : filteredQueue.length === 0 ? (
          <div className="py-24 text-center border border-dashed border-slate-800 rounded-2xl bg-slate-950/10 text-slate-500">
            <Inbox className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">
              {search ? "No items match your search term." : "No tenders pending human review."}
            </p>
            {!search && (
              <p className="text-xs text-slate-600 mt-1">
                Upload new tenders to populate the ingestion verification board.
              </p>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm border-collapse">
              <thead>
                <tr className="border-b border-slate-800/80 text-slate-400 text-xs font-semibold uppercase tracking-wider">
                  <th className="py-3.5 px-4">Tender Number</th>
                  <th className="py-3.5 px-4">Department</th>
                  <th className="py-3.5 px-4 text-right">Value (INR)</th>
                  <th className="py-3.5 px-4">Ingested At</th>
                  <th className="py-3.5 px-4 text-center">Extraction Status</th>
                  <th className="py-3.5 px-4"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {filteredQueue.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-800/30 transition-colors group">
                    <td className="py-4.5 px-4 font-mono font-medium text-slate-300">
                      {item.tender_number}
                    </td>
                    <td className="py-4.5 px-4 text-slate-400">
                      <span className="flex items-center gap-2">
                        <Building className="w-4 h-4 text-slate-600" />
                        {item.department}
                      </span>
                    </td>
                    <td className="py-4.5 px-4 text-right font-medium text-slate-200 font-mono">
                      {item.tender_value ? parseInt(item.tender_value).toLocaleString("en-IN") : "UNKNOWN"}
                    </td>
                    <td className="py-4.5 px-4 text-slate-400">
                      {new Date(item.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-4.5 px-4 text-center">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border text-indigo-400 bg-indigo-500/10 border-indigo-500/20">
                        {item.status}
                      </span>
                    </td>
                    <td className="py-4.5 px-4 text-right">
                      <Link
                        href={`/tenders/${item.id}?review=true`}
                        className="inline-flex items-center justify-center px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-bold text-white transition gap-1.5 shadow-lg shadow-indigo-600/10 hover:shadow-indigo-500/20"
                      >
                        Begin Review
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
