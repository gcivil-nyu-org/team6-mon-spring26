import Link from "next/link";

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
}

export function AuthLayout({ children, title, subtitle }: AuthLayoutProps) {
  return (
    <div className="flex min-h-screen">
      {/* Left panel — branding */}
      <div className="relative hidden flex-1 flex-col justify-between bg-brand-950 p-12 lg:flex">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 overflow-hidden"
        >
          <div className="absolute -right-20 top-0 h-96 w-96 rounded-full bg-brand-800 opacity-30 blur-3xl" />
          <div className="absolute bottom-0 left-0 h-64 w-64 rounded-full bg-brand-700 opacity-20 blur-3xl" />
        </div>

        <Link href="/" className="relative flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500">
            <span className="text-sm font-bold text-white">D</span>
          </div>
          <span className="font-display text-lg font-semibold text-white">
            Dues <span className="text-brand-400">&</span> Do&apos;s
          </span>
        </Link>

        <div className="relative space-y-8">
          <blockquote className="space-y-3">
            <p className="font-display text-2xl font-medium leading-snug text-white">
              &ldquo;Finally, a way to handle the money stuff without making things weird.&rdquo;
            </p>
            <footer className="text-sm text-brand-300">— A very relieved roommate</footer>
          </blockquote>

          <div className="grid grid-cols-2 gap-4">
            {[
              { label: "Shared bills tracked", value: "Automated" },
              { label: "Chore disputes", value: "Zero" },
            ].map((stat) => (
              <div key={stat.label} className="rounded-xl bg-brand-900/60 p-4">
                <div className="font-display text-xl font-semibold text-white">{stat.value}</div>
                <div className="mt-1 text-xs text-brand-400">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>

        <p className="relative text-xs text-brand-600">
          © {new Date().getFullYear()} Dues &amp; Do&apos;s
        </p>
      </div>

      {/* Right panel — form */}
      <div className="flex flex-1 flex-col items-center justify-center px-4 py-12 sm:px-8 lg:px-12">
        {/* Mobile logo */}
        <div className="mb-10 lg:hidden">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600">
              <span className="text-sm font-bold text-white">D</span>
            </div>
            <span className="font-display text-lg font-semibold text-stone-900">
              Dues <span className="text-brand-600">&</span> Do&apos;s
            </span>
          </Link>
        </div>

        <div className="w-full max-w-md">
          <div className="mb-8">
            <h1 className="font-display text-3xl font-semibold text-stone-900">{title}</h1>
            {subtitle && <p className="mt-2 text-sm text-stone-500">{subtitle}</p>}
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
