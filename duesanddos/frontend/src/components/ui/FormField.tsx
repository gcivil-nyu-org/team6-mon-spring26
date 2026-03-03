"use client";

import { forwardRef, useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { clsx } from "clsx";

interface FormFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  hint?: string;
}

export const FormField = forwardRef<HTMLInputElement, FormFieldProps>(
  ({ label, error, hint, id, className, type, ...props }, ref) => {
    const [showPassword, setShowPassword] = useState(false);
    const isPassword = type === "password";
    const inputType = isPassword && showPassword ? "text" : type;

    return (
      <div className="space-y-1">
        <label htmlFor={id} className="form-label">
          {label}
        </label>
        <div className="relative">
          <input
            ref={ref}
            id={id}
            type={inputType}
            className={clsx(
              "input-field",
              error && "input-error",
              isPassword && "pr-10",
              className
            )}
            {...props}
          />
          {isPassword && (
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-600"
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          )}
        </div>
        {error && <p className="error-text">{error}</p>}
        {hint && !error && <p className="text-xs text-stone-400 mt-1">{hint}</p>}
      </div>
    );
  }
);

FormField.displayName = "FormField";

interface FormAlertProps {
  type: "error" | "success";
  message: string;
}

export function FormAlert({ type, message }: FormAlertProps) {
  const styles = {
    error: "bg-red-50 border-red-200 text-red-700",
    success: "bg-brand-50 border-brand-200 text-brand-700",
  };
  return (
    <div className={clsx("rounded-xl border px-4 py-3 text-sm", styles[type])}>
      {message}
    </div>
  );
}
