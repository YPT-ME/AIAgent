"use client";

import { useEffect, useState } from "react";
import { useQueryState } from "nuqs";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

// Served by the backend's custom route (backend/src/webapp.py)
type AppInfo = {
  server_started_at: string | null;
  code_updated_at: string | null;
  kb_updated_at: string | null;
  kb_documents: number;
  kb_chunks: number;
};

const FRONTEND_BUILT_AT = process.env.NEXT_PUBLIC_BUILD_TIME || null;

function formatDate(iso: string | null) {
  if (!iso) return "unknown";
  const date = new Date(iso);
  if (isNaN(date.getTime())) return "unknown";
  return date.toLocaleString(undefined, {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function latest(...dates: (string | null | undefined)[]) {
  const times = dates
    .filter((d): d is string => !!d)
    .map((d) => new Date(d).getTime())
    .filter((t) => !isNaN(t));
  return times.length ? new Date(Math.max(...times)).toISOString() : null;
}

/** Discreet "last deploy / knowledge base updated" line, details on hover. */
export function DeployInfo({ className }: { className?: string }) {
  const [apiUrl] = useQueryState("apiUrl");
  const effectiveApiUrl = apiUrl || process.env.NEXT_PUBLIC_API_URL;
  const [info, setInfo] = useState<AppInfo | null>(null);
  // Dates are formatted in the browser's locale/timezone, so render only after mount
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (!effectiveApiUrl) return;
    const controller = new AbortController();
    fetch(`${effectiveApiUrl.replace(/\/$/, "")}/app-info`, {
      signal: controller.signal,
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data: AppInfo | null) => data && setInfo(data))
      .catch(() => {});
    return () => controller.abort();
  }, [effectiveApiUrl]);

  if (!mounted) {
    return <p className={cn("h-4", className)} />;
  }

  const deployedAt = latest(FRONTEND_BUILT_AT, info?.code_updated_at);

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <p
            className={cn(
              "text-muted-foreground/60 h-4 cursor-default text-center text-[11px] leading-4 select-none",
              className,
            )}
          >
            Deployed {formatDate(deployedAt)}
            {info && <> · Knowledge base {formatDate(info.kb_updated_at)}</>}
          </p>
        </TooltipTrigger>
        <TooltipContent side="top">
          <div className="grid grid-cols-[auto_auto] gap-x-3 gap-y-0.5 text-left">
            <span>Frontend built</span>
            <span>{formatDate(FRONTEND_BUILT_AT)}</span>
            {info ? (
              <>
                <span>Backend code updated</span>
                <span>{formatDate(info.code_updated_at)}</span>
                <span>Server started</span>
                <span>{formatDate(info.server_started_at)}</span>
                <span>Knowledge base updated</span>
                <span>{formatDate(info.kb_updated_at)}</span>
                <span>Indexed</span>
                <span>
                  {info.kb_documents} docs, {info.kb_chunks} chunks
                </span>
              </>
            ) : (
              <>
                <span>Backend</span>
                <span>unavailable</span>
              </>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
