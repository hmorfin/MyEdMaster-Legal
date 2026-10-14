import ChatServiceHub from "@/features/chat/components/ChatServiceHub";

export default function ChatEntryPage() {
  return (
    <main className="flex h-full min-h-0 flex-col overflow-y-auto bg-background text-foreground">
      <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col justify-center px-6 py-10 md:px-10 md:py-16">
        <h2 className="mb-2 text-center text-xl font-semibold tracking-tight md:text-2xl">
          What would you like to do?
        </h2>
        <p className="mb-10 text-center text-sm text-muted-foreground md:text-base">
          Choose a service to get started.
        </p>
        <ChatServiceHub />
      </div>
    </main>
  );
}
