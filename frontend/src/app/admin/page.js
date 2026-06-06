"use client";

import React, { useState, useEffect, useCallback } from "react";
import { 
  Shield, 
  Activity, 
  Users, 
  Terminal, 
  Search, 
  Database, 
  Cpu, 
  TrendingUp, 
  Loader2, 
  RefreshCw, 
  AlertTriangle, 
  Trash2,
  Calendar,
  CheckCircle,
  Eye
} from "lucide-react";
import { 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  LineChart, 
  Line, 
  CartesianGrid 
} from "recharts";
import { api } from "@/lib/api";

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState("overview"); // overview, users, audits
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [stats, setStats] = useState(null);
  const [health, setHealth] = useState(null);
  const [telemetry, setTelemetry] = useState(null);
  const [recentLogs, setRecentLogs] = useState([]);

  // Users Tab state
  const [users, setUsers] = useState([]);
  const [userSearch, setUserSearch] = useState("");
  const [userRoleFilter, setUserRoleFilter] = useState("");
  const [selectedUserDetail, setSelectedUserDetail] = useState(null);
  const [userDetailLoading, setUserDetailLoading] = useState(false);

  // Audits Tab state
  const [auditLogs, setAuditLogs] = useState([]);
  const [expandedLogId, setExpandedLogId] = useState(null);
  const [auditSearchAction, setAuditSearchAction] = useState("");
  const [auditSearchUser, setAuditSearchUser] = useState("");

  // Check role client-side
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

  // Fetch functions
  const fetchOverviewData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [statsRes, healthRes, telemetryRes, logsRes] = await Promise.all([
        api.getPlatformStats(),
        api.getSystemHealth(),
        api.getApiUsageTelemetry(),
        api.getAuditLogs(0, 10)
      ]);
      setStats(statsRes);
      setHealth(healthRes);
      setTelemetry(telemetryRes);
      setRecentLogs(logsRes);
    } catch (err) {
      setError(err.message || "Failed to load telemetry stats");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const usersRes = await api.getUsers(0, 100, userSearch, userRoleFilter);
      setUsers(usersRes);
    } catch (err) {
      setError(err.message || "Failed to retrieve user directory");
    } finally {
      setLoading(false);
    }
  }, [userSearch, userRoleFilter]);

  const fetchAuditLogs = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const logsRes = await api.getAuditLogs(0, 100, auditSearchAction, auditSearchUser);
      setAuditLogs(logsRes);
    } catch (err) {
      setError(err.message || "Failed to fetch audit log trail");
    } finally {
      setLoading(false);
    }
  }, [auditSearchAction, auditSearchUser]);

  useEffect(() => {
    if (currentUser) {
      if (activeTab === "overview") fetchOverviewData();
      if (activeTab === "users") fetchUsers();
      if (activeTab === "audits") fetchAuditLogs();
    }
  }, [activeTab, currentUser, fetchOverviewData, fetchUsers, fetchAuditLogs]);

  // Actions
  const handleUpdateRole = async (userId, role) => {
    try {
      await api.updateUserRole(userId, role);
      fetchUsers();
      if (selectedUserDetail && selectedUserDetail.id === userId) {
        viewUserDetail(userId);
      }
    } catch (err) {
      alert(err.message || "Failed to update role");
    }
  };

  const handleToggleStatus = async (userId, currentStatus) => {
    try {
      await api.updateUserStatus(userId, !currentStatus);
      fetchUsers();
      if (selectedUserDetail && selectedUserDetail.id === userId) {
        viewUserDetail(userId);
      }
    } catch (err) {
      alert(err.message || "Failed to update account status");
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!confirm("Are you sure you want to permanently delete this user?")) return;
    try {
      await api.deleteUser(userId);
      fetchUsers();
      setSelectedUserDetail(null);
    } catch (err) {
      alert(err.message || "Failed to delete user");
    }
  };

  const viewUserDetail = async (userId) => {
    setUserDetailLoading(true);
    try {
      const detail = await api.getUser(userId);
      setSelectedUserDetail(detail);
    } catch (err) {
      alert("Failed to load user details");
    } finally {
      setUserDetailLoading(false);
    }
  };

  // Render helpers
  const formatChangeDiff = (diffStr) => {
    if (!diffStr) return <span className="text-slate-500 italic">No structural modifications</span>;
    try {
      const diffObj = JSON.parse(diffStr);
      return (
        <div className="bg-slate-950/60 p-3 rounded-lg border border-border-dark font-mono text-[11px] text-slate-300 space-y-1 max-w-full overflow-x-auto">
          {Object.entries(diffObj).map(([key, val]) => (
            <div key={key} className="flex flex-wrap gap-1.5 border-b border-border-dark/50 py-1 last:border-b-0">
              <span className="text-blue-400 font-bold">{key}:</span>
              {typeof val === "object" && val !== null ? (
                <div className="w-full pl-3 space-y-0.5">
                  {val.old_role || val.old_status !== undefined ? (
                    <>
                      <div className="text-rose-400">- {String(val.old_role || val.old_status)}</div>
                      <div className="text-emerald-400">+ {String(val.new_role || val.new_status)}</div>
                    </>
                  ) : (
                    <pre className="text-[10px] text-slate-400">{JSON.stringify(val, null, 2)}</pre>
                  )}
                </div>
              ) : (
                <span>{String(val)}</span>
              )}
            </div>
          ))}
        </div>
      );
    } catch (_) {
      return <pre className="text-[10px] font-mono whitespace-pre-wrap">{diffStr}</pre>;
    }
  };

  if (!currentUser) {
    return (
      <div className="flex justify-center items-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Console Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border-dark pb-5">
        <div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-indigo-200 bg-clip-text text-transparent flex items-center gap-2">
            <Shield className="w-7 h-7 text-blue-500" />
            Super Admin Control Center
          </h1>
          <p className="text-slate-400 text-xs mt-1">
            Global directory, platform telemetry diagnostics, and security audit logs.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={() => {
              if (activeTab === "overview") fetchOverviewData();
              if (activeTab === "users") fetchUsers();
              if (activeTab === "audits") fetchAuditLogs();
            }}
            disabled={loading}
            className="flex items-center justify-center p-2.5 rounded-xl bg-slate-900 border border-border-dark hover:bg-slate-800 text-slate-300 transition-all cursor-pointer"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-blue-400" : ""}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-semibold flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Tab Selectors */}
      <div className="flex border-b border-border-dark gap-2">
        <button
          onClick={() => setActiveTab("overview")}
          className={`px-5 py-3 text-sm font-semibold transition-all border-b-2 cursor-pointer flex items-center gap-2 ${
            activeTab === "overview"
              ? "border-blue-500 text-blue-400 bg-blue-600/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Activity className="w-4 h-4" /> Telemetry & Health
        </button>
        <button
          onClick={() => setActiveTab("users")}
          className={`px-5 py-3 text-sm font-semibold transition-all border-b-2 cursor-pointer flex items-center gap-2 ${
            activeTab === "users"
              ? "border-blue-500 text-blue-400 bg-blue-600/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Users className="w-4 h-4" /> User Directory
        </button>
        <button
          onClick={() => setActiveTab("audits")}
          className={`px-5 py-3 text-sm font-semibold transition-all border-b-2 cursor-pointer flex items-center gap-2 ${
            activeTab === "audits"
              ? "border-blue-500 text-blue-400 bg-blue-600/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Terminal className="w-4 h-4" /> Security Audit Logs
        </button>
      </div>

      {/* Overview Tab Content */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Health Diagnostics Indicator */}
          {health && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="glass-panel p-5 rounded-2xl border border-border-dark flex items-center gap-4">
                <div className="p-3 rounded-xl bg-slate-900 border border-border-dark text-slate-300">
                  <Database className="w-5 h-5" />
                </div>
                <div>
                  <span className="block text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
                    Postgres DB
                  </span>
                  <span className="flex items-center gap-1.5 mt-0.5">
                    <span className={`w-2 h-2 rounded-full ${
                      health.postgres_status === "HEALTHY" ? "bg-emerald-500 animate-pulse" : "bg-rose-500"
                    }`} />
                    <span className="text-sm font-bold text-slate-200">
                      {health.postgres_status === "HEALTHY" ? "Online" : "Degraded"}
                    </span>
                  </span>
                </div>
              </div>

              <div className="glass-panel p-5 rounded-2xl border border-border-dark flex items-center gap-4">
                <div className="p-3 rounded-xl bg-slate-900 border border-border-dark text-slate-300">
                  <TrendingUp className="w-5 h-5" />
                </div>
                <div>
                  <span className="block text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
                    Qdrant Vector DB
                  </span>
                  <span className="flex items-center gap-1.5 mt-0.5">
                    <span className={`w-2 h-2 rounded-full ${
                      health.qdrant_status === "HEALTHY" ? "bg-emerald-500 animate-pulse" : "bg-rose-500"
                    }`} />
                    <span className="text-sm font-bold text-slate-200">
                      {health.qdrant_status === "HEALTHY" ? "Online" : "Degraded"}
                    </span>
                  </span>
                </div>
              </div>

              <div className="glass-panel p-5 rounded-2xl border border-border-dark flex items-center gap-4">
                <div className="p-3 rounded-xl bg-slate-900 border border-border-dark text-slate-300">
                  <Cpu className="w-5 h-5" />
                </div>
                <div>
                  <span className="block text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
                    CPU Workload
                  </span>
                  <span className="block text-sm font-bold text-slate-200 mt-0.5">
                    {health.cpu_percent}%
                  </span>
                </div>
              </div>

              <div className="glass-panel p-5 rounded-2xl border border-border-dark flex items-center gap-4">
                <div className="p-3 rounded-xl bg-slate-900 border border-border-dark text-slate-300">
                  <Activity className="w-5 h-5" />
                </div>
                <div>
                  <span className="block text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
                    System RAM
                  </span>
                  <span className="block text-sm font-bold text-slate-200 mt-0.5">
                    {health.ram_percent}% <span className="text-[10px] text-slate-500">({health.ram_used_gb}/{health.ram_total_gb} GB)</span>
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Stats KPI widgets */}
          {stats && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-5 rounded-2xl bg-slate-900/60 border border-border-dark">
                <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Total Users</span>
                <span className="text-2xl font-bold text-slate-100">{stats.total_users}</span>
              </div>
              <div className="p-5 rounded-2xl bg-slate-900/60 border border-border-dark">
                <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Active Sessions</span>
                <span className="text-2xl font-bold text-slate-100">{stats.active_sessions}</span>
              </div>
              <div className="p-5 rounded-2xl bg-slate-900/60 border border-border-dark">
                <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Audits Count</span>
                <span className="text-2xl font-bold text-slate-100">{stats.total_audit_logs}</span>
              </div>
              <div className="p-5 rounded-2xl bg-slate-900/60 border border-border-dark">
                <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Tenders Count</span>
                <span className="text-2xl font-bold text-slate-100">{stats.total_tenders}</span>
              </div>
            </div>
          )}

          {/* API Charts */}
          {telemetry && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="glass-panel p-6 rounded-2xl border border-border-dark">
                <h3 className="text-sm font-bold text-slate-200 mb-4 uppercase tracking-wider">
                  Top Operations Frequency (Hits)
                </h3>
                <div className="h-64">
                  {telemetry.most_active_actions && telemetry.most_active_actions.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={telemetry.most_active_actions} layout="vertical">
                        <XAxis type="number" stroke="#64748b" fontSize={11} />
                        <YAxis dataKey="action" type="category" stroke="#64748b" fontSize={9} width={100} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b", color: "#f8fafc" }}
                          cursor={{ fill: "rgba(255,255,255,0.05)" }}
                        />
                        <Bar dataKey="hits" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex justify-center items-center h-full text-slate-500 text-xs">
                      No logs telemetry recorded yet
                    </div>
                  )}
                </div>
              </div>

              <div className="glass-panel p-6 rounded-2xl border border-border-dark">
                <h3 className="text-sm font-bold text-slate-200 mb-4 uppercase tracking-wider">
                  Audit Hits Trend (Last 7 Days)
                </h3>
                <div className="h-64">
                  {telemetry.timeline_hits && telemetry.timeline_hits.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={telemetry.timeline_hits}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis dataKey="date" stroke="#64748b" fontSize={10} />
                        <YAxis stroke="#64748b" fontSize={11} />
                        <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b", color: "#f8fafc" }} />
                        <Line type="monotone" dataKey="hits" stroke="#818cf8" strokeWidth={2} activeDot={{ r: 6 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex justify-center items-center h-full text-slate-500 text-xs">
                      No audit timeline recorded yet
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Recent Security Timeline */}
          <div className="glass-panel p-6 rounded-2xl border border-border-dark">
            <h3 className="text-sm font-bold text-slate-200 mb-4 uppercase tracking-wider">
              Recent Security Activities
            </h3>
            <div className="space-y-4">
              {recentLogs.length > 0 ? (
                recentLogs.map((log) => (
                  <div key={log.id} className="flex gap-4 border-l-2 border-slate-800 pl-4 py-1">
                    <div className="text-left">
                      <span className="block text-xs font-bold text-slate-200">{log.action}</span>
                      <span className="block text-[10px] text-slate-400 mt-0.5">
                        By user: {log.user_id || "Guest"} ({log.user_role || "Unknown"}) • IP: {log.ip_address || "None"}
                      </span>
                    </div>
                    <div className="ml-auto text-right text-[10px] text-slate-500 whitespace-nowrap self-center">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-slate-500 text-xs text-center py-4">No recent security logs found</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Users Tab Content */}
      {activeTab === "users" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* User List Panel */}
          <div className="lg:col-span-2 glass-panel p-6 rounded-2xl border border-border-dark space-y-4">
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="text"
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  placeholder="Search users by name or email..."
                  className="w-full pl-9 pr-4 py-2.5 bg-slate-900 border border-border-dark rounded-xl text-xs text-slate-200 focus:outline-none focus:border-blue-500 transition-all"
                />
              </div>
              <select
                value={userRoleFilter}
                onChange={(e) => setUserRoleFilter(e.target.value)}
                className="px-3 py-2.5 bg-slate-900 border border-border-dark rounded-xl text-xs text-slate-400 focus:outline-none focus:border-blue-500 cursor-pointer"
              >
                <option value="">All Roles</option>
                <option value="SUPER_ADMIN">SUPER_ADMIN</option>
                <option value="ADMIN">ADMIN</option>
                <option value="MANAGER">MANAGER</option>
                <option value="ANALYST">ANALYST</option>
                <option value="VIEWER">VIEWER</option>
              </select>
              <button 
                onClick={fetchUsers}
                className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-semibold transition-all cursor-pointer"
              >
                Filter
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-border-dark text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                    <th className="pb-3 pl-2">User details</th>
                    <th className="pb-3">Role</th>
                    <th className="pb-3 text-center">Status</th>
                    <th className="pb-3 text-center pr-2">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-dark/50">
                  {users.length > 0 ? (
                    users.map((u) => (
                      <tr 
                        key={u.id} 
                        onClick={() => viewUserDetail(u.id)}
                        className={`hover:bg-slate-900/30 transition-colors cursor-pointer group ${
                          selectedUserDetail && selectedUserDetail.id === u.id ? "bg-blue-900/10" : ""
                        }`}
                      >
                        <td className="py-4 pl-2">
                          <span className="block text-xs font-semibold text-slate-200">{u.full_name}</span>
                          <span className="block text-[10px] text-slate-500 mt-0.5">{u.email}</span>
                        </td>
                        <td className="py-4">
                          <span className={`inline-flex px-2 py-0.5 rounded text-[9px] font-semibold border ${
                            u.role === "SUPER_ADMIN" ? "bg-purple-500/10 border-purple-500/20 text-purple-400" :
                            u.role === "ADMIN" ? "bg-blue-500/10 border-blue-500/20 text-blue-400" :
                            u.role === "MANAGER" ? "bg-amber-500/10 border-amber-500/20 text-amber-400" :
                            u.role === "ANALYST" ? "bg-indigo-500/10 border-indigo-500/20 text-indigo-400" :
                            "bg-slate-500/10 border-slate-500/20 text-slate-400"
                          }`}>
                            {u.role}
                          </span>
                        </td>
                        <td className="py-4 text-center">
                          <span className={`inline-flex px-1.5 py-0.5 rounded-full text-[9px] font-bold ${
                            u.is_active ? "bg-emerald-500/10 text-emerald-400" : "bg-rose-500/10 text-rose-400"
                          }`}>
                            {u.is_active ? "Active" : "Suspended"}
                          </span>
                        </td>
                        <td className="py-4 text-center pr-2" onClick={(e) => e.stopPropagation()}>
                          <div className="flex justify-center items-center gap-1.5">
                            <button
                              onClick={() => viewUserDetail(u.id)}
                              title="View details"
                              className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
                            >
                              <Eye className="w-3.5 h-3.5" />
                            </button>
                            {currentUser.role === "SUPER_ADMIN" && (
                              <button
                                onClick={() => handleDeleteUser(u.id)}
                                title="Delete user"
                                className="p-1.5 rounded hover:bg-rose-500/10 text-slate-400 hover:text-rose-400 transition-colors cursor-pointer"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-slate-500 text-xs">No users matching search filters found</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* User Details Sidebar */}
          <div className="glass-panel p-6 rounded-2xl border border-border-dark space-y-5 h-fit relative">
            <h3 className="text-sm font-bold text-slate-200 border-b border-border-dark pb-3 uppercase tracking-wider flex items-center gap-2">
              User Details Inspector
            </h3>
            {userDetailLoading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
              </div>
            ) : selectedUserDetail ? (
              <div className="space-y-6">
                <div>
                  <h4 className="text-base font-bold text-slate-100">{selectedUserDetail.full_name}</h4>
                  <span className="text-xs text-slate-400 break-all">{selectedUserDetail.email}</span>
                </div>

                <div className="grid grid-cols-2 gap-4 border-y border-border-dark/60 py-4">
                  <div>
                    <span className="block text-[10px] font-semibold text-slate-500 uppercase">Total Sessions</span>
                    <span className="text-base font-bold text-slate-200">{selectedUserDetail.session_count}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] font-semibold text-slate-500 uppercase">Audit Operations</span>
                    <span className="text-base font-bold text-slate-200">{selectedUserDetail.action_count}</span>
                  </div>
                </div>

                {/* Role modifier */}
                <div className="space-y-2">
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Change Role Authority
                  </label>
                  <select
                    value={selectedUserDetail.role}
                    onChange={(e) => handleUpdateRole(selectedUserDetail.id, e.target.value)}
                    className="w-full px-3 py-2 bg-slate-900 border border-border-dark rounded-xl text-xs text-slate-300 focus:outline-none focus:border-blue-500 cursor-pointer"
                  >
                    <option value="VIEWER">VIEWER</option>
                    <option value="ANALYST">ANALYST</option>
                    <option value="MANAGER">MANAGER</option>
                    <option value="ADMIN">ADMIN</option>
                    {currentUser.role === "SUPER_ADMIN" && <option value="SUPER_ADMIN">SUPER_ADMIN</option>}
                  </select>
                </div>

                {/* Account status toggler */}
                <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950/40 border border-border-dark">
                  <div>
                    <span className="block text-xs font-semibold text-slate-200">Account Access</span>
                    <span className="block text-[10px] text-slate-500">Enable or suspend account permissions</span>
                  </div>
                  <button
                    onClick={() => handleToggleStatus(selectedUserDetail.id, selectedUserDetail.is_active)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                      selectedUserDetail.is_active
                        ? "bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20"
                        : "bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20"
                    }`}
                  >
                    {selectedUserDetail.is_active ? "Suspend" : "Activate"}
                  </button>
                </div>

                <div className="text-[10px] text-slate-500 space-y-1.5 border-t border-border-dark/60 pt-4">
                  <div className="flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-slate-600" />
                    <span>Registered: {new Date(selectedUserDetail.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <CheckCircle className="w-3.5 h-3.5 text-slate-600" />
                    <span>User ID: {selectedUserDetail.id}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-slate-500 text-xs text-center py-12">
                Select a user from the directory to review their logs, active sessions, and permissions.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Security Audits Tab Content */}
      {activeTab === "audits" && (
        <div className="glass-panel p-6 rounded-2xl border border-border-dark space-y-5">
          {/* Query Filters */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                value={auditSearchAction}
                onChange={(e) => setAuditSearchAction(e.target.value)}
                placeholder="Filter by Action (e.g. USER_LOGIN, MATCHING)..."
                className="w-full pl-9 pr-4 py-2.5 bg-slate-900 border border-border-dark rounded-xl text-xs text-slate-200 focus:outline-none focus:border-blue-500 transition-all"
              />
            </div>
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                value={auditSearchUser}
                onChange={(e) => setAuditSearchUser(e.target.value)}
                placeholder="Filter by User ID..."
                className="w-full pl-9 pr-4 py-2.5 bg-slate-900 border border-border-dark rounded-xl text-xs text-slate-200 focus:outline-none focus:border-blue-500 transition-all"
              />
            </div>
            <button
              onClick={fetchAuditLogs}
              className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-semibold transition-all cursor-pointer"
            >
              Search
            </button>
          </div>

          {/* Audit Logs Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border-dark text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                  <th className="pb-3 pl-2">Timestamp</th>
                  <th className="pb-3">Action</th>
                  <th className="pb-3">User & Role</th>
                  <th className="pb-3">IP Address</th>
                  <th className="pb-3 text-center pr-2">Telemetry</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-dark/50">
                {auditLogs.length > 0 ? (
                  auditLogs.map((log) => {
                    const isExpanded = expandedLogId === log.id;
                    return (
                      <React.Fragment key={log.id}>
                        <tr 
                          onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                          className={`hover:bg-slate-900/30 transition-all cursor-pointer ${
                            isExpanded ? "bg-slate-900/40" : ""
                          }`}
                        >
                          <td className="py-4 pl-2 text-[11px] text-slate-400 font-mono">
                            {new Date(log.timestamp).toLocaleString()}
                          </td>
                          <td className="py-4 text-xs font-bold text-slate-200">
                            {log.action}
                          </td>
                          <td className="py-4 text-xs">
                            <span className="block text-slate-300 font-semibold">{log.user_id ? log.user_id.slice(0, 8) + "..." : "Guest"}</span>
                            <span className="block text-[9px] text-slate-500 mt-0.5">{log.user_role || "Unknown"}</span>
                          </td>
                          <td className="py-4 text-xs font-mono text-slate-400">
                            {log.ip_address || "Internal"}
                          </td>
                          <td className="py-4 text-center pr-2">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setExpandedLogId(isExpanded ? null : log.id);
                              }}
                              className="px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 text-[10px] font-semibold text-slate-400 hover:text-slate-200 transition-colors"
                            >
                              {isExpanded ? "Hide Diff" : "View Diff"}
                            </button>
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr className="bg-slate-950/20">
                            <td colSpan={5} className="py-4 px-4 border-b border-border-dark/80">
                              <div className="space-y-3">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[11px]">
                                  <div>
                                    <span className="block font-bold text-slate-500 uppercase tracking-wide">Resource Type:</span>
                                    <span className="text-slate-300 font-mono">{log.resource_type}</span>
                                  </div>
                                  <div>
                                    <span className="block font-bold text-slate-500 uppercase tracking-wide">Resource ID:</span>
                                    <span className="text-slate-300 font-mono break-all">{log.resource_id || "None"}</span>
                                  </div>
                                  <div className="md:col-span-2">
                                    <span className="block font-bold text-slate-500 uppercase tracking-wide">User Agent:</span>
                                    <span className="text-slate-400 font-sans text-[10px] break-all">{log.client_agent || "No agent info"}</span>
                                  </div>
                                </div>
                                <div className="space-y-1">
                                  <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wide">Change Differentials:</span>
                                  {formatChangeDiff(log.change_diff)}
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-slate-500 text-xs">
                      No security audit log entries match search parameters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
