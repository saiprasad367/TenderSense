import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Download, FileText, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { listTenders, getEvaluationResults, downloadPdfReport, type Tender, type BidderEval } from "@/lib/api";
import { useSearchParams } from "react-router-dom";

export default function Reports() {
  const [searchParams] = useSearchParams();
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [selectedId, setSelectedId] = useState<string>(searchParams.get("tender_id") ?? "");
  const [results, setResults] = useState<BidderEval[]>([]);
  const [tender, setTender] = useState<Tender | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    listTenders({ limit: 50 }).then((r) => {
      setTenders(r.tenders);
      if (!selectedId && r.tenders.length > 0) setSelectedId(r.tenders[0].id);
    });
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setLoading(true);
    const t = tenders.find((t) => t.id === selectedId) ?? null;
    setTender(t);
    getEvaluationResults(selectedId)
      .then((r) => setResults(r.results))
      .catch((e) => toast.error(e.message))
      .finally(() => setLoading(false));
  }, [selectedId, tenders]);

  const counts = results.reduce(
    (acc, b) => { acc[b.final_verdict] = (acc[b.final_verdict] ?? 0) + 1; return acc; },
    {} as Record<string, number>
  );

  const handleExport = async () => {
    if (!selectedId) return;
    setExporting(true);
    try {
      await downloadPdfReport(selectedId);
      toast.success("PDF downloaded");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Export failed");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader
        eyebrow="Export"
        title="Evaluation report"
        description="Select a tender and preview its evaluation summary before exporting as PDF."
        actions={
          <div className="flex items-center gap-3">
            <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)}
              className="rounded-sm border border-border bg-background px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring">
              {tenders.map((t) => (
                <option key={t.id} value={t.id}>{t.tender_number} — {t.title.slice(0, 40)}</option>
              ))}
            </select>
            <button onClick={handleExport} disabled={exporting || !selectedId}
              className="inline-flex items-center gap-1.5 rounded-sm bg-foreground px-3.5 py-2 text-xs font-medium text-background hover:bg-foreground/90 disabled:opacity-50">
              {exporting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
              Export PDF
            </button>
          </div>
        }
      />

      {loading ? (
        <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      ) : tender ? (
        <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="ts-card-elevated">
          <div className="border-b border-border px-6 py-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-muted-foreground">
                <FileText className="h-3.5 w-3.5" /> Confidential · Government of Karnataka
              </div>
              <div className="text-[11px] text-muted-foreground font-mono">REF: {tender.tender_number}/EVAL/2026</div>
            </div>
            <h2 className="mt-3 text-xl font-semibold tracking-tight">Tender Evaluation Summary</h2>
            <div className="text-sm text-muted-foreground">{tender.title}</div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-0 divide-x divide-y md:divide-y-0 divide-border">
            {[
              ["Authority", tender.department],
              ["Estimated value", tender.estimated_value ? `₹ ${(tender.estimated_value / 1e7).toFixed(2)} Cr` : "N/A"],
              ["Issue Date", tender.created_at?.slice(0, 10) ?? "N/A"],
              ["Status", tender.status.toUpperCase()],
            ].map(([k, v]) => (
              <div key={k} className="px-5 py-4">
                <div className="ts-section-title">{k}</div>
                <div className="mt-1 text-[13px]">{v}</div>
              </div>
            ))}
          </div>

          <div className="px-6 py-5 grid grid-cols-3 gap-3">
            {(["eligible", "needs_review", "not_eligible"] as const).map((k) => (
              <div key={k} className="rounded-sm border border-border bg-surface p-4">
                <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
                  {k.replace("_", " ")}
                </div>
                <div className="mt-1 text-2xl font-semibold tabular-nums">{counts[k] ?? 0}</div>
              </div>
            ))}
          </div>

          <div className="px-6 pb-6">
            <div className="ts-section-title mb-2">Bidder roster</div>
            <div className="ts-card overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-surface text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">Bidder</th>
                    <th className="px-3 py-2.5 font-medium">Bid amount</th>
                    <th className="px-3 py-2.5 font-medium">Confidence</th>
                    <th className="px-3 py-2.5 font-medium">Verdict</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((b) => (
                    <tr key={b.id} className="border-t border-border">
                      <td className="px-4 py-3">
                        <div className="text-sm">{b.bidder_name}</div>
                        <div className="text-[11px] font-mono text-muted-foreground">{b.bidder_gstin}</div>
                      </td>
                      <td className="px-3 py-3 tabular-nums text-[12px]">
                        {b.bid_amount ? `₹ ${(b.bid_amount / 1e7).toFixed(2)} Cr` : "N/A"}
                      </td>
                      <td className="px-3 py-3 tabular-nums text-[12px]">
                        {(b.confidence_score * 100).toFixed(0)}%
                      </td>
                      <td className="px-3 py-3">
                        <StatusBadge value={b.final_verdict === "eligible" ? "Eligible" : b.final_verdict === "not_eligible" ? "Not Eligible" : "Needs Review"} />
                      </td>
                    </tr>
                  ))}
                  {results.length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-4 py-6 text-center text-[12px] text-muted-foreground">
                        No evaluation results for this tender yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="border-t border-border px-6 py-4 text-[11px] text-muted-foreground">
            Generated by TenderSense AI · Multi-agent procurement evaluation system · Digitally signed and timestamped.
          </div>
        </motion.div>
      ) : (
        <div className="ts-card px-4 py-10 text-center text-sm text-muted-foreground">
          Select a tender above to preview the evaluation report.
        </div>
      )}
    </div>
  );
}
