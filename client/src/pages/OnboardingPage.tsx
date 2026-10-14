import { useState } from "react";
import { useNavigate } from "react-router-dom";
import OnboardingProfileForm from "@/features/onboarding/components/OnboardingProfileForm";
import { submitOnboarding } from "@/features/onboarding/api";
import type { OnboardingRequestPayload } from "@/features/onboarding/types";
import {
  clearPendingOnboardingUser,
  getPendingOnboardingUserEmail,
  getPendingOnboardingUserId,
  getPostAuthPath,
  getStoredUserEmail,
  getStoredUserId,
  setStoredUser,
  setStoredUserProfile,
} from "@/lib/auth";

export default function OnboardingPage() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [serverMsg, setServerMsg] = useState<string | null>(null);

  const storedUserId = getStoredUserId();
  const pendingUserId = getPendingOnboardingUserId();
  const userId = storedUserId || pendingUserId;
  const storedUserEmail = getStoredUserEmail();
  const pendingUserEmail = getPendingOnboardingUserEmail();
  const emailValue = storedUserEmail?.trim() || pendingUserEmail?.trim() || "";

  async function handleSubmit(payload: OnboardingRequestPayload, resolvedEmail: string) {
    setServerMsg(null);
    setSubmitting(true);

    try {
      if (!userId) {
        setServerMsg("No registered user found. Please complete registration first.");
        return;
      }

      const { response, data } = await submitOnboarding(userId, payload);

      if (!response.ok) {
        const enumErrorText = data?.errors
          ? ` ${Object.entries(data.errors)
              .map(([field, detail]) => `${field}: ${detail}`)
              .join(" | ")}`
          : "";
        setServerMsg((data?.message || `Onboarding failed (HTTP ${response.status}).`) + enumErrorText);
        return;
      }

      if (data?.status === "success" && data.data) {
        setStoredUser(data.data.id || userId, resolvedEmail);
        setStoredUserProfile(payload);
        clearPendingOnboardingUser();
        navigate(getPostAuthPath(true));
        return;
      }

      setServerMsg(data?.message || "Unexpected response from server.");
    } catch (error: unknown) {
      setServerMsg(error instanceof Error ? error.message : "Network error while submitting onboarding.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <OnboardingProfileForm
      title="Onboarding"
      description="Help us with the details below to personalize the legal chatbot for you."
      submitLabel="Register"
      initialEmail={emailValue}
      isSubmitting={submitting}
      serverMessage={serverMsg}
      onSubmit={handleSubmit}
    />
  );
}
