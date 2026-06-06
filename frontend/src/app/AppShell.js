"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { 
  LayoutDashboard, 
  FileText, 
  Layers,
  Menu,
  X,
  ChevronRight,
  ClipboardCheck,
  Settings,
  LogOut,
  FolderOpen,
  User,
  ShieldAlert,
  ChevronLeft
} from "lucide-react";
import { api } from "@/lib/api";

export default function AppShell({ children }) {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [apiConnected, setApiConnected] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);

  // Authentication client-side router guard
  useEffect(() => {
    if (typeof window === "undefined") return;
    
    const token = localStorage.getItem("access_token");
    const userStr = localStorage.getItem("user");
    const isAuthPage = ["/login", "/register", "/forgot-password", "/reset-password"].includes(pathname);
    
    if (!token && !isAuthPage) {
      window.location.href = "/login";
    } else if (userStr) {
      try {
        setCurrentUser(JSON.parse(userStr));
      } catch (_) {
        localStorage.clear();
        window.location.href = "/login";
      }
    }
  }, [pathname]);

  // Check backend health on mount
  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch("http://localhost:8000/health");
        if (res.ok) {
          setApiConnected(true);
        } else {
          setApiConnected(false);
        }
      } catch (err) {
        setApiConnected(false);
      }
    }
    checkHealth();
    const timer = setInterval(checkHealth, 30000);
    return () => clearInterval(timer);
  }, []);

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch (_) {}
    localStorage.clear();
    window.location.href = "/login";
  };

  const isAuthPage = ["/login", "/register", "/forgot-password", "/reset-password"].includes(pathname);

  if (isAuthPage) {
    return (
      <div className="min-h-screen bg-background-dark text-slate-100 flex flex-col justify-center items-center relative overflow-hidden">
        {/* Animated background glow elements */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full bg-indigo-600/10 blur-[130px] pointer-events-none animate-pulse" />
        <div className="absolute bottom-1/4 left-1/2 -translate-x-1/2 translate-y-1/2 w-96 h-96 rounded-full bg-blue-600/10 blur-[130px] pointer-events-none animate-pulse" style={{ animationDelay: "1s" }} />
        <div className="w-full max-w-md z-10 p-4">
          {children}
        </div>
      </div>
    );
  }

  // Base navigation
  const navigation = [
    { name: "Executive Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Tender Explorer", href: "/tenders", icon: FileText },
    { name: "Review Queue", href: "/reviews", icon: ClipboardCheck },
    { name: "Past Projects", href: "/projects", icon: FolderOpen },
    { name: "User Profile", href: "/profile", icon: User }
  ];

  // Conditional Admin & Audit navigation
  const isAdmin = currentUser && (currentUser.role === "ADMIN" || currentUser.role === "SUPER_ADMIN");
  
  const adminNavigation = [
    { name: "Platform Admin", href: "/admin", icon: Settings },
    { name: "Security Audit Logs", href: "/admin/audit-logs", icon: ShieldAlert }
  ];

  // Extract initials for profile icon
  const getInitials = (name) => {
    if (!name) return "U";
    return name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2);
  };

  const getPageTitle = () => {
    if (pathname === "/") return "Executive Summary";
    if (pathname.startsWith("/tenders/")) return "Tender Detail Analysis";
    if (pathname.startsWith("/tenders")) return "Tender Explorer Registry";
    if (pathname.startsWith("/reviews")) return "Human Evaluation Queue";
    if (pathname.startsWith("/projects")) return "Corporate Project Matching";
    if (pathname.startsWith("/profile")) return "Account Diagnostics";
    if (pathname.startsWith("/admin/audit-logs")) return "Security Audit Trail";
    if (pathname.startsWith("/admin")) return "Super Admin Operations";
    return "Tender Intelligence Engine";
  };

  return (
    <div className="flex min-h-screen bg-background-dark text-slate-100">
      {/* Sidebar for Desktop */}
      <motion.aside 
        animate={{ width: sidebarCollapsed ? 76 : 260 }}
        transition={{ duration: 0.3, ease: "easeInOut" }}
        className="hidden md:flex md:flex-col md:fixed md:inset-y-0 glass-panel border-r border-border-dark z-20 overflow-hidden"
      >
        <div className="flex flex-col flex-1 min-h-0 relative">
          {/* Logo & Collapse button */}
          <div className="flex items-center h-16 px-4 bg-slate-950/40 border-b border-border-dark justify-between overflow-hidden">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-600 text-white shadow-lg shadow-indigo-500/30 shrink-0">
                <Layers className="w-5 h-5" />
              </div>
              {!sidebarCollapsed && (
                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  className="whitespace-nowrap"
                >
                  <span className="text-base font-bold bg-gradient-to-r from-indigo-400 to-slate-200 bg-clip-text text-transparent">
                    TenderIntel
                  </span>
                  <span className="block text-[8px] text-slate-400 font-semibold tracking-widest uppercase">
                    Enterprise SaaS
                  </span>
                </motion.div>
              )}
            </div>
            {!sidebarCollapsed && (
              <button 
                onClick={() => setSidebarCollapsed(true)}
                className="p-1 rounded-lg hover:bg-slate-800/60 text-slate-400 hover:text-slate-200 hidden md:block"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Toggle Expand for collapsed sidebar */}
          {sidebarCollapsed && (
            <button
              onClick={() => setSidebarCollapsed(false)}
              className="absolute right-0 top-18 translate-x-1/2 p-1 rounded-full bg-indigo-600 border border-indigo-400 text-white shadow-md hover:bg-indigo-500 z-30 transition-transform hover:scale-110"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          )}

          {/* Navigation Links */}
          <nav className="flex-1 px-3 py-6 space-y-1.5 overflow-y-auto">
            {/* Core Section Label */}
            {!sidebarCollapsed && (
              <div className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
                Core Engine
              </div>
            )}
            {navigation.map((item) => {
              const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center px-3 py-2.5 text-sm font-medium rounded-xl transition-all duration-200 group relative ${
                    active
                      ? "bg-indigo-600/15 text-indigo-400 border border-indigo-500/20 shadow-inner"
                      : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/40 border border-transparent"
                  }`}
                  title={sidebarCollapsed ? item.name : undefined}
                >
                  <Icon className={`h-5 w-5 shrink-0 transition-transform duration-200 group-hover:scale-105 ${
                    active ? "text-indigo-400" : "text-slate-400 group-hover:text-slate-200"
                  } ${sidebarCollapsed ? "" : "mr-3"}`} />
                  {!sidebarCollapsed && <span>{item.name}</span>}
                  {active && !sidebarCollapsed && <ChevronRight className="ml-auto w-4 h-4 text-indigo-400" />}
                </Link>
              );
            })}

            {/* Admin Management Section */}
            {isAdmin && (
              <>
                <div className="pt-4 pb-2">
                  {!sidebarCollapsed ? (
                    <div className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                      Administration
                    </div>
                  ) : (
                    <div className="border-t border-slate-800/60 my-2" />
                  )}
                </div>
                {adminNavigation.map((item) => {
                  const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={`flex items-center px-3 py-2.5 text-sm font-medium rounded-xl transition-all duration-200 group ${
                        active
                          ? "bg-indigo-600/15 text-indigo-400 border border-indigo-500/20 shadow-inner"
                          : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/40 border border-transparent"
                      }`}
                      title={sidebarCollapsed ? item.name : undefined}
                    >
                      <Icon className={`h-5 w-5 shrink-0 transition-transform duration-200 group-hover:scale-105 ${
                        active ? "text-indigo-400" : "text-slate-400 group-hover:text-slate-200"
                      } ${sidebarCollapsed ? "" : "mr-3"}`} />
                      {!sidebarCollapsed && <span>{item.name}</span>}
                      {active && !sidebarCollapsed && <ChevronRight className="ml-auto w-4 h-4 text-indigo-400" />}
                    </Link>
                  );
                })}
              </>
            )}
          </nav>

          {/* Connection Status Footnote */}
          <div className="p-3 border-t border-border-dark bg-slate-950/20 shrink-0">
            <div className={`flex items-center justify-between text-xs px-2 ${sidebarCollapsed ? "flex-col gap-1.5" : ""}`}>
              {!sidebarCollapsed && <span className="text-slate-400 font-medium">Core Engine:</span>}
              <span className="flex items-center gap-1.5 font-semibold">
                <span className={`w-2 h-2 rounded-full ${
                  apiConnected === null 
                    ? "bg-slate-500 animate-pulse" 
                    : apiConnected 
                      ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" 
                      : "bg-rose-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]"
                }`} />
                {!sidebarCollapsed && (
                  <span className="text-[10px]">
                    {apiConnected === null ? "Pinging..." : apiConnected ? "Online" : "Offline"}
                  </span>
                )}
              </span>
            </div>
          </div>
        </div>
      </motion.aside>

      {/* Mobile Menu Backdrop */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-30 md:hidden"
            onClick={() => setMobileMenuOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar for Mobile */}
      <aside className={`fixed inset-y-0 left-0 w-64 glass-panel border-r border-border-dark z-40 transform transition-transform duration-300 ease-in-out md:hidden ${
        mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
      }`}>
        <div className="flex flex-col h-full">
          <div className="flex items-center justify-between h-16 px-6 border-b border-border-dark">
            <div className="flex items-center gap-2">
              <Layers className="w-5 h-5 text-indigo-500" />
              <span className="text-lg font-bold text-slate-100">TenderIntel</span>
            </div>
            <button 
              onClick={() => setMobileMenuOpen(false)}
              className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-100"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
          <nav className="flex-1 px-4 py-6 space-y-1">
            {navigation.map((item) => {
              const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center px-4 py-3 text-sm font-medium rounded-xl border transition-all ${
                    active
                      ? "bg-indigo-600/20 text-indigo-400 border-indigo-500/20"
                      : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/40 border-transparent"
                  }`}
                >
                  <Icon className="mr-3 h-5 w-5" />
                  {item.name}
                </Link>
              );
            })}

            {isAdmin && (
              <>
                <div className="border-t border-slate-800/60 my-4 pt-4" />
                {adminNavigation.map((item) => {
                  const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center px-4 py-3 text-sm font-medium rounded-xl border transition-all ${
                        active
                          ? "bg-indigo-600/20 text-indigo-400 border-indigo-500/20"
                          : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/40 border-transparent"
                      }`}
                    >
                      <Icon className="mr-3 h-5 w-5" />
                      {item.name}
                    </Link>
                  );
                })}
              </>
            )}
          </nav>
          <div className="p-4 border-t border-border-dark">
            <div className="flex items-center justify-between text-xs px-2">
              <span className="text-slate-400">Core API:</span>
              <span className="flex items-center gap-1 font-semibold">
                <span className={`w-2.5 h-2.5 rounded-full ${apiConnected ? "bg-emerald-500" : "bg-rose-500"}`} />
                {apiConnected ? "Connected" : "Offline"}
              </span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div 
        className="flex flex-col flex-1 transition-all duration-300" 
        style={{ paddingLeft: typeof window !== "undefined" && window.innerWidth >= 768 ? (sidebarCollapsed ? "76px" : "260px") : "0px" }}
      >
        {/* Top Navbar */}
        <header className="sticky top-0 h-16 flex items-center justify-between px-6 md:px-8 bg-slate-950/40 backdrop-blur-md border-b border-border-dark z-10">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="p-2 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-100 md:hidden"
            >
              <Menu className="w-6 h-6" />
            </button>
            <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-widest">
              {getPageTitle()}
            </h2>
          </div>

          <div className="flex items-center gap-4">
            {/* Live Clock / Date Indicator */}
            <div className="text-xs text-slate-400 hidden lg:block border border-border-dark px-3 py-1.5 rounded-lg bg-slate-950/50 font-mono">
              <span className="font-semibold text-indigo-400">UTC Time: </span>
              {new Date().toISOString().replace('T', ' ').substring(0, 19)}
            </div>
            
            {/* User Profile Info */}
            {currentUser && (
              <div className="flex items-center gap-3">
                <Link href="/profile" className="flex items-center gap-2 group">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-blue-500 flex items-center justify-center font-bold text-sm text-white shadow-inner shadow-white/20 transition-transform group-hover:scale-105">
                    {getInitials(currentUser.full_name)}
                  </div>
                  <div className="text-left hidden sm:block">
                    <span className="block text-xs font-semibold text-slate-200 group-hover:text-indigo-400 transition-colors">{currentUser.full_name}</span>
                    <span className="block text-[9px] text-slate-400 uppercase tracking-wider font-semibold">{currentUser.role}</span>
                  </div>
                </Link>

                <button 
                  onClick={handleLogout}
                  title="Logout"
                  className="p-1.5 rounded-lg bg-slate-900 border border-border-dark hover:bg-rose-500/10 text-slate-400 hover:text-rose-400 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </header>

        {/* Dynamic Page Layout Container */}
        <main className="flex-1 p-6 md:p-8 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
