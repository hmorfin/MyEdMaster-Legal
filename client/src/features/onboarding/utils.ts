import {
  COUNTRY_USA_PAYLOAD,
  DISABILITY_STATUS,
  EMPLOYMENT_TYPES,
  INCOME_BRACKETS,
  INITIAL_ONBOARDING_STATE,
  MARITAL_STATUS,
  PROFESSIONS,
  US_STATES,
  VETERAN_STATUS,
} from "@/features/onboarding/constants";
import type { Action, FieldErrors, FormState, OnboardingRequestPayload, UserProfileLike } from "@/features/onboarding/types";

const STATE_NAME_BY_CODE: Record<string, string> = {
  AL: "Alabama",
  AK: "Alaska",
  AZ: "Arizona",
  AR: "Arkansas",
  CA: "California",
  CO: "Colorado",
  CT: "Connecticut",
  DE: "Delaware",
  FL: "Florida",
  GA: "Georgia",
  HI: "Hawaii",
  ID: "Idaho",
  IL: "Illinois",
  IN: "Indiana",
  IA: "Iowa",
  KS: "Kansas",
  KY: "Kentucky",
  LA: "Louisiana",
  ME: "Maine",
  MD: "Maryland",
  MA: "Massachusetts",
  MI: "Michigan",
  MN: "Minnesota",
  MS: "Mississippi",
  MO: "Missouri",
  MT: "Montana",
  NE: "Nebraska",
  NV: "Nevada",
  NH: "New Hampshire",
  NJ: "New Jersey",
  NM: "New Mexico",
  NY: "New York",
  NC: "North Carolina",
  ND: "North Dakota",
  OH: "Ohio",
  OK: "Oklahoma",
  OR: "Oregon",
  PA: "Pennsylvania",
  RI: "Rhode Island",
  SC: "South Carolina",
  SD: "South Dakota",
  TN: "Tennessee",
  TX: "Texas",
  UT: "Utah",
  VT: "Vermont",
  VA: "Virginia",
  WA: "Washington",
  WV: "West Virginia",
  WI: "Wisconsin",
  WY: "Wyoming",
};

function normalizeWhitespace(value: string): string {
  return value.trim().replace(/\s+/g, " ");
}

function normalizeOptionValue(value: string | undefined | null, options: readonly string[]): string {
  if (!value) return "";
  const normalizedInput = normalizeWhitespace(value).toLowerCase();
  const matchedOption = options.find((option) => normalizeWhitespace(option).toLowerCase() === normalizedInput);
  return matchedOption ?? "";
}

function normalizeStateValue(value: string | undefined | null): string {
  if (!value) return "";
  const normalized = normalizeWhitespace(value);
  const fromCode = STATE_NAME_BY_CODE[normalized.toUpperCase()];
  if (fromCode) return fromCode;
  return normalizeOptionValue(normalized, US_STATES);
}

export function formatDobToMMDDYYYY(yyyyMMdd: string): string {
  if (!yyyyMMdd) return "";
  const [yyyy, mm, dd] = yyyyMMdd.split("-");
  if (!yyyy || !mm || !dd) return "";
  return `${mm}-${dd}-${yyyy}`;
}

export function onlyDigits(value: string): string {
  return value.replace(/\D/g, "");
}

export function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

export function calcAge(yyyyMMdd: string): number | null {
  if (!yyyyMMdd) return null;
  const dob = new Date(yyyyMMdd);
  if (Number.isNaN(dob.getTime())) return null;

  const now = new Date();
  let age = now.getFullYear() - dob.getFullYear();
  const monthDelta = now.getMonth() - dob.getMonth();
  if (monthDelta < 0 || (monthDelta === 0 && now.getDate() < dob.getDate())) {
    age--;
  }
  return age;
}

export function validatePhone(phone: string): boolean {
  return onlyDigits(phone).length === 10;
}

export function buildOnboardingPayload(form: FormState, email: string): OnboardingRequestPayload {
  return {
    email: email.trim(),
    phone: onlyDigits(form.phone),
    dob: form.dob,
    location: {
      country: COUNTRY_USA_PAYLOAD,
      state: form.location.state,
      county: form.location.county.trim(),
      province: form.location.province.trim(),
    },
    user_attributes: {
      profession: form.user_attributes.profession,
      employment_type: form.user_attributes.employment_type,
      veteran_status: form.user_attributes.veteran_status,
      disability_status: form.user_attributes.disability_status,
      marital_status: form.user_attributes.marital_status,
      income_bracket: form.user_attributes.income_bracket,
    },
  };
}

export function validateOnboardingForm(form: FormState, email: string): FieldErrors {
  const nextErrors: FieldErrors = {};
  const age = calcAge(form.dob);

  if (!email.trim()) nextErrors.email = "Email is required.";
  else if (!isValidEmail(email)) nextErrors.email = "Enter a valid email address.";

  if (!form.phone.trim()) nextErrors.phone = "Phone is required.";
  else if (!validatePhone(form.phone)) nextErrors.phone = "Enter a valid 10-digit phone number.";

  if (!form.dob) nextErrors.dob = "Date of birth is required.";
  else if (age === null) nextErrors.dob = "Enter a valid date of birth.";
  else if (age < 13) nextErrors.dob = "You must be at least 13 years old.";

  if (!form.location.state) nextErrors.state = "State is required.";
  if (!form.location.county.trim()) nextErrors.county = "County is required.";

  if (!form.user_attributes.profession) nextErrors.profession = "Profession is required.";
  if (!form.user_attributes.employment_type) nextErrors.employment_type = "Employment type is required.";
  if (!form.user_attributes.veteran_status) nextErrors.veteran_status = "Veteran status is required.";
  if (!form.user_attributes.disability_status) nextErrors.disability_status = "Disability status is required.";
  if (!form.user_attributes.marital_status) nextErrors.marital_status = "Marital status is required.";
  if (!form.user_attributes.income_bracket) nextErrors.income_bracket = "Income bracket is required.";

  return nextErrors;
}

export function formStateFromUserProfile(profile: UserProfileLike): FormState {
  return {
    email: profile.email ?? "",
    phone: profile.phone ?? "",
    dob: profile.dob ?? "",
    location: {
      country: COUNTRY_USA_PAYLOAD,
      state: normalizeStateValue(profile.location?.state),
      county: profile.location?.county ?? "",
      province: profile.location?.province ?? "",
    },
    user_attributes: {
      profession: normalizeOptionValue(profile.user_attributes?.profession, PROFESSIONS),
      employment_type: normalizeOptionValue(profile.user_attributes?.employment_type, EMPLOYMENT_TYPES),
      veteran_status: normalizeOptionValue(profile.user_attributes?.veteran_status, VETERAN_STATUS),
      disability_status: normalizeOptionValue(profile.user_attributes?.disability_status, DISABILITY_STATUS),
      marital_status: normalizeOptionValue(profile.user_attributes?.marital_status, MARITAL_STATUS),
      income_bracket: normalizeOptionValue(profile.user_attributes?.income_bracket, INCOME_BRACKETS),
    },
  };
}

export function onboardingFormReducer(state: FormState, action: Action): FormState {
  switch (action.type) {
    case "SET_FIELD":
      return { ...state, [action.key]: action.value };
    case "SET_LOCATION":
      return { ...state, location: { ...state.location, [action.key]: action.value } };
    case "SET_ATTR":
      return { ...state, user_attributes: { ...state.user_attributes, [action.key]: action.value } };
    case "HYDRATE":
      return action.value;
    case "RESET":
      return INITIAL_ONBOARDING_STATE;
    default:
      return state;
  }
}
