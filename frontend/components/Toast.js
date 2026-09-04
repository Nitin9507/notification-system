"use client";

import { useEffect, useState } from "react";

/** Small hook returning [toastElement, showToast]. */
export function useToast() {
  const [toast, setToast] = useState(null);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = setTimeout(() => setToast(null), 6000);
    return () => clearTimeout(timer);
  }, [toast]);

  const element = toast ? (
    <div className={`toast ${toast.kind}`} role="status">
      {toast.message}
    </div>
  ) : null;

  return [
    element,
    (message, kind = "ok") => setToast({ message, kind }),
  ];
}
