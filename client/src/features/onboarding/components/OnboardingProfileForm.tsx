import { useEffect, useMemo, useReducer, useState, type FormEvent, type ReactNode } from "react";
import { Input } from "@/components/ui/input";
import { FieldLabel } from "@/components/ui/field";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  COUNTRY_USA_DISPLAY,
  DISABILITY_STATUS,
  EMPLOYMENT_TYPES,
  INITIAL_ONBOARDING_STATE,
  INCOME_BRACKETS,
  MARITAL_STATUS,
  PROFESSIONS,
  US_STATES,
  VETERAN_STATUS,
} from "@/features/onboarding/constants";
import { buildOnboardingPayload, onboardingFormReducer, validateOnboardingForm } from "@/features/onboarding/utils";
import type { FieldErrors, FormState, OnboardingRequestPayload } from "@/features/onboarding/types";

const ONBOARDING_INPUT_CLASS =
  "w-full dark:border-[#3a3a3c] dark:bg-[#111113] dark:text-slate-100 dark:focus-visible:border-[#5a5a5e]";
const ONBOARDING_SELECT_CLASS =
  "w-full dark:border-[#3a3a3c] dark:bg-[#111113] dark:text-slate-100 dark:focus-visible:border-[#5a5a5e]";

function InputGroup({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-2">
      <FieldLabel className="block pt-2 text-sm font-medium text-slate-900 dark:text-slate-100">
        {label}
      </FieldLabel>
      {children}
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </div>
  );
}

type OnboardingProfileFormProps = {
  title: string;
  description: string;
  submitLabel: string;
  initialEmail?: string;
  initialForm?: FormState;
  isInitialLoading?: boolean;
  isSubmitting?: boolean;
  serverMessage?: string | null;
  onSubmit: (payload: OnboardingRequestPayload, emailValue: string) => Promise<void> | void;
};

export default function OnboardingProfileForm({
  title,
  description,
  submitLabel,
  initialEmail,
  initialForm,
  isInitialLoading = false,
  isSubmitting = false,
  serverMessage,
  onSubmit,
}: OnboardingProfileFormProps) {
  const [form, dispatch] = useReducer(onboardingFormReducer, initialForm ?? INITIAL_ONBOARDING_STATE);
  const [errors, setErrors] = useState<FieldErrors>({});

  useEffect(() => {
    if (!initialForm) return;
    dispatch({ type: "HYDRATE", value: initialForm });
  }, [initialForm]);

  const emailValue = useMemo(() => form.email.trim() || initialEmail?.trim() || "", [form.email, initialEmail]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();

    const validationErrors = validateOnboardingForm(form, emailValue);
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) return;

    await onSubmit(buildOnboardingPayload(form, emailValue), emailValue);
  }

  return (
    <main className="min-h-screen bg-white dark:bg-black">
      <div className="mx-auto max-w-2xl px-5 py-10">
        <div className="rounded-2xl border border-transparent p-1 dark:border-[#2c2c2e]">
          <div className="rounded-2xl bg-transparent dark:bg-[#1c1c1e] dark:px-5 dark:py-6">
            <header className="mb-8">
              <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">{title}</h1>
              <p className="mt-2 text-sm text-black dark:text-white">{description}</p>
            </header>

            {isInitialLoading ? (
              <p className="text-sm text-black dark:white">Loading your saved profile...</p>
            ) : (
              <form className="space-y-10" onSubmit={handleSubmit} noValidate>
                <section className="space-y-5">
                  <h2 className="text-lg font-semibold text-black dark:text-white">Basic Information</h2>

                  <InputGroup label="Email" error={errors.email}>
                    <Input
                      className={ONBOARDING_INPUT_CLASS}
                      type="email"
                      value={emailValue}
                      onChange={(event) => dispatch({ type: "SET_FIELD", key: "email", value: event.target.value })}
                      placeholder="j.appleseed@icloud.com"
                      autoComplete="email"
                      disabled
                    />
                  </InputGroup>

                  <InputGroup label="Phone" error={errors.phone}>
                    <Input
                      className={ONBOARDING_INPUT_CLASS}
                      inputMode="tel"
                      value={form.phone}
                      onChange={(event) => dispatch({ type: "SET_FIELD", key: "phone", value: event.target.value })}
                      placeholder="+1 (234)-567-890"
                      autoComplete="tel"
                    />
                  </InputGroup>

                  <InputGroup label="Date of Birth" error={errors.dob}>
                    <Input
                      className={`${ONBOARDING_INPUT_CLASS} onboarding-date-input [color-scheme:light] dark:[color-scheme:dark]`}
                      type="date"
                      value={form.dob}
                      onChange={(event) => dispatch({ type: "SET_FIELD", key: "dob", value: event.target.value })}
                    />
                  </InputGroup>
                </section>

                <section className="space-y-5">
                  <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Location</h2>

                  <InputGroup label="Country">
                    <Input className={ONBOARDING_INPUT_CLASS} value={COUNTRY_USA_DISPLAY} disabled />
                  </InputGroup>

                  <InputGroup label="State" error={errors.state}>
                    <Select
                      value={form.location.state}
                      onValueChange={(value) => dispatch({ type: "SET_LOCATION", key: "state", value })}
                    >
                      <SelectTrigger className={ONBOARDING_SELECT_CLASS}>
                        <SelectValue placeholder="Select a state..." />
                      </SelectTrigger>
                      <SelectContent>
                        {US_STATES.map((state) => (
                          <SelectItem key={state} value={state}>
                            {state}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </InputGroup>

                  <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                    <InputGroup label="County" error={errors.county}>
                      <Input
                        className={ONBOARDING_INPUT_CLASS}
                        value={form.location.county}
                        onChange={(event) =>
                          dispatch({ type: "SET_LOCATION", key: "county", value: event.target.value })
                        }
                        placeholder="Maricopa County"
                      />
                    </InputGroup>

                    <InputGroup label="Province (optional)">
                      <Input
                        className={ONBOARDING_INPUT_CLASS}
                        value={form.location.province}
                        onChange={(event) =>
                          dispatch({ type: "SET_LOCATION", key: "province", value: event.target.value })
                        }
                      />
                    </InputGroup>
                  </div>
                </section>

                <section className="space-y-5">
                  <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">User Attributes</h2>

                  <InputGroup label="Profession" error={errors.profession}>
                    <Select
                      value={form.user_attributes.profession}
                      onValueChange={(value) => dispatch({ type: "SET_ATTR", key: "profession", value })}
                    >
                      <SelectTrigger className={ONBOARDING_SELECT_CLASS}>
                        <SelectValue placeholder="Select a profession..." />
                      </SelectTrigger>
                      <SelectContent>
                        {PROFESSIONS.map((profession) => (
                          <SelectItem key={profession} value={profession}>
                            {profession}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </InputGroup>

                  <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                    <InputGroup label="Employment type" error={errors.employment_type}>
                      <Select
                        value={form.user_attributes.employment_type}
                        onValueChange={(value) => dispatch({ type: "SET_ATTR", key: "employment_type", value })}
                      >
                        <SelectTrigger className={ONBOARDING_SELECT_CLASS}>
                          <SelectValue placeholder="Select..." />
                        </SelectTrigger>
                        <SelectContent>
                          {EMPLOYMENT_TYPES.map((employmentType) => (
                            <SelectItem key={employmentType} value={employmentType}>
                              {employmentType}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </InputGroup>

                    <InputGroup label="Veteran status" error={errors.veteran_status}>
                      <Select
                        value={form.user_attributes.veteran_status}
                        onValueChange={(value) => dispatch({ type: "SET_ATTR", key: "veteran_status", value })}
                      >
                        <SelectTrigger className={ONBOARDING_SELECT_CLASS}>
                          <SelectValue placeholder="Select..." />
                        </SelectTrigger>
                        <SelectContent>
                          {VETERAN_STATUS.map((status) => (
                            <SelectItem key={status} value={status}>
                              {status}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </InputGroup>
                  </div>

                  <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                    <InputGroup label="Disability status" error={errors.disability_status}>
                      <Select
                        value={form.user_attributes.disability_status}
                        onValueChange={(value) => dispatch({ type: "SET_ATTR", key: "disability_status", value })}
                      >
                        <SelectTrigger className={ONBOARDING_SELECT_CLASS}>
                          <SelectValue placeholder="Select..." />
                        </SelectTrigger>
                        <SelectContent>
                          {DISABILITY_STATUS.map((status) => (
                            <SelectItem key={status} value={status}>
                              {status}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </InputGroup>

                    <InputGroup label="Marital status" error={errors.marital_status}>
                      <Select
                        value={form.user_attributes.marital_status}
                        onValueChange={(value) => dispatch({ type: "SET_ATTR", key: "marital_status", value })}
                      >
                        <SelectTrigger className={ONBOARDING_SELECT_CLASS}>
                          <SelectValue placeholder="Select..." />
                        </SelectTrigger>
                        <SelectContent>
                          {MARITAL_STATUS.map((status) => (
                            <SelectItem key={status} value={status}>
                              {status}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </InputGroup>
                  </div>

                  <InputGroup label="Income bracket" error={errors.income_bracket}>
                    <Select
                      value={form.user_attributes.income_bracket}
                      onValueChange={(value) => dispatch({ type: "SET_ATTR", key: "income_bracket", value })}
                    >
                      <SelectTrigger className={ONBOARDING_SELECT_CLASS}>
                        <SelectValue placeholder="Select..." />
                      </SelectTrigger>
                      <SelectContent>
                        {INCOME_BRACKETS.map((incomeBracket) => (
                          <SelectItem key={incomeBracket} value={incomeBracket}>
                            {incomeBracket}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </InputGroup>
                </section>

                <section className="space-y-4">
                  <Button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full rounded-lg bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-950 dark:hover:bg-slate-200"
                  >
                    {isSubmitting ? "Saving..." : submitLabel}
                  </Button>

                  {serverMessage ? <p className="text-sm text-black dark:text-white">{serverMessage}</p> : null}
                </section>
              </form>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
