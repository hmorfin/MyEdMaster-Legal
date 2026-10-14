import { API_BASE_URL } from "@/lib/api";
import type { UserProfileRecord } from "@/features/onboarding/types";

export type LoginResponse = {
  status: "success" | "error";
  data?: UserProfileRecord;
  message?: string;
};

export type CreateUserResponse = {
  status: "success" | "error";
  data?: {
    id: string;
    onboarded: boolean;
    createdAt: string;
  };
  message?: string;
};

function usersBase(): string {
  return `${API_BASE_URL.replace(/\/+$/, "")}/users`;
}

export async function loginUser(email: string): Promise<{ response: Response; payload: LoginResponse | null }> {
  const response = await fetch(`${usersBase()}/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim() }),
  });

  const payload = (await response.json().catch(() => null)) as LoginResponse | null;
  return { response, payload };
}

export async function createUser(input: {
  firstName: string;
  lastName: string;
  email: string;
}): Promise<{ response: Response; payload: CreateUserResponse | null }> {
  const response = await fetch(`${usersBase()}/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      first_name: input.firstName.trim(),
      last_name: input.lastName.trim(),
      email: input.email.trim(),
    }),
  });

  const payload = (await response.json().catch(() => null)) as CreateUserResponse | null;
  return { response, payload };
}
