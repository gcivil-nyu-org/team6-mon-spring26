"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import {
  LayoutDashboard,
  Receipt,
  CheckSquare,
  Users,
  Settings,
  LogOut,
  Menu,
  X,
  Loader2,
  ChevronRight,
  Home,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", href: "/dashboard", active: true },
  { icon: Receipt, label: "Expenses", href: "#", comingSoon: true },
  { icon: CheckSquare, label: "Chores", href: "#", comingSoon: true },
  { icon: Users, label: "Household", href: "#", comingSoon: true },
  { icon: Settings, label: "Settings", href: "/dashboard/settings" },
];

function Avatar({ name }: { name: string }) {
  const initials = name
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  return (
    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-600 text-xs font-semibold text-white">
      {initials || "?"}
    </div>
  );
}

function ComingSoonBadge() {
  return (
    <span className="rounded-full bg-stone-100 px-2 py-0.5 text-xs font-medium text-stone-400">
      Soon
    </span>
  );
}

function Sidebar({
  user,
  logout,
  mobile,
  onClose,
}: {
  user: { display_name: string; email: string } | null;
  logout: () => void;
  mobile?: boolean;
  onClose?: () => void;
}) {
  const pathname = usePathname();

  return (
    <aside
      className={
        mobile
          ? "fixed inset-y-0 left-0 z-50 flex w-72 flex-col bg-white shadow-xl"
          : "hidden w-64 flex-shrink-0 flex-col border-r border-stone-100 bg-white lg:flex"
      }
    >
      {/* Logo */}
      <div className="flex items-center justify-between border-b border-stone-100 px-6 py-5">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center">
            <Image src="/logo.png" alt="Dues & Do's Logo" width={32} height={32} className="object-contain" />
          </div>
          <span className="font-display text-base font-semibold text-stone-900">
            Dues <span className="text-brand-600">&</span> Do&apos;s
          </span>
        </Link>
        {mobile && (
          <button onClick={onClose} className="rounded-lg p-1 hover:bg-stone-100">
            <X size={18} className="text-stone-500" />
          </button>
        )}
      </div>

      {/* Household pill */}
      <div className="border-b border-stone-100 px-4 py-3">
        <button className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors hover:bg-stone-50">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-100">
            <Home size={16} className="text-brand-600" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium text-stone-900">My Household</div>
            <div className="text-xs text-stone-400">Manage →</div>
          </div>
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1 overflow-y-auto p-4">
        {navItems.map((item) => {
          const isActive = item.href === pathname;
          return (
            <div key={item.label}>
              {item.comingSoon ? (
                <div className="flex cursor-not-allowed items-center gap-3 rounded-xl px-3 py-2.5 text-stone-400">
                  <item.icon size={18} />
                  <span className="flex-1 text-sm">{item.label}</span>
                  <ComingSoonBadge />
                </div>
              ) : (
                <Link
                  href={item.href}
                  onClick={onClose}
                  className={`flex items-center gap-3 rounded-xl px-3 py-2.5 transition-colors ${
                    isActive
                      ? "bg-brand-50 text-brand-700"
                      : "text-stone-600 hover:bg-stone-50 hover:text-stone-900"
                  }`}
                >
                  <item.icon size={18} />
                  <span className={`flex-1 text-sm ${isActive ? "font-medium" : ""}`}>
                    {item.label}
                  </span>
                </Link>
              )}
            </div>
          );
        })}
      </nav>

      {/* User */}
      <div className="border-t border-stone-100 p-4">
        <div className="flex items-center gap-3 rounded-xl px-3 py-2.5">
          <Avatar name={user?.display_name || ""} />
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium text-stone-900">
              {user?.display_name}
            </div>
            <div className="truncate text-xs text-stone-400">{user?.email}</div>
          </div>
          <button
            onClick={logout}
            className="rounded-lg p-1.5 text-stone-400 transition-colors hover:bg-stone-100 hover:text-stone-600"
            title="Log out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 size={24} className="animate-spin text-brand-600" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-stone-50">
      {/* Desktop sidebar */}
      <Sidebar user={user} logout={logout} />

      {/* Mobile sidebar overlay */}
      {mobileSidebarOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-stone-900/30 backdrop-blur-sm lg:hidden"
            onClick={() => setMobileSidebarOpen(false)}
          />
          <Sidebar
            user={user}
            logout={logout}
            mobile
            onClose={() => setMobileSidebarOpen(false)}
          />
        </>
      )}

      {/* Main content */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Top bar */}
        <header className="flex items-center gap-4 border-b border-stone-100 bg-white px-4 py-4 sm:px-6">
          <button
            className="rounded-lg p-2 text-stone-500 hover:bg-stone-100 lg:hidden"
            onClick={() => setMobileSidebarOpen(true)}
          >
            <Menu size={20} />
          </button>
          <div className="flex-1">
            <h1 className="text-base font-semibold text-stone-900 sm:text-lg">
              {/* Header content like "Good morning, user" can be passed up via context or moved to page components.
                  Since layout wraps multiple pages, we'll keep it simple and generic, or allow children to define their title. 
                  For now we render a generic app header, and individual pages can use the main content area for their specific headers. */}
            </h1>
          </div>
        </header>

        {/* Page body */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
