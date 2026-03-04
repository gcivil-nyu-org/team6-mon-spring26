import type { AxiosError } from "axios";
import type { ApiError } from "@/types";

export function parseApiError(error: unknown): string {
  const axiosError = error as AxiosError<ApiError>;
  const data = axiosError?.response?.data;

  if (!data) return "Something went wrong. Please try again.";

  if (typeof data === "string") return data;

  if (data.detail) return data.detail;

  // Collect all field errors
  const messages: string[] = [];
  for (const [key, value] of Object.entries(data)) {
    if (Array.isArray(value)) {
      messages.push(...value);
    } else if (typeof value === "string") {
      messages.push(value);
    }
  }

  return messages.join(" ") || "Something went wrong. Please try again.";
}
