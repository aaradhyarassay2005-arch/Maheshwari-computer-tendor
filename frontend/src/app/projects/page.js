"use client";

import React, { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { 
  FolderOpen, 
  UploadCloud, 
  Search, 
  SlidersHorizontal, 
  ChevronLeft, 
  ChevronRight, 
  Loader2, 
  CheckCircle, 
  AlertTriangle,
  Building,
  DollarSign,
  ChevronDown,
  Percent,
  Plus
} from "lucide-react";
import { 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  Legend 
} from "recharts";

export default function ProjectsPage() {
  const [projects, setProjects] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [capabilities, setCapabilities] = useState([]);
  const [isMounted, setIsMounted] = useState(false);

  // Uploader form states
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadMode, setUploadMode] = useState("single"); // single or excel
  const [documentType, setDocumentType] = useState("LOA");
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [uploadError, setUploadError] = useState(null);

  // Search/Filters states
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [domainFilter, setDomainFilter] = useState("ALL");
  const [page, setPage] = useState(1);
  const limit = 10;

  useEffect(() => {
    setIsMounted(true);
    fetchCapabilities();
  }, []);

  // Debounce search
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 400);
    return () => clearTimeout(handler);
  }, [search]);

  // Query projects
  useEffect(() => {
    fetchProjects();
  }, [debouncedSearch, domainFilter, page]);

  const fetchProjects = async () => {
    setLoading(true);
    try {
      const skip = (page - 1) * limit;
      const data = await api.getProjects(
        skip, 
        limit, 
        debouncedSearch, 
        domainFilter === "ALL" ? "" : domainFilter
      );
      setProjects(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error("Failed to query projects", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchCapabilities = async () => {
    try {
      const data = await api.getCapabilities();
      setCapabilities(data || []);
    } catch (err) {
      console.error("Failed to fetch capabilities", err);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setUploadSuccess(null);
    setUploadError(null);

    try {
      const result = await api.uploadProject(documentType, file);
      setUploadSuccess(`Successfully extracted & saved project: ${result.project_name}`);
      fetchProjects();
      fetchCapabilities();
      setTimeout(() => setShowUploadModal(false), 2000);
    } catch (err) {
      setUploadError(err.message || "Failed to process project certificate");
    } finally {
      setUploading(false);
    }
  };

  const handleExcelUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setUploadSuccess(null);
    setUploadError(null);

    try {
      const result = await api.importProjectsExcel(file);
      setUploadSuccess(`Import complete! Inserted ${result.inserted} projects, duplicates: ${result.duplicates}, failed: ${result.failed}`);
      fetchProjects();
      fetchCapabilities();
      setTimeout(() => setShowUploadModal(false), 3000);
    } catch (err) {
      setUploadError(err.message || "Failed to import projects from Excel");
    } finally {
      setUploading(false);
    }
  };

  // Unique domains list
  const domainsList = ["ALL", "Signaling", "Telecom", "Civil", "Electrical", "Mechanical"];

  // Bar chart data from capabilities
  const chartData = capabilities.map(cap => ({
    name: cap.domain.substring(0, 15),
    value: parseFloat(cap.total_value) / 10000000 // Convert to Crores
  }));

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white bg-gradient-to-r from-indigo-400 to-slate-200 bg-clip-text text-transparent flex items-center gap-2">
            <FolderOpen className="w-6 h-6 text-indigo-500" />
            Past Projects Registry
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Store and evaluate capability certificates (LOAs, Work Orders, Completion Certificates) to match active tender criteria.
          </p>
        </div>
        <button
          onClick={() => {
            setUploadSuccess(null);
            setUploadError(null);
            setShowUploadModal(true);
          }}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-xl text-xs font-bold text-white shadow-md shadow-indigo-500/25 transition-all duration-200 hover:-translate-y-0.5"
        >
          <Plus className="w-4 h-4" />
          Ingest Project File
        </button>
      </div>

      {/* Upload Modal overlay */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel max-w-md w-full rounded-2xl p-6 border-indigo-500/30 relative overflow-hidden shadow-2xl">
            <div className="absolute top-0 right-0 w-48 h-48 bg-indigo-600/5 rounded-full blur-[60px]" />
            <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <UploadCloud className="w-4.5 h-4.5 text-indigo-400" />
                Ingest Past Project Document
              </h3>
              <button 
                onClick={() => setShowUploadModal(false)}
                className="text-slate-400 hover:text-slate-200 text-xs font-medium cursor-pointer"
              >
                Close
              </button>
            </div>

            <div className="space-y-4">
              {/* Toggle Mode */}
              <div className="flex bg-slate-950/60 p-1 rounded-xl border border-slate-850">
                <button
                  type="button"
                  onClick={() => {
                    setUploadSuccess(null);
                    setUploadError(null);
                    setUploadMode("single");
                  }}
                  className={`flex-1 py-1.5 text-center text-[10px] font-bold rounded-lg transition-all cursor-pointer ${
                    uploadMode === "single"
                      ? "bg-indigo-600 text-white shadow"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Single PDF Ingestion
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setUploadSuccess(null);
                    setUploadError(null);
                    setUploadMode("excel");
                  }}
                  className={`flex-1 py-1.5 text-center text-[10px] font-bold rounded-lg transition-all cursor-pointer ${
                    uploadMode === "excel"
                      ? "bg-indigo-600 text-white shadow"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Excel Batch Import
                </button>
              </div>

              {uploadMode === "single" ? (
                <>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Document Type</label>
                    <select
                      value={documentType}
                      onChange={(e) => setDocumentType(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-850 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none cursor-pointer"
                    >
                      <option value="LOA">Letter of Award (LOA)</option>
                      <option value="WORK_ORDER">Work Order</option>
                      <option value="COMPLETION_CERTIFICATE">Completion Certificate</option>
                      <option value="INVOICE">Invoice Receipt</option>
                    </select>
                  </div>

                  <div>
                    <label className="border border-dashed border-slate-805 hover:border-indigo-500/50 rounded-2xl p-6 flex flex-col items-center text-center cursor-pointer transition bg-slate-950/20 hover:bg-slate-950/40">
                      <input 
                        type="file" 
                        accept=".pdf"
                        className="hidden" 
                        onChange={handleFileUpload} 
                        disabled={uploading} 
                      />
                      {uploading ? (
                        <div className="space-y-2">
                          <Loader2 className="w-7 h-7 text-indigo-500 animate-spin mx-auto" />
                          <span className="block text-xs font-semibold text-slate-200">Extracting contract scope...</span>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <div className="w-9 h-9 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-center mx-auto text-slate-400">
                            <UploadCloud className="w-4.5 h-4.5" />
                          </div>
                          <span className="block text-xs font-semibold text-slate-350">Click to select contract PDF</span>
                          <span className="block text-[9px] text-slate-500 font-medium">NLP automatically indexes domain capabilities</span>
                        </div>
                      )}
                    </label>
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="border border-dashed border-slate-805 hover:border-indigo-500/50 rounded-2xl p-6 flex flex-col items-center text-center cursor-pointer transition bg-slate-950/20 hover:bg-slate-950/40">
                      <input 
                        type="file" 
                        accept=".xlsx, .xls"
                        className="hidden" 
                        onChange={handleExcelUpload} 
                        disabled={uploading} 
                      />
                      {uploading ? (
                        <div className="space-y-2">
                          <Loader2 className="w-7 h-7 text-indigo-500 animate-spin mx-auto" />
                          <span className="block text-xs font-semibold text-slate-200">Importing past projects...</span>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <div className="w-9 h-9 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-center mx-auto text-slate-400">
                            <UploadCloud className="w-4.5 h-4.5 text-indigo-400" />
                          </div>
                          <span className="block text-xs font-semibold text-slate-350">Click to select projects Excel sheet</span>
                          <span className="block text-[9px] text-slate-500 font-medium">Accepts Location, LOA Name, Project Name, value headers</span>
                        </div>
                      )}
                    </label>
                  </div>
                </>
              )}

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
            </div>
          </div>
        </div>
      )}

      {/* Analytics Visualization Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Capability chart */}
        <div className="lg:col-span-2 glass-panel rounded-2xl p-6 flex flex-col gap-4">
          <div>
            <h3 className="text-sm font-bold text-slate-200">Capability Value Distribution</h3>
            <p className="text-[10px] text-slate-400">Total volume of indexed projects grouped by tech domain.</p>
          </div>
          <div className="h-44">
            {isMounted && chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <XAxis dataKey="name" stroke="#475569" fontSize={8} tickLine={false} />
                  <YAxis stroke="#475569" fontSize={8} tickLine={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: "#0b0f19", borderRadius: "10px", borderColor: "rgba(255,255,255,0.08)", color: "#fff", fontSize: "11px" }}
                  />
                  <Bar dataKey="value" fill="#6366f1" radius={[3, 3, 0, 0]} name="Total Volume (Cr)" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex flex-col items-center justify-center text-xs text-slate-500 h-full border border-dashed border-slate-800 rounded-2xl w-full">
                <FolderOpen className="w-6 h-6 mb-2 opacity-40 text-slate-500" />
                <span>No capabilities index.</span>
              </div>
            )}
          </div>
        </div>

        {/* Business Capability Summaries List */}
        <div className="glass-panel rounded-2xl p-6 flex flex-col gap-4 border-l-2 border-l-indigo-500/80">
          <div>
            <h3 className="text-sm font-bold text-slate-200">Domain Summaries</h3>
            <p className="text-[10px] text-slate-400 font-medium">Domain counts registered in vector memory.</p>
          </div>
          <div className="space-y-3 flex-1 overflow-y-auto max-h-[160px] pr-1 scrollbar-none">
            {capabilities.length > 0 ? (
              capabilities.map((cap, i) => (
                <div key={i} className="flex items-center justify-between p-2.5 bg-slate-950/20 border border-slate-850 rounded-xl">
                  <div className="text-xs">
                    <span className="block font-bold text-slate-250">{cap.domain}</span>
                    <span className="block text-[9px] text-slate-500 mt-0.5">{cap.project_count} projects indexed</span>
                  </div>
                  <span className="text-xs font-mono font-bold text-indigo-400">
                    ₹{(parseFloat(cap.total_value) / 10000000).toFixed(1)} Cr
                  </span>
                </div>
              ))
            ) : (
              <div className="text-xs text-slate-500 text-center py-6">No capabilities mapped yet.</div>
            )}
          </div>
        </div>
      </div>

      {/* Control filters & lists */}
      <div className="glass-panel rounded-2xl p-4 shadow-xl">
        <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
          <div className="w-full md:max-w-md relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search contracts by project name, location or client name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-slate-950/60 border border-slate-800 focus:border-indigo-500 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-200 outline-none transition-all duration-200"
            />
          </div>

          <div className="w-full md:w-auto flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5 bg-slate-950/50 border border-slate-800 rounded-xl px-2.5 py-1.5 shrink-0">
              <SlidersHorizontal className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Filters:</span>
            </div>
            
            <div className="relative">
              <select
                value={domainFilter}
                onChange={(e) => setDomainFilter(e.target.value)}
                className="appearance-none bg-slate-900 border border-slate-800 hover:border-slate-700 focus:border-indigo-500 rounded-xl pl-3 pr-8 py-1.5 text-xs text-slate-300 outline-none transition cursor-pointer"
              >
                {domainsList.map(d => (
                  <option key={d} value={d}>{d === "ALL" ? "All Domains" : d}</option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>
        </div>
      </div>

      {/* Database table ledger */}
      <div className="glass-panel rounded-2xl p-5 shadow-2xl overflow-hidden">
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center text-slate-400">
            <Loader2 className="w-8 h-8 text-indigo-500 animate-spin mb-2" />
            <span className="text-xs font-semibold">Retrieving capability list...</span>
          </div>
        ) : projects.length === 0 ? (
          <div className="py-16 text-center border border-dashed border-slate-800 rounded-2xl bg-slate-950/25 text-slate-500">
            <FolderOpen className="w-9 h-9 mx-auto mb-3 opacity-30 text-indigo-500" />
            <p className="text-xs font-medium">No past projects indexed in this category.</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-800/80 text-slate-400 text-[10px] font-bold uppercase tracking-wider">
                    <th className="py-3 px-4">Project Name</th>
                    <th className="py-3 px-4">Client</th>
                    <th className="py-3 px-4 text-right">Value (INR)</th>
                    <th className="py-3 px-4">Completion Date</th>
                    <th className="py-3 px-4">Domain</th>
                    <th className="py-3 px-4">Location</th>
                    <th className="py-3 px-4 text-center">Type</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40">
                  {projects.map((proj) => (
                    <tr key={proj.id} className="hover:bg-slate-800/20 transition-colors">
                      <td className="py-3.5 px-4 font-bold text-slate-300">{proj.project_name}</td>
                      <td className="py-3.5 px-4 text-slate-400 font-medium">
                        <span className="flex items-center gap-2">
                          <Building className="w-3.5 h-3.5 text-slate-650" />
                          {proj.client}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right font-semibold text-slate-200 font-mono">
                        ₹{parseFloat(proj.project_value).toLocaleString("en-IN")}
                      </td>
                      <td className="py-3.5 px-4 text-slate-400 font-mono">
                        {proj.completion_date ? new Date(proj.completion_date).toLocaleDateString() : "UNKNOWN"}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="px-2 py-0.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[9px] font-bold">
                          {proj.domain}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-slate-400 font-medium">{proj.location}</td>
                      <td className="py-3.5 px-4 text-center">
                        <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400 font-mono text-[9px] uppercase">
                          {proj.document_type}
                        </span>
                      </td>
                    </tr>
                  ))}
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
