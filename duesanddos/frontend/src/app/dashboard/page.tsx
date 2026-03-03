"use client";

import { useAuth } from "@/hooks/useAuth";
import { Receipt, CheckSquare, Users, ChevronRight } from "lucide-react";

export default function DashboardPage() {
  const { user } = useAuth();
  
  if (!user) return null;

  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  return (
    <>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-stone-900">
          {greeting}, {user.display_name.split(" ")[0]}
        </h1>
      </div>

      {/* Welcome banner */}
      <div className="mb-8 rounded-2xl bg-brand-600 p-6 text-white sm:p-8">
        <div className="max-w-lg">
          <h2 className="font-display text-2xl font-semibold">
            Welcome to Dues &amp; Do&apos;s!
          </h2>
          <p className="mt-2 text-brand-100">
            Your household is set up and ready. Once we launch the full features, you&apos;ll be able to track expenses, assign chores, and keep everyone on the same page.
          </p>
        </div>
      </div>

      {/* Coming soon cards */}
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-widest text-stone-400">
        Coming soon
      </h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[
          {
            icon: Receipt,
            title: "Expense Splitting",
            body: "Log shared bills and split them any way you like. Running balances always visible.",
            color: "bg-blue-50 text-blue-600",
          },
          {
            icon: CheckSquare,
            title: "Chore Scheduling",
            body: "Assign chores, set recurrence, and rotate fairly. No more forgetting who does what.",
            color: "bg-amber-50 text-amber-600",
          },
          {
            icon: Users,
            title: "Household Members",
            body: "Invite roommates, manage roles, and see everyone's contribution at a glance.",
            color: "bg-purple-50 text-purple-600",
          },
        ].map((card) => (
          <div key={card.title} className="card p-5 opacity-75">
            <div
              className={`mb-4 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-white shadow-sm ring-1 ring-stone-900/5 ${card.color}`}
            >
              <card.icon size={20} />
            </div>
            <h3 className="mb-1 font-semibold text-stone-900">{card.title}</h3>
            <p className="text-sm leading-relaxed text-stone-500">{card.body}</p>
            <div className="mt-4 inline-flex items-center gap-1 text-xs font-medium text-stone-400">
              In development
              <ChevronRight size={12} />
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
