import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import {
    Dialog,
    DialogClose,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog"
import { Plus } from "lucide-react"
import { Field, FieldGroup } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { getStoredUserId } from "@/lib/auth"
import { SidebarMenuButton } from "@/components/ui/sidebar"
import { createChat } from "@/features/chat/api"
import { useAsyncAction } from "@/hooks/use-async-action"

const US_STATES = [
  "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
  "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
  "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
  "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
  "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
  "New Hampshire", "New Jersey", "New Mexico", "New York",
  "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
  "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
  "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
  "West Virginia", "Wisconsin", "Wyoming", "Federal"
]

type CreateChatDialogProps = {
  onChatCreated?: () => void;
  autoOpen?: number;
  mode?: "learn" | "help";
  onAutoOpenConsumed?: () => void;
}

export function CreateChatDialog({ onChatCreated, autoOpen, mode = "learn", onAutoOpenConsumed }: CreateChatDialogProps) {
    const navigate = useNavigate()

    const [open, setOpen] = useState(false)
    const [legalSituation, setLegalSituation] = useState("")
    const [priorExperience, setPriorExperience] = useState("")
    const [desiredOutcome, setDesiredOutcome] = useState("")
    const [jurisdiction, setJurisdiction] = useState("")
    const { loading: submitting, error: errorMsg, setError, run } = useAsyncAction()

    useEffect(() => {
        if (autoOpen) {
            setOpen(true)
        }
    }, [autoOpen])

    function resetForm() {
        setLegalSituation("")
        setPriorExperience("")
        setDesiredOutcome("")
        setJurisdiction("")
    }

    async function handleCreateChat() {
        setError(null)

        const userId = getStoredUserId()
        if (!userId) {
            console.warn("[CreateChat] Missing stored user id")
            setError("No logged-in user found. Please log in again.")
            return
        }

        if (!legalSituation.trim()) {
            setError("Please describe your legal situation.")
            return
        }
        if (!priorExperience.trim()) {
            setError("Please describe your prior experience.")
            return
        }
        if (!desiredOutcome.trim()) {
            setError("Please describe your desired outcome.")
            return
        }
        if (!jurisdiction) {
            setError("Please select your jurisdiction.")
            return
        }

        await run(async () => {
            const { response, payload: data } = await createChat(
                userId,
                legalSituation.trim(),
                priorExperience.trim(),
                desiredOutcome.trim(),
                jurisdiction,
            )

            if (!response.ok || data?.status !== "success" || !data.data?.chat_id) {
                setError(data?.message || `Create chat failed (HTTP ${response.status}).`)
                return
            }

            const chatId = data.data.chat_id
            const selfAssessmentData = data.data.self_assessment_data

            resetForm()
            setOpen(false)
            onAutoOpenConsumed?.()
            onChatCreated?.()
            console.log("[CreateChat] Chat created, mode:", mode, "chatId:", chatId)

            if (mode === "learn") {
                navigate(`/chat/${chatId}/self-assessment`, {
                    state: {
                        chatId,
                        selfAssessmentData,
                    }
                })
            } else {
                // Help mode: navigate first, then auto-send so typewriter effect works
                navigate(`/chat/${chatId}`, {
                    state: { autoSendMessage: legalSituation.trim() }
                })
            }
        })
    }

    return (
        <Dialog open={open} onOpenChange={(val) => {
            setOpen(val)
            if (!val) {
                resetForm()
                onAutoOpenConsumed?.()
            }
        }}>
            <>
                <DialogTrigger asChild>
                    <SidebarMenuButton tooltip="New Chat">
                        <Plus className="h-4 w-4" />
                        <span className="group-data-[collapsible=icon]:hidden">New Chat</span>
                    </SidebarMenuButton>
                </DialogTrigger>
                <DialogContent className="sm:max-w-lg">
                    <DialogHeader>
                        <DialogTitle>New Chat</DialogTitle>
                        <DialogDescription>
                            {mode === "learn"
                                ? "Tell us about your legal situation so we can guide your learning."
                                : "Tell us about your legal situation so we can help you directly."
                            }
                        </DialogDescription>
                    </DialogHeader>
                    <FieldGroup>
                        <Field>
                            <label className="text-sm font-medium mb-1 block">Legal Situation</label>
                            <Input
                                placeholder="e.g. I got a speeding ticket on I-35 in Austin"
                                value={legalSituation}
                                onChange={(e) => setLegalSituation(e.target.value)}
                                className="focus-visible:ring-[1px] focus-visible:ring-white/25 dark:focus-visible:ring-white/20"
                            />
                        </Field>
                        <Field>
                            <label className="text-sm font-medium mb-1 block">Prior Experience</label>
                            <Input
                                placeholder="e.g. No, this is my first time dealing with this"
                                value={priorExperience}
                                onChange={(e) => setPriorExperience(e.target.value)}
                                className="focus-visible:ring-[1px] focus-visible:ring-white/25 dark:focus-visible:ring-white/20"
                            />
                        </Field>
                        <Field>
                            <label className="text-sm font-medium mb-1 block">Desired Outcome</label>
                            <Input
                                placeholder="e.g. I want to understand my options"
                                value={desiredOutcome}
                                onChange={(e) => setDesiredOutcome(e.target.value)}
                                className="focus-visible:ring-[1px] focus-visible:ring-white/25 dark:focus-visible:ring-white/20"
                            />
                        </Field>
                        <Field>
                            <label className="text-sm font-medium mb-1 block">Jurisdiction</label>
                            <select
                                value={jurisdiction}
                                onChange={(e) => setJurisdiction(e.target.value)}
                                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                            >
                                <option value="">Select your state...</option>
                                {US_STATES.map((state) => (
                                    <option key={state} value={state.toLowerCase()}>
                                        {state}
                                    </option>
                                ))}
                            </select>
                        </Field>
                        {errorMsg ? <p className="text-sm text-red-600">{errorMsg}</p> : null}
                    </FieldGroup>
                    <DialogFooter>
                        <DialogClose asChild>
                            <Button variant="outline" type="button">Cancel</Button>
                        </DialogClose>
                        <Button type="button" disabled={submitting} onClick={handleCreateChat}>
                            {submitting ? "Creating..." : "Continue"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </>
        </Dialog>
    )
}
