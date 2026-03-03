export interface User {
  id: number;
  email: string;
  full_name: string;
  display_name: string;
  username: string | null;
  avatar_url: string | null;
  phone: string | null;
  timezone: string;
  language: string;
  notifications_enabled: boolean;
  default_currency: string;
  date_format: string;
  auth_provider: string;
  email_verified: boolean;
  date_joined: string;
}

export interface ApiError {
  detail?: string;
  [key: string]: string | string[] | undefined;
}
