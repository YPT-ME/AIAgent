"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";
import { TooltipIconButton } from "./tooltip-icon-button";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  // Theme is only known after mount (it depends on localStorage) - render a
  // same-size placeholder first so the header doesn't jump/hydration-mismatch.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return <div className="size-9" />;
  }

  const isDark = resolvedTheme === "dark";

  return (
    <TooltipIconButton
      size="lg"
      className="p-4"
      variant="ghost"
      tooltip={isDark ? "Switch to light mode" : "Switch to dark mode"}
      onClick={() => setTheme(isDark ? "light" : "dark")}
    >
      {isDark ? <Sun className="size-5" /> : <Moon className="size-5" />}
    </TooltipIconButton>
  );
}
