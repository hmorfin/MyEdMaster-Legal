export type LocationPayload = {
  country: string;
  state: string;
  county: string;
  province: string;
};

export type UserAttributesPayload = {
  profession: string;
  employment_type: string;
  veteran_status: string;
  disability_status: string;
  marital_status: string;
  income_bracket: string;
};

export type OnboardingRequestPayload = {
  email: string;
  phone: string;
  dob: string;
  location: LocationPayload;
  user_attributes: UserAttributesPayload;
};

export type OnboardingResponsePayload = {
  status: "success" | "error";
  data?: { id: string };
  message?: string;
  errors?: Record<string, string>;
};

export type UserProfileRecord = {
  id: string;
  first_name?: string;
  last_name?: string;
  email: string;
  phone?: string;
  dob?: string | null;
  location?: Partial<LocationPayload> | null;
  user_attributes?: Partial<UserAttributesPayload> | null;
  onboarded: boolean;
  created_at?: string | null;
};

export type UserProfileLike = Partial<UserProfileRecord> & {
  email?: string;
  phone?: string;
  dob?: string | null;
  location?: Partial<LocationPayload> | null;
  user_attributes?: Partial<UserAttributesPayload> | null;
};

export type FieldErrors = Partial<Record<string, string>>;

export type FormState = {
  email: string;
  phone: string;
  dob: string;
  location: LocationPayload;
  user_attributes: UserAttributesPayload;
};

export type Action =
  | { type: "SET_FIELD"; key: keyof Omit<FormState, "location" | "user_attributes">; value: string }
  | { type: "SET_LOCATION"; key: keyof LocationPayload; value: string }
  | { type: "SET_ATTR"; key: keyof UserAttributesPayload; value: string }
  | { type: "HYDRATE"; value: FormState }
  | { type: "RESET" };
