import Link from "next/link";

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-stone-100 px-6 py-5">
        <Link href="/" className="flex items-center gap-2 w-fit">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600">
            <span className="text-sm font-bold text-white">D</span>
          </div>
          <span className="font-display text-lg font-semibold text-stone-900">
            Dues <span className="text-brand-600">&</span> Do&apos;s
          </span>
        </Link>
      </header>
      <main className="mx-auto max-w-2xl px-6 py-16">
        <h1 className="font-display text-3xl font-semibold text-stone-900">Privacy Policy</h1>
        <p className="mt-6 text-stone-500">
          We respect your privacy. Dues &amp; Do&apos;s collects only the data necessary to provide our service. We do not sell your data or show you ads. Our full Privacy Policy is being written and will appear here before public launch.
        </p>
        <Link href="/" className="mt-8 inline-block text-sm text-brand-600 hover:underline">
          ← Back to home
        </Link>
      </main>
    </div>
  );
}
