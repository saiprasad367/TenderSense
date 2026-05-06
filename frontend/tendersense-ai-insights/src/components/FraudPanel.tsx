import type { AgentVerdict } from "@/lib/api";
import { AlertTriangle } from "lucide-react";

interface Props {
  fraudVerdict?: AgentVerdict | null;
}

export function FraudPanel({ fraudVerdict }: Props) {
  if (!fraudVerdict) return null;

  const indicators = (fraudVerdict as { fraud_indicators?: Array<{ type: string; severity: string; description: string }> }).fraud_indicators ?? [];
  const riskScore = (fraudVerdict as { risk_score?: number }).risk_score ?? 0;

  return (
    <div className="rounded-sm border border-status-danger/30 bg-status-danger/5 overflow-hidden">
      <div className="flex items-center gap-2 border-b border-status-danger/20 px-4 py-3">
        <AlertTriangle className="h-4 w-4 text-status-danger" />
        <div className="text-sm font-semibold text-status-danger">Fraud Detection Report</div>
        <div className="ml-auto text-[11px] font-mono text-status-danger">Risk: {riskScore}/100</div>
      </div>
      {indicators.length === 0 ? (
        <div className="px-4 py-3 text-[12px] text-muted-foreground">No fraud indicators detected.</div>
      ) : (
        <ul className="divide-y divide-status-danger/10">
          {indicators.map((flag, i) => (
            <li key={i} className="px-4 py-3">
              <div className="flex items-center gap-2 text-[12px] font-medium">
                <span className={`inline-block h-1.5 w-1.5 rounded-full ${
                  flag.severity === "high" ? "bg-status-danger" : flag.severity === "medium" ? "bg-status-warning" : "bg-muted-foreground"
                }`} />
                {flag.type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                <span className="ml-auto text-[10px] uppercase text-muted-foreground">{flag.severity}</span>
              </div>
              <div className="mt-1 text-[11px] text-muted-foreground leading-relaxed">{flag.description}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
