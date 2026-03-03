"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { authApi } from "@/lib/api";
import { Loader2, CheckCircle2 } from "lucide-react";

export default function SettingsPage() {
  const { user, refreshUser } = useAuth();
  
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  
  const [formData, setFormData] = useState({
    full_name: user?.full_name || "",
    phone: user?.phone || "",
    timezone: user?.timezone || "UTC",
    language: user?.language || "en",
    default_currency: user?.default_currency || "USD",
    date_format: user?.date_format || "MM/DD/YYYY",
    notifications_enabled: user?.notifications_enabled ?? true,
  });

  if (!user) return null;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    if (type === "checkbox") {
      const checked = (e.target as HTMLInputElement).checked;
      setFormData((prev) => ({ ...prev, [name]: checked }));
    } else {
      setFormData((prev) => ({ ...prev, [name]: value }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg("");
    setSuccessMsg("");
    
    try {
      await authApi.updateMe({ ...formData, notifications_enabled: formData.notifications_enabled.toString() });
      await refreshUser();
      setSuccessMsg("Profile updated successfully");
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || "Failed to update profile.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-stone-900">Settings</h1>
        <p className="mt-1 text-sm text-stone-500">Manage your account preferences and personal details.</p>
      </div>

      <div className="rounded-2xl bg-white shadow-sm ring-1 ring-stone-900/5">
        <div className="px-6 py-5 border-b border-stone-100 flex items-center justify-between">
          <h2 className="text-base font-semibold text-stone-900">Profile Information</h2>
          {user.email_verified && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
              <CheckCircle2 size={14} className="text-emerald-500" />
              Verified Account
            </span>
          )}
        </div>

        <form onSubmit={handleSubmit} className="p-6">
          {errorMsg && (
            <div className="mb-6 rounded-xl bg-red-50 p-4 text-sm text-red-600">
              {errorMsg}
            </div>
          )}
          {successMsg && (
            <div className="mb-6 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-600">
              {successMsg}
            </div>
          )}

          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <label htmlFor="full_name" className="block text-sm font-medium text-stone-700">Full Name</label>
              <input
                type="text"
                id="full_name"
                name="full_name"
                value={formData.full_name}
                onChange={handleChange}
                className="mt-1 block w-full rounded-xl border-stone-200 shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm px-4 py-2 flex items-center border"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-stone-700">Email Address</label>
              <div className="mt-1 flex gap-2 items-center w-full px-4 py-2 border rounded-xl border-stone-200 bg-stone-50 text-stone-500 sm:text-sm">
                <span>{user.email}</span>
              </div>
              <p className="mt-1 text-xs text-stone-400">Signed in via {user.auth_provider === 'google' ? 'Google' : 'Email'}</p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-stone-700">Username</label>
              <div className="mt-1 flex gap-2 items-center w-full px-4 py-2 border rounded-xl border-stone-200 bg-stone-50 text-stone-500 sm:text-sm">
                <span>@{user.username}</span>
              </div>
            </div>

            <div>
              <label htmlFor="phone" className="block text-sm font-medium text-stone-700">Phone Number <span className="text-stone-400 font-normal">(optional)</span></label>
              <input
                type="tel"
                id="phone"
                name="phone"
                value={formData.phone}
                onChange={handleChange}
                className="mt-1 block w-full rounded-xl border-stone-200 shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm px-4 py-2 flex items-center border"
              />
            </div>

            <div>
              <label htmlFor="timezone" className="block text-sm font-medium text-stone-700">Timezone</label>
              <select
                id="timezone"
                name="timezone"
                value={formData.timezone}
                onChange={handleChange}
                className="mt-1 block w-full rounded-xl border-stone-200 shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm px-4 py-2.5 flex items-center border bg-white"
              >
                <option value="UTC">UTC</option>
                <option value="America/New_York">Eastern Time (US)</option>
                <option value="America/Chicago">Central Time (US)</option>
                <option value="America/Los_Angeles">Pacific Time (US)</option>
                <option value="Europe/London">London (GMT)</option>
              </select>
            </div>

            <div>
              <label htmlFor="language" className="block text-sm font-medium text-stone-700">Language</label>
              <select
                id="language"
                name="language"
                value={formData.language}
                onChange={handleChange}
                className="mt-1 block w-full rounded-xl border-stone-200 shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm px-4 py-2.5 flex items-center border bg-white"
              >
                <option value="en">English (US)</option>
                <option value="en-gb">English (UK)</option>
                <option value="es">Español</option>
                <option value="fr">Français</option>
              </select>
            </div>

            <div>
              <label htmlFor="default_currency" className="block text-sm font-medium text-stone-700">Default Currency</label>
              <select
                id="default_currency"
                name="default_currency"
                value={formData.default_currency}
                onChange={handleChange}
                className="mt-1 block w-full rounded-xl border-stone-200 shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm px-4 py-2.5 flex items-center border bg-white"
              >
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
                <option value="CAD">CAD ($)</option>
              </select>
            </div>

            <div>
              <label htmlFor="date_format" className="block text-sm font-medium text-stone-700">Date Format</label>
              <select
                id="date_format"
                name="date_format"
                value={formData.date_format}
                onChange={handleChange}
                className="mt-1 block w-full rounded-xl border-stone-200 shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm px-4 py-2.5 flex items-center border bg-white"
              >
                <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                <option value="YYYY-MM-DD">YYYY-MM-DD</option>
              </select>
            </div>
            
            <div className="flex items-center pt-6">
              <input
                type="checkbox"
                id="notifications_enabled"
                name="notifications_enabled"
                checked={formData.notifications_enabled}
                onChange={handleChange}
                className="h-4 w-4 rounded border-stone-300 text-brand-600 focus:ring-brand-600"
              />
              <label htmlFor="notifications_enabled" className="ml-3 block text-sm font-medium text-stone-700">
                Enable Email Notifications
              </label>
            </div>
          </div>

          <div className="mt-8 flex justify-end pt-5 border-t border-stone-100">
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center justify-center rounded-xl bg-brand-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-brand-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 disabled:opacity-50"
            >
              {loading ? <Loader2 size={18} className="animate-spin" /> : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
