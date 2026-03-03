"use client";

import Link from "next/link";
import Image from "next/image";
import { useState } from "react";
import {
  Receipt,
  CheckSquare,
  Users,
  ArrowRight,
  Bell,
  BarChart3,
  Shield,
  Menu,
  X,
  ChevronRight,
  Wallet,
  Sparkles,
  MessageCircle,
} from "lucide-react";

function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2">
      <Image src="/logo.png" alt="Dues & Do's Logo" width={32} height={32} className="rounded-lg object-contain" />
      <span className="font-display text-lg font-semibold text-stone-900">
        Dues <span className="text-brand-600">&</span> Do&apos;s
      </span>
    </Link>
  );
}

function Navbar() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-50 border-b border-stone-100 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
        <Logo />
        {/* Desktop nav */}
        <nav className="hidden items-center gap-8 md:flex">
          <a href="#features" className="text-sm text-stone-600 transition-colors hover:text-stone-900">
            Features
          </a>
          <a href="#how-it-works" className="text-sm text-stone-600 transition-colors hover:text-stone-900">
            How it works
          </a>
        </nav>
        <div className="hidden items-center gap-3 md:flex">
          <Link href="/login" className="btn-secondary py-2 text-sm">
            Log in
          </Link>
          <Link href="/register" className="btn-primary py-2 text-sm">
            Get started free
          </Link>
        </div>
        {/* Mobile menu toggle */}
        <button
          className="rounded-lg p-2 text-stone-600 hover:bg-stone-100 md:hidden"
          onClick={() => setOpen(!open)}
          aria-label="Toggle menu"
        >
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>
      {/* Mobile drawer */}
      {open && (
        <div className="border-t border-stone-100 bg-white px-4 pb-6 pt-4 md:hidden">
          <nav className="flex flex-col gap-4">
            <a href="#features" onClick={() => setOpen(false)} className="text-sm font-medium text-stone-700">
              Features
            </a>
            <a href="#how-it-works" onClick={() => setOpen(false)} className="text-sm font-medium text-stone-700">
              How it works
            </a>
            <hr className="border-stone-100" />
            <Link href="/login" className="btn-secondary text-center text-sm">
              Log in
            </Link>
            <Link href="/register" className="btn-primary text-center text-sm">
              Get started free
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden bg-white py-20 sm:py-28 lg:py-36">
      {/* Background decoration */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 overflow-hidden"
      >
        <div className="absolute -top-40 right-0 h-[600px] w-[600px] rounded-full bg-brand-50 opacity-60 blur-3xl" />
        <div className="absolute -bottom-20 left-0 h-[400px] w-[400px] rounded-full bg-brand-100 opacity-40 blur-3xl" />
      </div>

      <div className="relative mx-auto max-w-4xl px-4 text-center sm:px-6 lg:px-8">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50 px-4 py-2 text-xs font-medium text-brand-700">
          <span className="h-1.5 w-1.5 rounded-full bg-brand-500" />
          Built for real households
        </div>
        <h1 className="font-display text-4xl font-semibold leading-tight text-stone-900 sm:text-5xl lg:text-6xl">
          Living together,{" "}
          <span className="text-brand-600 italic">better</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-stone-500">
          Track shared expenses, rotate chores, and collaborate effortlessly — all in one place. Say goodbye to messy spreadsheets and hello to peaceful shared living.
        </p>
        <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          <Link href="/register" className="btn-primary w-full px-8 py-3.5 sm:w-auto text-base">
            Get started — it&apos;s free
            <ArrowRight size={16} />
          </Link>
          <Link href="/login" className="btn-secondary w-full px-8 py-3.5 sm:w-auto text-base">
            Log in
          </Link>
        </div>
      </div>
    </section>
  );
}

function ProblemSection() {
  const problems = [
    {
      icon: <Wallet className="text-brand-600" size={24} />,
      title: "Who owes who?",
      body: "Tracking who paid what can be confusing. We make it easy to see shared expenses so everyone is always on the same page.",
    },
    {
      icon: <Sparkles className="text-brand-600" size={24} />,
      title: "Sharing household chores",
      body: "A clear system helps everyone pitch in. Rotate tasks effortlessly and keep your home tidy, together.",
    },
    {
      icon: <MessageCircle className="text-brand-600" size={24} />,
      title: "Friendly reminders",
      body: "Helpful nudges make it easy to manage shared bills without the awkward conversations.",
    },
  ];

  return (
    <section className="bg-stone-50 py-20 sm:py-28">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl">
          <h2 className="font-display text-3xl font-semibold text-stone-900 sm:text-4xl">
            Shared living is great.{" "}
            <span className="text-stone-400">Let&apos;s keep it that way.</span>
          </h2>
          <p className="mt-4 text-stone-500">
            A simple, clear system helps everyone pitch in so your home remains peaceful and organized.
          </p>
        </div>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {problems.map((p) => (
            <div key={p.title} className="card p-6">
              <div className="mb-4">{p.icon}</div>
              <h3 className="mb-2 font-semibold text-stone-900">{p.title}</h3>
              <p className="text-sm leading-relaxed text-stone-500">{p.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FeaturesSection() {
  const features = [
    {
      icon: Receipt,
      title: "Expense splitting",
      description:
        "Log any shared expense and split it by percentage, equal shares, or custom amounts. Everyone sees the same numbers.",
    },
    {
      icon: CheckSquare,
      title: "Chore scheduling",
      description:
        "Assign chores, set frequencies, and rotate automatically. A shared schedule means no one can say they forgot.",
    },
    {
      icon: Users,
      title: "Household management",
      description:
        "Create your household, invite roommates, and manage everything from one dashboard. It's your home, organized.",
    },
    {
      icon: Bell,
      title: "Gentle reminders",
      description:
        "Dues & Do's handles the nudge so you don't have to. Automated reminders keep things moving without the awkwardness.",
    },
    {
      icon: BarChart3,
      title: "Running balances",
      description:
        "A live ledger shows who owes what at a glance. Settle up in one click and start fresh.",
    },
    {
      icon: Shield,
      title: "Private & secure",
      description:
        "Your household data stays yours. We don't sell it, share it, or use it to show you ads.",
    },
  ];

  return (
    <section id="features" className="bg-white py-20 sm:py-28">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="font-display text-3xl font-semibold text-stone-900 sm:text-4xl">
            Everything your household needs
          </h2>
          <p className="mt-4 text-stone-500">
            Simple tools, thoughtfully designed for the reality of shared living.
          </p>
        </div>
        <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div
              key={f.title}
              className="group rounded-2xl border border-stone-100 bg-stone-50 p-6 transition-all duration-200 hover:border-brand-200 hover:bg-brand-50/40"
            >
              <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-brand-100 text-brand-700 transition-colors group-hover:bg-brand-200">
                <f.icon size={20} />
              </div>
              <h3 className="mb-2 font-semibold text-stone-900">{f.title}</h3>
              <p className="text-sm leading-relaxed text-stone-500">{f.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function HowItWorks() {
  const steps = [
    {
      num: "01",
      title: "Create your household",
      body: "Sign up, name your household, and send invite links to your roommates. They join in one click — no friction.",
    },
    {
      num: "02",
      title: "Log expenses & set up chores",
      body: "Add bills as they come in. Set up recurring chores and decide who does what. Takes five minutes to get started.",
    },
    {
      num: "03",
      title: "Stay on the same page",
      body: "Everyone can see balances, chore status, and history in real time. Settle up whenever it suits you.",
    },
  ];

  return (
    <section id="how-it-works" className="bg-stone-50 py-20 sm:py-28">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="font-display text-3xl font-semibold text-stone-900 sm:text-4xl">
            Up and running in minutes
          </h2>
          <p className="mt-4 text-stone-500">
            Designed to be so simple, your busiest roommate will actually use it.
          </p>
        </div>
        <div className="mt-14 grid gap-8 sm:grid-cols-3">
          {steps.map((step, i) => (
            <div key={step.num} className="relative">
              {i < steps.length - 1 && (
                <div
                  aria-hidden
                  className="absolute left-full top-6 hidden h-px w-full -translate-x-4 bg-stone-200 sm:block"
                  style={{ width: "calc(100% - 2rem)" }}
                />
              )}
              <div className="font-display text-4xl font-bold text-brand-200">{step.num}</div>
              <h3 className="mt-3 font-semibold text-stone-900">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-stone-500">{step.body}</p>
            </div>
          ))}
        </div>
        <div className="mt-14 text-center">
          <Link href="/register" className="btn-primary inline-flex px-8 py-3.5 text-base">
            Set up your household
            <ChevronRight size={16} />
          </Link>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-stone-100 bg-white py-10">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center justify-between gap-6 sm:flex-row">
          <Logo />
          <nav className="flex flex-wrap items-center justify-center gap-6">
            <Link href="/terms" className="text-xs text-stone-400 transition-colors hover:text-stone-600">
              Terms of Service
            </Link>
            <Link href="/privacy" className="text-xs text-stone-400 transition-colors hover:text-stone-600">
              Privacy Policy
            </Link>
            <Link href="/login" className="text-xs text-stone-400 transition-colors hover:text-stone-600">
              Log in
            </Link>
            <Link href="/register" className="text-xs text-stone-400 transition-colors hover:text-stone-600">
              Sign up
            </Link>
          </nav>
          <p className="text-xs text-stone-400">
            © {new Date().getFullYear()} Dues &amp; Do&apos;s
          </p>
        </div>
      </div>
    </footer>
  );
}

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="flex-1">
        <Hero />
        <ProblemSection />
        <FeaturesSection />
        <HowItWorks />
      </main>
      <Footer />
    </div>
  );
}
