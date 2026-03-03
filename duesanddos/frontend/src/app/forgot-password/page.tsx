"use client";

import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState } from "react";
import { Loader2, ArrowLeft, MailCheck } from "lucide-react";
import { AuthLayout } from "@/components/layout/AuthLayout";
import { FormField, FormAlert } from "@/components/ui/FormField";
import { authApi } from "@/lib/api";
import { parseApiError } from "@/lib/errors";

const schema = z.object({
  email: z.string().email("Enter a valid email address"),
});

type FormData = z.infer<typeof schema>;

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const [apiError, setApiError] = useState("");
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    setLoading(true);
    setApiError("");
    try {
      await authApi.forgotPassword({ email: data.email });
      setSent(true);
    } catch (err) {
      setApiError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <AuthLayout title="Check your inbox">
        <div className="space-y-6 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-brand-100">
            <MailCheck size={24} className="text-brand-600" />
          </div>
          <div className="space-y-2">
            <p className="text-stone-600">
              If an account exists for that email, we&apos;ve sent a password reset link. Check your inbox — it expires in 15 minutes.
            </p>
            <p className="text-sm text-stone-400">
              Don&apos;t see it? Check your spam folder.
            </p>
          </div>
          <Link href="/login" className="btn-secondary inline-flex gap-2">
            <ArrowLeft size={16} />
            Back to login
          </Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Forgot your password?"
      subtitle="No worries. We'll send you a reset link."
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
        {apiError && <FormAlert type="error" message={apiError} />}

        <FormField
          id="email"
          label="Email address"
          type="email"
          placeholder="you@example.com"
          autoComplete="email"
          error={errors.email?.message}
          {...register("email")}
        />

        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full py-3"
        >
          {loading ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Sending link…
            </>
          ) : (
            "Send reset link"
          )}
        </button>

        <Link
          href="/login"
          className="flex items-center justify-center gap-2 text-sm text-stone-500 hover:text-stone-700"
        >
          <ArrowLeft size={14} />
          Back to login
        </Link>
      </form>
    </AuthLayout>
  );
}
