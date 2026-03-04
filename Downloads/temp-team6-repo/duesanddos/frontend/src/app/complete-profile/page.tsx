"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";
import { FormField, FormAlert } from "@/components/ui/FormField";
import { useAuth } from "@/hooks/useAuth";
import { authApi } from "@/lib/api";
import { parseApiError } from "@/lib/errors";
import { useRouter } from "next/navigation";

const schema = z.object({
  username: z.string().min(3, "Username must be at least 3 characters").max(150),
});

type FormData = z.infer<typeof schema>;

export default function CompleteProfilePage() {
  const { user, refreshUser } = useAuth();
  const router = useRouter();
  const [apiError, setApiError] = useState("");
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  useEffect(() => {
    if (user?.username) {
      router.replace("/dashboard");
    }
  }, [user, router]);

  const onSubmit = async (data: FormData) => {
    setLoading(true);
    setApiError("");
    try {
      await authApi.updateMe({ username: data.username });
      await refreshUser();
      router.push("/dashboard");
    } catch (err) {
      setApiError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  };

  if (!user) return null;

  return (
    <div className="flex min-h-screen bg-stone-50 items-center justify-center p-4">
      <div className="w-full max-w-md bg-white p-8 rounded-2xl shadow-xl ring-1 ring-stone-900/5">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold tracking-tight text-stone-900">
            Choose a Username
          </h1>
          <p className="mt-2 text-sm text-stone-500">
            Almost done! Please choose a unique username to complete your profile.
          </p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
          {apiError && <FormAlert type="error" message={apiError} />}

          <FormField
            id="username"
            label="Username"
            placeholder="e.g. alexjohnson"
            autoComplete="username"
            error={errors.username?.message}
            {...register("username")}
          />

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full py-3 mt-4"
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Saving…
              </>
            ) : (
              "Complete Profile"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
