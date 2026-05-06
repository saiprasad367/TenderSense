import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { StatusBadge } from "./StatusBadge";
import { FraudPanel } from "./FraudPanel";
import { FileText } from "lucide-react";
import type { BidderEval, CriterionResult } from "@/lib/api";

interface Props {
  evaluationId: string | null;
  onClose: () => void;
  evaluations: BidderEval[];
}

export function BidderDetailDialog({ evaluationId, onClose, evaluations }: Props) {
  const ev = evaluations.find((e) => e.id === evaluationId);
  if (!ev) return null;

  // Merge all criteria results from all agents
  const allCriteria: CriterionResult[] = [
    ...(ev.finance_verdict?.criteria_results ?? []),
    ...(ev.tech_verdict?.criteria_results ?? []),
    ...(ev.compliance_verdict?.criteria_results ?? []),
    ...(ev.validation_verdict?.criteria_results ?? []),
  ];

  const verdictLabel = (v: string) =>
    v === "eligible" ? "Eligible" : v === "not_eligible" ? "Not Eligible" : "Needs Review";

  const fraudRisk = (ev.fraud_verdict as { risk_score?: number } | null)?.risk_score ?? 0;
  const fraudFlag: "None" | "Low" | "Medium" | "High" =
    fraudRisk >= 70 ? "High" : fraudRisk >= 40 ? "Medium" : fraudRisk > 0 ? "Low" : "None";

  return (
    <Dialog open={!!evaluationId} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto scrollbar-thin">
        <DialogHeader>
          <div className="flex items-center justify-between gap-3">
            <div>
              <DialogTitle className="text-lg">{ev.bidder_name}</DialogTitle>
              <DialogDescription className="font-mono text-[11px]">
                {ev.bidder_id} · GSTIN: {ev.bidder_gstin}
              </DialogDescription>
            </div>
            <StatusBadge value={verdictLabel(ev.final_verdict)} />
          </div>
        </DialogHeader>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[12px]">
          {[
            ["Bid amount", ev.bid_amount ? `₹${(ev.bid_amount / 1e7).toFixed(2)}Cr` : "N/A"],
            ["Confidence", `${(ev.confidence_score * 100).toFixed(0)}%`],
            ["Fraud risk", `${fraudRisk}/100`],
            ["Criteria", allCriteria.length.toString()],
          ].map(([k, v]) => (
            <div key={k} className="rounded-sm border border-border p-2.5">
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{k}</div>
              <div className="mt-0.5 font-medium tabular-nums">{v}</div>
            </div>
          ))}
        </div>

        {ev.explanation_chain?.summary && (
          <div className="mt-3 rounded-sm border border-border bg-surface p-3 text-[12px] leading-relaxed">
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground mr-2">AI Summary</span>
            {ev.explanation_chain.summary}
          </div>
        )}

        {allCriteria.length > 0 && (
          <div className="mt-4">
            <div className="ts-section-title mb-2">Explainable evaluation</div>
            <Accordion type="single" collapsible className="ts-card divide-y divide-border">
              {allCriteria.map((c, i) => (
                <AccordionItem key={i} value={`c-${i}`} className="border-0">
                  <AccordionTrigger className="px-4 py-3 hover:no-underline hover:bg-surface/60">
                    <div className="flex flex-1 items-center justify-between gap-3 pr-2">
                      <div className="text-left">
                        <div className="text-sm font-medium">{c.criterion_id}</div>
                        <div className="text-[11px] text-muted-foreground">{c.required_value}</div>
                      </div>
                      <StatusBadge value={c.result === "pass" ? "Eligible" : c.result === "fail" ? "Not Eligible" : "Needs Review"} />
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[12px]">
                      <div>
                        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Extracted value</div>
                        <div className="mt-0.5">{c.extracted_value || "—"}</div>
                      </div>
                      <div>
                        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Evidence</div>
                        <div className="mt-0.5 flex flex-wrap gap-1">
                          {c.evidence.map((e, j) => (
                            <span key={j} className="flex items-center gap-1">
                              <FileText className="h-3 w-3 text-muted-foreground" />{e}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                    <div className="mt-3 rounded-sm border border-border bg-surface p-3 text-[12px] leading-relaxed">
                      <span className="text-[10px] uppercase tracking-wider text-muted-foreground mr-2">Why</span>
                      {c.explanation}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        )}

        {fraudFlag !== "None" && (
          <div className="mt-4">
            <FraudPanel fraudVerdict={ev.fraud_verdict} />
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
