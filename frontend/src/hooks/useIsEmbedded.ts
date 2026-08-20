import { useEffect, useState } from "react";

/**
 * Detects whether the app is running inside an iframe (embedded on another site).
 * Always false during SSR/first render; flips synchronously on mount before paint.
 */
export function useIsEmbedded(): boolean {
  const [isEmbedded, setIsEmbedded] = useState(false);

  useEffect(() => {
    try {
      setIsEmbedded(window.self !== window.top);
    } catch {
      // Cross-origin frame access throws a SecurityError - that only happens inside an iframe.
      setIsEmbedded(true);
    }
  }, []);

  return isEmbedded;
}
