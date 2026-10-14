import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Field,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { clearPendingOnboardingUser, getPostAuthPath, setPendingOnboardingUser } from "@/lib/auth"
import { createUser } from "@/features/auth/api"
import { useAsyncAction } from "@/hooks/use-async-action"

export function RegisterForm({
  className,
  ...props
}: React.ComponentProps<"form">) {
  const navigate = useNavigate()
  const { loading: submitting, error: errorMsg, setError, run } = useAsyncAction()
  const [formValues, setFormValues] = useState({
    firstName: "",
    lastName: "",
    email: "",
    password: "",
    confirmPassword: "",
  })
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)

    if (formValues.password !== formValues.confirmPassword) {
      setError("Password and confirm password must match.")
      return
    }

    await run(async () => {
      const { response, payload: data } = await createUser({
        firstName: formValues.firstName,
        lastName: formValues.lastName,
        email: formValues.email,
      });

      if (!response.ok || data?.status !== "success" || !data.data?.id) {
        setError(data?.message || `Registration failed (HTTP ${response.status}).`)
        return
      }

      clearPendingOnboardingUser()
      setPendingOnboardingUser(data.data.id, formValues.email.trim())
      navigate(getPostAuthPath(false))
    })
  }

  return (
    <form className={cn("flex flex-col gap-6", className)} {...props} onSubmit={handleSubmit}>
      <FieldGroup>
        <div className="flex flex-col items-center gap-1 text-center">
          <h1 className="text-2xl font-bold">Register a new account</h1>
          <p className="text-muted-foreground text-sm text-balance">
            Enter your details
          </p>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field>
            <FieldLabel htmlFor="first-name">First Name</FieldLabel>
            <Input
              id="first-name"
              type="text"
              placeholder="John"
              autoComplete="given-name"
              required
              value={formValues.firstName}
              onChange={(event) => setFormValues((current) => ({ ...current, firstName: event.target.value }))}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="last-name">Last Name</FieldLabel>
            <Input
              id="last-name"
              type="text"
              placeholder="Appleseed"
              autoComplete="family-name"
              required
              value={formValues.lastName}
              onChange={(event) => setFormValues((current) => ({ ...current, lastName: event.target.value }))}
            />
          </Field>
        </div>
        <Field>
          <FieldLabel htmlFor="email">Email</FieldLabel>
          <Input
            id="email"
            type="email"
            placeholder="j.appleseed@example.com"
            required
            value={formValues.email}
            onChange={(event) => setFormValues((current) => ({ ...current, email: event.target.value }))}
          />
        </Field>
        <Field>
          <div className="flex items-center">
            <FieldLabel htmlFor="password">Password</FieldLabel>
          </div>
          <Input
            id="password"
            type="password"
            required
            placeholder="********"
            value={formValues.password}
            onChange={(event) => setFormValues((current) => ({ ...current, password: event.target.value }))}
          />
        </Field>
        <Field>
          <div className="flex items-center">
            <FieldLabel htmlFor="confirm-password">Confirm Password</FieldLabel>
          </div>
          <Input
            id="confirm-password"
            type="password"
            required
            placeholder="********"
            value={formValues.confirmPassword}
            onChange={(event) => setFormValues((current) => ({ ...current, confirmPassword: event.target.value }))}
          />
        </Field>
        {errorMsg ? <p className="text-sm text-red-600">{errorMsg}</p> : null}
        <Field>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Creating account..." : "Continue"}
          </Button>
        </Field>
      </FieldGroup>
    </form>
  )
}
