import { useLocation, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function SuccessPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as { name?: string; email?: string } | null;

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 p-4">
      <Card className="w-full max-w-xl">
        <CardHeader>
          <CardTitle className="text-2xl">Onboarding complete</CardTitle>
          <CardDescription>
            {state?.name ? `Welcome, ${state.name}!` : "Welcome!"}
            {state?.email ? ` We will use ${state.email} for account updates.` : ""}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex gap-3">
          <Button onClick={() => navigate("/onboarding")}>Back to onboarding</Button>
          <Button variant="outline" onClick={() => navigate("/")}>
            Home
          </Button>
          <Button variant="outline" onClick={() => navigate(0)}>
            Refresh
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
