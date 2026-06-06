"use client";

import React, { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { 
  ShieldAlert, 
  Search, 
  Loader2, 
  RefreshCw, 
  SlidersHorizontal,
  Calendar,
  User,
  ChevronLeft,
  ChevronRight,
  Eye,
  Info
} from "lucide-react";

export default function AuditLogsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const limit = 15;

  // Search/Filters states
  const [searchAction, setSearchAction] = useState("");
  const [searchUser, setSearchUser] = useState("");
  const [resourceType, setResourceType] = useState("");
  const [expandedLogId, setExpandedLogId] = useState(null);

  // Authenticated user check
  const [currentUser, setCurrentUser] = useState(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const userStr = localStorage.getItem("user");
      if (userStr) {
        const user = JSON.parse(userStr);
        setCurrentUser(user);
        if (user.role !== "ADMIN" && user.role !== "SUPER_ADMIN") {
          window.location.href = "/";
        }
      }
    }
  }, []);

  const fetchAuditLogs = useCallback(async () => {
    if (!currentUser) return;
    setLoading(true);
    setError("");
    try {
      const skip = (page - 1) * limit;
      const logsRes = await api.getAuditLogs(skip, limit, searchAction, searchUser, resourceType);
      setLogs(logsRes || []);
      // Approximate total for pagination if not provided explicitly by the mock/db
      setTotal(logsRes ? logsRes.length + (logsRes.length === limit ? limit : 0) : 0);
    } catch (err) {
      setError(err.message || "Failed to retrieve security audit logs");
    } finally {
      setLoading(false);
    }
  }, [page, searchAction, searchUser, resourceType, currentUser]);

  useEffect(() => {
    fetchAuditLogs();
  }, [fetchAuditLogs]);

  const formatChangeDiff = (diffStr) => {
    if (!diffStr) return <span className="text-slate-500 italic">No structural modifications</span>;
    try {
      const diffObj = JSON.parse(diffStr);
      return (
        <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-850 font-mono text-[10.5px] text-slate-350 space-y-1.5 max-w-full overflow-x-auto">
          {Object.entries(diffObj).map(([key, val]) => (
            <div key={key} className="flex flex-wrap gap-1.5 border-b border-slate-900/60 py-1 last:border-b-0">
              <span className="text-indigo-400 font-bold">{key}:</span>
              {typeof val === "object" && val !== null ? (
                <div className="w-full pl-3 space-y-0.5 mt-0.5">
                  {val.old_role || val.old_status !== undefined || val.old_value !== undefined ? (
                    <>
                      <div className="text-rose-400 font-semibold">- {String(val.old_role || val.old_status || val.old_value)}</div>
                      <div className="text-emerald-400 font-semibold">+ {String(val.new_role || val.new_status || val.new_value)}</div>
                    </>
                  ) : (
                    <pre className="text-[9.5px] text-slate-500">{JSON.stringify(val, null, 2)}</pre>
                  )}
                </div>
              ) : (
                <span className="font-semibold text-slate-200">{String(val)}</span>
              )}
            </div>
          ))}
        </div>
      );
    } catch (_) {
      return <pre className="text-[10px] font-mono whitespace-pre-wrap text-slate-400 bg-slate-950/40 p-3 rounded-lg border border-slate-850">{diffStr}</pre>;
    }
  };

  if (!currentUser) {
    return (
      <div className="flex justify-center items-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white bg-gradient-to-r from-indigo-400 to-slate-200 bg-clip-text text-transparent flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-indigo-500" />
            Security Audit Trail
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Browse global system state edits, operator authentication records, database mutations, and metadata overrides.
          </p>
        </div>
        <button 
          onClick={fetchAuditLogs}
          disabled={loading}
          className="flex items-center justify-center p-2.5 rounded-xl bg-slate-900 border border-slate-850 hover:bg-slate-800 text-slate-350 transition-all cursor-pointer shadow-sm"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-indigo-400" : ""}`} />
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-semibold">
          {error}
        </div>
      )}

      {/* Query Filters */}
      <div className="glass-panel rounded-2xl p-4 shadow-xl">
        <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                value={searchAction}
                onChange={(e) => setSearchAction(e.target.value)}
                placeholder="Action (e.g. USER_LOGIN)..."
                className="w-full bg-slate-950/60 border border-slate-800 focus:border-indigo-500 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-200 outline-none transition"
              />
            </div>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                value={searchUser}
                onChange={(e) => setSearchUser(e.target.value)}
                placeholder="User ID / Operator UUID..."
                className="w-full bg-slate-950/60 border border-slate-800 focus:border-indigo-500 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-200 outline-none transition"
              />
            </div>
            <div className="relative">
              <SlidersHorizontal className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                value={resourceType}
                onChange={(e) => setResourceType(e.target.value)}
                placeholder="Resource (e.g. TENDER)..."
                className="w-full bg-slate-950/60 border border-slate-800 focus:border-indigo-500 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-200 outline-none transition"
              />
            </div>
          </div>
          <button
            onClick={() => { setPage(1); fetchAuditLogs(); }}
            className="w-full md:w-auto px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-bold text-white transition-all shadow-md shadow-indigo-600/20"
          >
            Apply Filters
          </button>
        </div>
      </div>

      {/* Audit table */}
      <div className="glass-panel rounded-2xl p-5 shadow-2xl overflow-hidden">
        {loading ? (
          <div className="py-24 flex flex-col items-center justify-center text-slate-400">
            <Loader2 className="w-8 h-8 text-indigo-500 animate-spin mb-3" />
            <span className="text-xs font-semibold">Retrieving system ledger...</span>
          </div>
        ) : logs.length === 0 ? (
          <div className="py-16 text-center border border-dashed border-slate-800 rounded-2xl bg-slate-950/25 text-slate-500">
            <ShieldAlert className="w-9 h-9 mx-auto mb-3 opacity-30 text-indigo-500" />
            <p className="text-xs font-medium">No security logs matching search parameters.</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-800/80 text-slate-400 text-[10px] font-bold uppercase tracking-wider">
                    <th className="py-3 px-4">Timestamp</th>
                    <th className="py-3 px-4">Action</th>
                    <th className="py-3 px-4">Operator UUID</th>
                    <th className="py-3 px-4">Role</th>
                    <th className="py-3 px-4">IP Footprint</th>
                    <th className="py-3 px-4 text-center">Change Diff</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40">
                  {logs.map((log) => {
                    const isExpanded = expandedLogId === log.id;
                    return (
                      <React.Fragment key={log.id}>
                        <tr 
                          onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                          className={`hover:bg-slate-800/20 transition-all cursor-pointer ${
                            isExpanded ? "bg-slate-900/35" : ""
                          }`}
                        >
                          <td className="py-3.5 px-4 text-slate-450 font-mono font-medium">
                            {new Date(log.timestamp).toLocaleString()}
                          </td>
                          <td className="py-3.5 px-4 text-slate-200 font-bold font-mono">
                            {log.action}
                          </td>
                          <td className="py-3.5 px-4 text-slate-400 font-mono">
                            {log.user_id ? log.user_id : "System Agent"}
                          </td>
                          <td className="py-3.5 px-4">
                            {log.user_role ? (
                              <span className="px-2 py-0.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[9px] font-bold">
                                {log.user_role}
                              </span>
                            ) : (
                              <span className="text-slate-600">—</span>
                            )}
                          </td>
                          <td className="py-3.5 px-4 text-slate-450 font-mono">
                            {log.ip_address || "localhost"}
                          </td>
                          <td className="py-3.5 px-4 text-center">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setExpandedLogId(isExpanded ? null : log.id);
                              }}
                              className="px-2.5 py-1 rounded bg-slate-950 hover:bg-slate-900 border border-slate-800 text-[9px] font-bold text-slate-400 hover:text-slate-200 transition-colors"
                            >
                              {isExpanded ? "Close Panel" : "Inspect Diff"}
                            </button>
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr className="bg-slate-950/40">
                            <td colSpan={6} className="py-4 px-6 border-b border-slate-800/60">
                              <div className="space-y-4 max-w-4xl">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-medium">
                                  <div>
                                    <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest">Resource Domain:</span>
                                    <span className="text-slate-350 font-mono mt-0.5 block">{log.resource_type}</span>
                                  </div>
                                  <div>
                                    <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest">Resource Target UUID:</span>
                                    <span className="text-slate-350 font-mono mt-0.5 block break-all">{log.resource_id || "None"}</span>
                                  </div>
                                  <div className="md:col-span-2">
                                    <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest">User Agent Header:</span>
                                    <span className="text-slate-400 font-sans mt-0.5 block text-[10px]">{log.client_agent || "No metadata recorded"}</span>
                                  </div>
                                </div>
                                <div className="space-y-2">
                                  <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest">JSON Change Diff:</span>
                                  {formatChangeDiff(log.change_diff)}
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <div className="flex items-center justify-between border-t border-slate-800/80 pt-4 text-xs text-slate-400">
              <span>
                Showing Page <span className="font-semibold text-slate-200 font-mono">{page}</span>
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
                  onClick={() => setPage(p => p + 1)}
                  disabled={logs.length < limit}
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
