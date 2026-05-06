import { useState } from "react";
import { StatusBadge } from "./StatusBadge";
import { BidderDetailDialog } from "./BidderDetailDialog";
import type { BidderEval } from "@/lib/api";

interface VerdictTableProps {
  evaluations?: BidderEval[];
}

export function VerdictTable({ evaluations = [] }: VerdictTableProps) {
  const [openId, setOpenId] = useState<string | null>(null);

  const verdictLabel = (v: string) =>
    v === "eligible" ? "Eligible" : v === "not_eligible" ? "Not Eligible" : "Needs Review";

  const agentStatus = (verdict: BidderEval["finance_verdict"]) =>
    verdict ? verdictLabel(verdict.status === "pass" ? "eligible" : verdict.status === "fail" ? "not_eligible" : "needs_review") : "Needs Review";

  const fraudLabel = (v: BidderEval["fraud_verdict"]): "None" | "Low" | "Medium" | "High" => {
    if (!v) return "None";
    const risk = (v as { risk_score?: number }).risk_score ?? 0;
    if (risk >= 70) return "High";
    if (risk >= 40) return "Medium";
    if (risk > 0) return "Low";
    return "None";
  };

  return (
    <div className="ts-card overflow-hidden">
      <div className="overflow-x-auto scrollbar-thin">
        <table className="w-full text-sm min-w-[820px]">
          <thead className="bg-surface text-left text-[11px] uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-4 py-2.5 font-medium">Bidder</th>
              <th className="px-3 py-2.5 font-medium">Finance</th>
              <th className="px-3 py-2.5 font-medium">Technical</th>
              <th className="px-3 py-2.5 font-medium">Compliance</th>
              <th className="px-3 py-2.5 font-medium">Validation</th>
              <th className="px-3 py-2.5 font-medium">Fraud</th>
              <th className="px-4 py-2.5 font-medium">Final Verdict</th>
            </tr>
          </thead>
          <tbody>
            {evaluations.map((b) => (
              <tr key={b.id} onClick={() => setOpenId(b.id)}
                className="border-t border-border cursor-pointer hover:bg-surface/60">
                <td className="px-4 py-3">
                  <div className="font-medium">{b.bidder_name}</div>
                  <div className="text-[11px] text-muted-foreground font-mono">
                    {b.bidder_id.slice(0, 8)} · {b.bid_amount ? `₹${(b.bid_amount / 1e7).toFixed(2)}Cr` : "N/A"}
                  </div>
                </td>
                <td className="px-3 py-3"><StatusBadge value={agentStatus(b.finance_verdict)} /></td>
                <td className="px-3 py-3"><StatusBadge value={agentStatus(b.tech_verdict)} /></td>
                <td className="px-3 py-3"><StatusBadge value={agentStatus(b.compliance_verdict)} /></td>
                <td className="px-3 py-3"><StatusBadge value={agentStatus(b.validation_verdict)} /></td>
                <td className="px-3 py-3"><StatusBadge value={fraudLabel(b.fraud_verdict)} /></td>
                <td className="px-4 py-3"><StatusBadge value={verdictLabel(b.final_verdict)} /></td>
              </tr>
            ))}
            {evaluations.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-[12px] text-muted-foreground">
                  No evaluation results yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <BidderDetailDialog evaluationId={openId} onClose={() => setOpenId(null)} evaluations={evaluations} />
    </div>
  );
}
