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
  full_name: z.string().optional(),
  username: z.string().min(3, "Username must be at least 3 characters").max(150),
  email: z.string().email("Enter a valid email address"),
  password: z
    .string()
    .min(8, "At least 8 characters")
    .regex(/[A-Z]/, "Must include an uppercase letter")
    .regex(/[a-z]/, "Must include a lowercase letter")
    .regex(/\d/, "Must include a number"),
});

type FormData = z.infer<typeof schema>;

export default function RegisterPage() {
  const { register: authRegister, loginWithGoogle } = useAuth();
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
      await authRegister(data.username, data.email, data.password, data.full_name);
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
      title="Create your account"
      subtitle="Set up your household and invite roommates in minutes."
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
        {apiError && <FormAlert type="error" message={apiError} />}

        <div className="flex justify-center flex-col gap-4">
           <GoogleLogin 
              onSuccess={handleGoogleSuccess} 
              onError={() => setApiError("Google Sign Up failed")} 
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
          id="full_name"
          label="Full name"
          placeholder="Alex Johnson"
          autoComplete="name"
          error={errors.full_name?.message}
          {...register("full_name")}
        />
        <FormField
          id="username"
          label="Username"
          placeholder="alexjohnson"
          autoComplete="username"
          error={errors.username?.message}
          {...register("username")}
        />
        <FormField
          id="email"
          label="Email address"
          type="email"
          placeholder="you@example.com"
          autoComplete="email"
          error={errors.email?.message}
          {...register("email")}
        />
        <FormField
          id="password"
          label="Password"
          type="password"
          placeholder="Min. 8 characters"
          autoComplete="new-password"
          hint="Must include uppercase, lowercase, and a number."
          error={errors.password?.message}
          {...register("password")}
        />

        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full py-3"
        >
          {loading ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Creating account…
            </>
          ) : (
            "Create account"
          )}
        </button>

        <p className="text-center text-sm text-stone-500">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-brand-600 hover:underline">
            Log in
          </Link>
        </p>

        <p className="text-center text-xs text-stone-400">
          By signing up, you agree to our{" "}
          <Link href="/terms" className="underline hover:text-stone-600">
            Terms
          </Link>{" "}
          and{" "}
          <Link href="/privacy" className="underline hover:text-stone-600">
            Privacy Policy
          </Link>
          .
        </p>
      </form>
    </AuthLayout>
  );
}
