import { cn } from "@/lib/utils";

type Tone = "success" | "warning" | "danger" | "info" | "neutral";

const map: Record<string, Tone> = {
  Eligible: "success",
  "Not Eligible": "danger",
  "Needs Review": "warning",
  None: "neutral",
  Low: "info",
  Medium: "warning",
  High: "danger",
  Idle: "neutral",
  Running: "info",
  Done: "success",
};

const toneClasses: Record<Tone, string> = {
  success: "bg-status-success-bg text-status-success border-status-success/20",
  warning: "bg-status-warning-bg text-status-warning border-status-warning/20",
  danger: "bg-status-danger-bg text-status-danger border-status-danger/20",
  info: "bg-status-info-bg text-status-info border-status-info/20",
  neutral: "bg-status-neutral-bg text-status-neutral border-border",
};

export function StatusBadge({ value, className }: { value: string; className?: string }) {
  const tone = map[value] ?? "neutral";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-[11px] font-medium tracking-wide",
        toneClasses[tone],
        className
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", {
        "bg-status-success": tone === "success",
        "bg-status-warning": tone === "warning",
        "bg-status-danger": tone === "danger",
        "bg-status-info": tone === "info",
        "bg-status-neutral": tone === "neutral",
      })} />
      {value}
    </span>
  );
}
