"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState, Suspense } from "react";
import { Loader2, CheckCircle, ArrowLeft, AlertTriangle } from "lucide-react";
import { AuthLayout } from "@/components/layout/AuthLayout";
import { FormField, FormAlert } from "@/components/ui/FormField";
import { authApi } from "@/lib/api";
import { parseApiError } from "@/lib/errors";

const schema = z
  .object({
    new_password: z
      .string()
      .min(8, "At least 8 characters")
      .regex(/[A-Z]/, "Must include an uppercase letter")
      .regex(/[a-z]/, "Must include a lowercase letter")
      .regex(/\d/, "Must include a number"),
    confirm_password: z.string(),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: "Passwords don't match",
    path: ["confirm_password"],
  });

type FormData = z.infer<typeof schema>;

function ResetForm() {
  const searchParams = useSearchParams();
  const uid = searchParams.get("uid");
  const token = searchParams.get("token");

  const [success, setSuccess] = useState(false);
  const [apiError, setApiError] = useState("");
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  if (!uid || !token) {
    return (
      <div className="space-y-6 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-red-100">
          <AlertTriangle size={24} className="text-red-500" />
        </div>
        <div className="space-y-2">
          <h2 className="font-semibold text-stone-900">Invalid reset link</h2>
          <p className="text-sm text-stone-500">
            This reset link is missing required parameters. Please request a new one.
          </p>
        </div>
        <Link href="/forgot-password" className="btn-primary inline-flex">
          Request new link
        </Link>
      </div>
    );
  }

  if (success) {
    return (
      <div className="space-y-6 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-brand-100">
          <CheckCircle size={24} className="text-brand-600" />
        </div>
        <div className="space-y-2">
          <p className="text-stone-600">
            Your password has been updated successfully. You can now log in with your new password.
          </p>
        </div>
        <Link href="/login" className="btn-primary inline-flex">
          Go to login
        </Link>
      </div>
    );
  }

  const onSubmit = async (data: FormData) => {
    setLoading(true);
    setApiError("");
    try {
      await authApi.resetPassword({ uid, token, new_password: data.new_password });
      setSuccess(true);
    } catch (err) {
      setApiError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
      {apiError && <FormAlert type="error" message={apiError} />}

      <FormField
        id="new_password"
        label="New password"
        type="password"
        placeholder="Min. 8 characters"
        autoComplete="new-password"
        hint="Must include uppercase, lowercase, and a number."
        error={errors.new_password?.message}
        {...register("new_password")}
      />
      <FormField
        id="confirm_password"
        label="Confirm new password"
        type="password"
        placeholder="Repeat your password"
        autoComplete="new-password"
        error={errors.confirm_password?.message}
        {...register("confirm_password")}
      />

      <button type="submit" disabled={loading} className="btn-primary w-full py-3">
        {loading ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            Saving…
          </>
        ) : (
          "Set new password"
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
  );
}

export default function ResetPasswordPage() {
  return (
    <AuthLayout
      title="Set a new password"
      subtitle="Choose a strong password you haven't used before."
    >
      <Suspense fallback={<div className="text-sm text-stone-500">Loading…</div>}>
        <ResetForm />
      </Suspense>
    </AuthLayout>
  );
}
