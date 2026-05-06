import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Check, X, MessageSquare, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { getReviewQueue, submitReview, type BidderEval } from "@/lib/api";

type QueueItem = BidderEval & { tender_title: string; department: string };

export default function Review() {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [comments, setComments] = useState<Record<string, string>>({});
  const [decided, setDecided] = useState<Record<string, "approved" | "rejected">>({});
  const [submitting, setSubmitting] = useState<Record<string, boolean>>({});

  useEffect(() => {
    getReviewQueue()
      .then((res) => setQueue(res.queue as QueueItem[]))
      .catch((e) => toast.error(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleDecision = async (item: QueueItem, verdict: "eligible" | "not_eligible") => {
    setSubmitting((s) => ({ ...s, [item.id]: true }));
    try {
      await submitReview(item.id, verdict, comments[item.id] ?? "");
      setDecided((d) => ({ ...d, [item.id]: verdict === "eligible" ? "approved" : "rejected" }));
      toast[verdict === "eligible" ? "success" : "error"](
        `${verdict === "eligible" ? "Approved" : "Rejected"}: ${item.bidder_name}`
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to submit review");
    } finally {
      setSubmitting((s) => ({ ...s, [item.id]: false }));
    }
  };

  const fraudFlagMap = (verdict: BidderEval["fraud_verdict"]): "None" | "Low" | "Medium" | "High" => {
    if (!verdict) return "None";
    const risk = typeof verdict === "object" && "risk_score" in verdict ? (verdict as { risk_score: number }).risk_score : 0;
    if (risk >= 70) return "High";
    if (risk >= 40) return "Medium";
    if (risk > 0) return "Low";
    return "None";
  };

  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader
        eyebrow="Human-in-the-loop"
        title="Review queue"
        description="Bidders flagged by agents for human adjudication. Each decision is logged in the immutable audit trail."
      />

      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : queue.length === 0 ? (
        <div className="ts-card px-4 py-12 text-center text-sm text-muted-foreground">
          No items in review queue. All evaluations resolved.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {queue.map((item, i) => (
            <motion.div key={item.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }} className="ts-card p-4 flex flex-col">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-mono text-[11px] text-muted-foreground">{item.bidder_id?.slice(0, 8)}</div>
                  <div className="text-sm font-semibold truncate">{item.bidder_name}</div>
                  <div className="text-[11px] text-muted-foreground truncate">{item.tender_title}</div>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    <StatusBadge value={item.final_verdict === "eligible" ? "Eligible" : item.final_verdict === "not_eligible" ? "Not Eligible" : "Needs Review"} />
                    <StatusBadge value={fraudFlagMap(item.fraud_verdict)} />
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Confidence</div>
                  <div className="text-lg font-semibold tabular-nums">{(item.confidence_score * 100).toFixed(0)}%</div>
                </div>
              </div>

              {item.review_reason && (
                <div className="mt-2 rounded-sm border border-status-warning/30 bg-status-warning/5 px-3 py-2 text-[11px] text-status-warning">
                  {item.review_reason}
                </div>
              )}

              <div className="mt-3 grid grid-cols-4 gap-1.5 text-[10px]">
                {[
                  ["Fin", item.finance_verdict?.status],
                  ["Tech", item.tech_verdict?.status],
                  ["Comp", item.compliance_verdict?.status],
                  ["Val", item.validation_verdict?.status],
                ].map(([label, val]) => (
                  <div key={label as string} className="rounded-sm border border-border bg-surface px-2 py-1.5">
                    <div className="text-muted-foreground uppercase tracking-wider">{label}</div>
                    <div className="mt-0.5 truncate capitalize">{val ?? "—"}</div>
                  </div>
                ))}
              </div>

              <div className="relative mt-3">
                <MessageSquare className="absolute left-2 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                <textarea
                  placeholder="Add reviewer comment…"
                  value={comments[item.id] ?? ""}
                  onChange={(e) => setComments({ ...comments, [item.id]: e.target.value })}
                  className="w-full rounded-sm border border-border bg-background pl-7 pr-2 py-2 text-[12px] resize-none focus:outline-none focus:ring-1 focus:ring-ring"
                  rows={2}
                  disabled={!!decided[item.id]}
                />
              </div>

              <div className="mt-3 flex items-center justify-end gap-2">
                {decided[item.id] && (
                  <span className="text-[11px] text-muted-foreground mr-auto">Decision recorded · {decided[item.id]}</span>
                )}
                {!decided[item.id] && (
                  <>
                    <button
                      onClick={() => handleDecision(item, "not_eligible")}
                      disabled={submitting[item.id]}
                      className="inline-flex items-center gap-1.5 rounded-sm border border-border bg-background px-3 py-1.5 text-[12px] font-medium hover:bg-surface disabled:opacity-50"
                    >
                      {submitting[item.id] ? <Loader2 className="h-3 w-3 animate-spin" /> : <X className="h-3.5 w-3.5" />} Reject
                    </button>
                    <button
                      onClick={() => handleDecision(item, "eligible")}
                      disabled={submitting[item.id]}
                      className="inline-flex items-center gap-1.5 rounded-sm bg-foreground px-3 py-1.5 text-[12px] font-medium text-background hover:bg-foreground/90 disabled:opacity-50"
                    >
                      {submitting[item.id] ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3.5 w-3.5" />} Approve
                    </button>
                  </>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
