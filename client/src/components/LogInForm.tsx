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
import { getPostAuthPath, setStoredUser, setStoredUserProfile } from "@/lib/auth"
import { loginUser } from "@/features/auth/api"
import { useAsyncAction } from "@/hooks/use-async-action"

export function LoginForm({
  className,
  ...props
}: React.ComponentProps<"form">) {
  const navigate = useNavigate()
  const { loading: submitting, error: errorMsg, setError, run } = useAsyncAction()
  const [formValues, setFormValues] = useState({
    email: "",
    password: "",
  })

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)

    await run(async () => {
      const { response, payload: data } = await loginUser(formValues.email)
      if (!response.ok || data?.status !== "success" || !data.data?.id) {
        setError(data?.message || `Login failed (HTTP ${response.status}).`)
        return
      }

      setStoredUser(data.data.id, data.data.email || formValues.email.trim())
      setStoredUserProfile(data.data)
      navigate(getPostAuthPath(data.data.onboarded))
    })
  }

  return (
    <form className={cn("flex flex-col gap-6", className)} {...props} onSubmit={handleSubmit}>
      <FieldGroup>
        <div className="flex flex-col items-center gap-1 text-center">
          <h1 className="text-2xl font-bold">Login to your account</h1>
          <p className="text-muted-foreground text-sm text-balance">
            Enter your email below to login to your account
          </p>
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
            <a
              href="#"
              className="ml-auto text-sm underline-offset-4 hover:underline"
            >
              Forgot your password?
            </a>
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
        {errorMsg ? <p className="text-sm text-red-600">{errorMsg}</p> : null}
        <Field>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Logging in..." : "Login"}
          </Button>
        </Field>
      </FieldGroup>
    </form>
  )
}
