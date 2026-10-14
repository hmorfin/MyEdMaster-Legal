import { API_BASE_URL } from "@/lib/api";
import type { OnboardingRequestPayload, OnboardingResponsePayload } from "@/features/onboarding/types";

function usersBase(): string {
  return `${API_BASE_URL.replace(/\/+$/, "")}/users`;
}

export async function submitOnboarding(
  userId: string,
  payload: OnboardingRequestPayload
): Promise<{ response: Response; data: OnboardingResponsePayload | null }> {
  const response = await fetch(`${usersBase()}/${userId}/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = (await response.json().catch(() => null)) as OnboardingResponsePayload | null;
  return { response, data };
}
