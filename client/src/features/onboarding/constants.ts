import type { FormState } from "@/features/onboarding/types";

export const COUNTRY_USA_DISPLAY = "USA";
export const COUNTRY_USA_PAYLOAD = "United States";

export const US_STATES = [
  "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
  "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
  "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
  "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
  "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
  "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
  "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming",
] as const;

export const PROFESSIONS = [
  "Legal Professional",
  "Healthcare Professional",
  "Education Professional",
  "Government Employee",
  "Military",
  "IT Professional",
  "Finance Professional",
  "Business Owner",
  "Student",
  "Retired",
  "Other",
] as const;

export const EMPLOYMENT_TYPES = [
  "Full-Time",
  "Part-Time",
  "Self-Employed",
  "Contract",
  "Temporary",
  "Student",
  "Unemployed",
  "Retired",
] as const;
export const VETERAN_STATUS = ["Veteran", "Non-Veteran", "Active Duty", "Prefer Not to Say"] as const;
export const DISABILITY_STATUS = ["None", "Yes", "Prefer Not to Say"] as const;
export const MARITAL_STATUS = ["Single", "Married", "Divorced", "Prefer Not to Say"] as const;
export const INCOME_BRACKETS = [
  "Below $25,000",
  "$25,000 - $34,999",
  "$35,000 - $49,999",
  "$50,000 - $74,999",
  "$75,000 - $99,999",
  "$100,000 - $149,999",
  "$150,000+",
] as const;

export const INPUT_CLASSNAME =
  "w-full rounded-lg border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none focus:border-slate-900 focus:ring-0 dark:border-[#3a3a3c] dark:bg-[#111113] dark:text-slate-100 dark:focus:border-[#5a5a5e]";
export const SELECT_CLASSNAME =
  "w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none focus:border-slate-900 focus:ring-0 dark:border-[#3a3a3c] dark:bg-[#111113] dark:text-slate-100 dark:focus:border-[#5a5a5e]";

export const INITIAL_ONBOARDING_STATE: FormState = {
  email: "",
  phone: "",
  dob: "",
  location: {
    country: COUNTRY_USA_PAYLOAD,
    state: "",
    county: "",
    province: "",
  },
  user_attributes: {
    profession: "",
    employment_type: "",
    veteran_status: "",
    disability_status: "",
    marital_status: "",
    income_bracket: "",
  },
};
