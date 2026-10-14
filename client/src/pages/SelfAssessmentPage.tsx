import { useState } from "react"
import { useNavigate, useLocation } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { getStoredUserId } from "@/lib/auth"
import { submitSelfAssessment, skipSelfAssessment } from "@/features/chat/api"
import type { DimensionInput, SelfAssessmentData } from "@/features/chat/api"
import { useAsyncAction } from "@/hooks/use-async-action"

type LocationState = {
  chatId: string
  selfAssessmentData: SelfAssessmentData
}

type DimensionFormState = {
  examples: string
  uncertainties: string
}

const EMPTY_DIMENSION: DimensionFormState = { examples: "", uncertainties: "" }

const DIMENSIONS = ["Facts", "Strategies", "Procedures", "Rationales"] as const
type DimensionKey = "facts" | "strategies" | "procedures" | "rationales"

export default function SelfAssessmentPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const state = location.state as LocationState | null

  const userId = getStoredUserId()
  const chatId = state?.chatId
  const selfAssessmentData = state?.selfAssessmentData

  const [facts, setFacts] = useState<DimensionFormState>(EMPTY_DIMENSION)
  const [strategies, setStrategies] = useState<DimensionFormState>(EMPTY_DIMENSION)
  const [procedures, setProcedures] = useState<DimensionFormState>(EMPTY_DIMENSION)
  const [rationales, setRationales] = useState<DimensionFormState>(EMPTY_DIMENSION)

  const { loading: submitting, error: submitError, setError: setSubmitError, run: runSubmit } = useAsyncAction()
  const { loading: skipping, run: runSkip } = useAsyncAction()

  const dimensionStateMap: Record<DimensionKey, [DimensionFormState, (v: DimensionFormState) => void]> = {
    facts: [facts, setFacts],
    strategies: [strategies, setStrategies],
    procedures: [procedures, setProcedures],
    rationales: [rationales, setRationales],
  }

  // Get the section prompt from the empty_template for a given dimension heading
  function getSectionPrompt(heading: string): string {
    const section = selfAssessmentData?.empty_template?.sections?.find(
      (s) => s.heading.toLowerCase() === heading.toLowerCase()
    )
    return section?.prompt ?? ""
  }

  async function handleSubmit() {
    if (!userId || !chatId) return
    setSubmitError(null)

    await runSubmit(async () => {
      const { response, payload } = await submitSelfAssessment(
        userId,
        chatId,
        facts as DimensionInput,
        strategies as DimensionInput,
        procedures as DimensionInput,
        rationales as DimensionInput,
      )

      if (!response.ok || payload?.status !== "success") {
        setSubmitError(payload?.message || `Submission failed (HTTP ${response.status}).`)
        return
      }

      console.log("[SelfAssessment] Submitted successfully, priority:", payload.data?.priority)
      navigate(`/chat/${chatId}`)
    })
  }

  async function handleSkip() {
    if (!userId || !chatId) return

    await runSkip(async () => {
      await skipSelfAssessment(userId, chatId)
      console.log("[SelfAssessment] Skipped")
      navigate(`/chat/${chatId}`)
    })
  }

  // Fallback if page is accessed directly without state
  if (!chatId || !selfAssessmentData) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <p className="text-muted-foreground mb-4">No self-assessment data found.</p>
          <Button onClick={() => navigate("/chat")}>Go to Chat</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-3xl mx-auto px-6 py-10">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold mb-2">Self-Assessment</h1>
          <p className="text-muted-foreground text-sm">
            Before we begin, help us understand your current knowledge. This allows Broqué to
            tailor responses to your gaps. You can skip this step if you prefer.
          </p>
        </div>

        {/* KB Highlights */}
        {selfAssessmentData.global_highlights?.length > 0 && (
          <div className="mb-8 rounded-lg border border-border p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3">
              Key Legal Highlights
            </h2>
            <ul className="space-y-2">
              {selfAssessmentData.global_highlights.map((highlight, i) => (
                <li key={i} className="text-sm flex gap-2">
                  <span className="text-muted-foreground mt-0.5">•</span>
                  <span>{highlight}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Example Text */}
        {selfAssessmentData.example_text && (
          <div className="mb-8 rounded-lg border border-border p-5 bg-muted/30">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3">
              Example Self-Assessment
            </h2>
            <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">
              {selfAssessmentData.example_text}
            </p>
          </div>
        )}

        {/* Four Dimension Forms */}
        <div className="space-y-8 mb-10">
          {DIMENSIONS.map((dim) => {
            const key = dim.toLowerCase() as DimensionKey
            const [state, setState] = dimensionStateMap[key]
            const prompt = getSectionPrompt(dim)

            return (
              <div key={dim} className="rounded-lg border border-border p-5">
                <h2 className="text-base font-semibold mb-1">{dim}</h2>
                {prompt && (
                  <p className="text-sm text-muted-foreground mb-4">{prompt}</p>
                )}
                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-medium mb-1 block">
                      What do you know or have examples of?
                    </label>
                    <textarea
                      className="w-full min-h-[80px] rounded-md border border-input bg-background px-3 py-2 text-sm resize-y focus:outline-none focus:ring-1 focus:ring-ring"
                      placeholder={`Share what you already know about ${dim.toLowerCase()} in your situation...`}
                      value={state.examples}
                      onChange={(e) => setState({ ...state, examples: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium mb-1 block">
                      What are you uncertain about?
                    </label>
                    <textarea
                      className="w-full min-h-[80px] rounded-md border border-input bg-background px-3 py-2 text-sm resize-y focus:outline-none focus:ring-1 focus:ring-ring"
                      placeholder={`Describe what you are unsure about regarding ${dim.toLowerCase()}...`}
                      value={state.uncertainties}
                      onChange={(e) => setState({ ...state, uncertainties: e.target.value })}
                    />
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Error */}
        {submitError && (
          <p className="text-sm text-red-600 mb-4">{submitError}</p>
        )}

        {/* Actions */}
        <div className="flex justify-between items-center">
          <Button
            variant="outline"
            onClick={handleSkip}
            disabled={skipping || submitting}
          >
            {skipping ? "Skipping..." : "Skip for now"}
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={submitting || skipping}
          >
            {submitting ? "Submitting..." : "Submit Assessment"}
          </Button>
        </div>

      </div>
    </div>
  )
}