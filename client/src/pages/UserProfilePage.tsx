import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import OnboardingProfileForm from "@/features/onboarding/components/OnboardingProfileForm";
import { loginUser } from "@/features/auth/api";
import { submitOnboarding } from "@/features/onboarding/api";
import { formStateFromUserProfile } from "@/features/onboarding/utils";
import type { FormState, OnboardingRequestPayload, UserProfileLike } from "@/features/onboarding/types";
import { getStoredUserEmail, getStoredUserId, getStoredUserProfile, setStoredUser, setStoredUserProfile } from "@/lib/auth";

export default function UserProfilePage() {
  const userId = getStoredUserId();
  const storedEmail = getStoredUserEmail() ?? "";
  const [initialForm, setInitialForm] = useState<FormState | undefined>(undefined);
  const [initialEmail, setInitialEmail] = useState(storedEmail);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [serverMsg, setServerMsg] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;

    async function loadProfile() {
      if (!userId) return;
      const cachedProfile = getStoredUserProfile<UserProfileLike | OnboardingRequestPayload>();

      if (cachedProfile && !isCancelled) {
        setInitialForm(formStateFromUserProfile(cachedProfile));
      }

      if (!storedEmail) {
        setServerMsg("Missing saved email. Please log in again.");
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setServerMsg(null);

      try {
        const { response, payload } = await loginUser(storedEmail);

        if (!response.ok || payload?.status !== "success" || !payload.data?.id) {
          if (!isCancelled) {
            setServerMsg(payload?.message || `Unable to load your profile (HTTP ${response.status}).`);
          }
          return;
        }

        if (!isCancelled) {
          setStoredUserProfile(payload.data);
          setInitialForm(formStateFromUserProfile(payload.data));
          setInitialEmail(payload.data.email || storedEmail);
        }
      } catch (error: unknown) {
        if (!isCancelled) {
          setServerMsg(error instanceof Error ? error.message : "Unable to load your profile.");
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadProfile();

    return () => {
      isCancelled = true;
    };
  }, [storedEmail, userId]);

  if (!userId) {
    return <Navigate to="/log-in" replace />;
  }

  const activeUserId = userId;

  async function handleSubmit(payload: OnboardingRequestPayload, resolvedEmail: string) {
    setServerMsg(null);
    setIsSubmitting(true);

    try {
      const { response, data } = await submitOnboarding(activeUserId, payload);

      if (!response.ok) {
        const enumErrorText = data?.errors
          ? ` ${Object.entries(data.errors)
              .map(([field, detail]) => `${field}: ${detail}`)
              .join(" | ")}`
          : "";
        setServerMsg((data?.message || `Profile update failed (HTTP ${response.status}).`) + enumErrorText);
        return;
      }

      if (data?.status === "success") {
        setStoredUser(activeUserId, resolvedEmail);
        setStoredUserProfile(payload);
        setServerMsg("Profile updated successfully.");
        return;
      }

      setServerMsg(data?.message || "Unexpected response from server.");
    } catch (error: unknown) {
      setServerMsg(error instanceof Error ? error.message : "Network error while updating your profile.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <OnboardingProfileForm
      title="Profile"
      description="Review and update the information we use to personalize your experience."
      submitLabel="Save changes"
      initialEmail={initialEmail}
      initialForm={initialForm}
      isInitialLoading={isLoading}
      isSubmitting={isSubmitting}
      serverMessage={serverMsg}
      onSubmit={handleSubmit}
    />
  );
}
