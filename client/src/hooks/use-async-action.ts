import { useCallback, useState } from "react";

export function useAsyncAction() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async <T,>(action: () => Promise<T>): Promise<T | null> => {
    setLoading(true);
    setError(null);
    try {
      return await action();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unexpected error.");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { loading, error, setError, run };
}
