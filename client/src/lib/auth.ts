export const USER_ID_STORAGE_KEY = "legal_chatbot_user_id";
export const USER_EMAIL_STORAGE_KEY = "legal_chatbot_user_email";
export const USER_PROFILE_STORAGE_KEY = "legal_chatbot_user_profile";
export const PENDING_ONBOARDING_USER_ID_STORAGE_KEY = "legal_chatbot_pending_user_id";
export const PENDING_ONBOARDING_EMAIL_STORAGE_KEY = "legal_chatbot_pending_user_email";

export function setStoredUser(userId: string, email: string): void {
  localStorage.setItem(USER_ID_STORAGE_KEY, userId);
  localStorage.setItem(USER_EMAIL_STORAGE_KEY, email);
}

export function getStoredUserId(): string | null {
  return localStorage.getItem(USER_ID_STORAGE_KEY);
}

export function getStoredUserEmail(): string | null {
  return localStorage.getItem(USER_EMAIL_STORAGE_KEY);
}

export function clearStoredUser(): void {
  localStorage.removeItem(USER_ID_STORAGE_KEY);
  localStorage.removeItem(USER_EMAIL_STORAGE_KEY);
  localStorage.removeItem(USER_PROFILE_STORAGE_KEY);
  localStorage.removeItem(PENDING_ONBOARDING_USER_ID_STORAGE_KEY);
  localStorage.removeItem(PENDING_ONBOARDING_EMAIL_STORAGE_KEY);
}

export function setStoredUserProfile(profile: unknown): void {
  localStorage.setItem(USER_PROFILE_STORAGE_KEY, JSON.stringify(profile));
}

export function getStoredUserProfile<T>(): T | null {
  const raw = localStorage.getItem(USER_PROFILE_STORAGE_KEY);
  if (!raw) return null;

  try {
    return JSON.parse(raw) as T;
  } catch {
    localStorage.removeItem(USER_PROFILE_STORAGE_KEY);
    return null;
  }
}

export function setPendingOnboardingUser(userId: string, email: string): void {
  localStorage.setItem(PENDING_ONBOARDING_USER_ID_STORAGE_KEY, userId);
  localStorage.setItem(PENDING_ONBOARDING_EMAIL_STORAGE_KEY, email);
}

export function getPendingOnboardingUserId(): string | null {
  return localStorage.getItem(PENDING_ONBOARDING_USER_ID_STORAGE_KEY);
}

export function getPendingOnboardingUserEmail(): string | null {
  return localStorage.getItem(PENDING_ONBOARDING_EMAIL_STORAGE_KEY);
}

export function clearPendingOnboardingUser(): void {
  localStorage.removeItem(PENDING_ONBOARDING_USER_ID_STORAGE_KEY);
  localStorage.removeItem(PENDING_ONBOARDING_EMAIL_STORAGE_KEY);
}

export function getPostAuthPath(onboarded: boolean): "/chat" | "/onboarding" {
  return onboarded ? "/chat" : "/onboarding";
}
