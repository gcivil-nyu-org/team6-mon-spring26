"use client";

import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState } from "react";
import { Loader2 } from "lucide-react";
import { AuthLayout } from "@/components/layout/AuthLayout";
import { FormField, FormAlert } from "@/components/ui/FormField";
import { useAuth } from "@/hooks/useAuth";
import { GoogleLogin } from "@react-oauth/google";
import { parseApiError } from "@/lib/errors";

const schema = z.object({
  username_or_email: z.string().min(1, "Username or email is required"),
  password: z.string().min(1, "Password is required"),
});

type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const { login, loginWithGoogle } = useAuth();
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
      await login(data.username_or_email, data.password);
    } catch (err) {
      setApiError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSuccess = async (credentialResponse: any) => {
    setLoading(true);
    setApiError("");
    try {
      if (credentialResponse.credential) {
         await loginWithGoogle(credentialResponse.credential);
      }
    } catch (err) {
      setApiError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Log in to see your household's expenses and chores."
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
        {apiError && <FormAlert type="error" message={apiError} />}

        <div className="flex justify-center flex-col gap-4">
           <GoogleLogin 
              onSuccess={handleGoogleSuccess} 
              onError={() => setApiError("Google Sign In failed")} 
              useOneTap
              theme="outline"
              size="large"
              width="100%"
           />
           <div className="relative my-2">
             <div className="absolute inset-0 flex items-center">
               <div className="w-full border-t border-stone-200" />
             </div>
             <div className="relative flex justify-center text-sm">
               <span className="bg-white px-2 text-stone-500">Or continue with email</span>
             </div>
           </div>
        </div>

        <FormField
          id="username_or_email"
          label="Username or email address"
          type="text"
          placeholder="your_username or you@example.com"
          autoComplete="username"
          error={errors.username_or_email?.message}
          {...register("username_or_email")}
        />
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <label htmlFor="password" className="form-label">
              Password
            </label>
            <Link
              href="/forgot-password"
              className="text-xs text-brand-600 hover:underline"
            >
              Forgot password?
            </Link>
          </div>
          <div className="relative">
            <FormField
              id="password"
              label=""
              type="password"
              placeholder="Your password"
              autoComplete="current-password"
              error={errors.password?.message}
              {...register("password")}
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full py-3"
        >
          {loading ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Logging in…
            </>
          ) : (
            "Log in"
          )}
        </button>

        <p className="text-center text-sm text-stone-500">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="font-medium text-brand-600 hover:underline">
            Sign up free
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}
