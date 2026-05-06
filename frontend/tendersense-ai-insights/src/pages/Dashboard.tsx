import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { PageHeader } from "@/components/PageHeader";
import { CountUp } from "@/components/CountUp";
import { StatusBadge } from "@/components/StatusBadge";
import { ArrowUpRight, FileText, Users, CheckCircle2, AlertTriangle, XCircle, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import { getDashboardAnalytics, type DashboardAnalytics } from "@/lib/api";

export default function Dashboard() {
  const [data, setData] = useState<DashboardAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getDashboardAnalytics();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const stats = data
    ? [
        { label: "Tenders Processed", value: data.tenders_processed, icon: FileText, hint: `${data.active_tenders} active` },
        { label: "Bidders Evaluated", value: data.bidders_evaluated, icon: Users, hint: `${(data.avg_confidence * 100).toFixed(1)}% avg confidence` },
        { label: "Eligible", value: data.eligible, icon: CheckCircle2, hint: data.bidders_evaluated ? `${((data.eligible / data.bidders_evaluated) * 100).toFixed(1)}% of total` : "0%", tone: "success" as const },
        { label: "Needs Review", value: data.needs_review, icon: AlertTriangle, hint: "Awaiting human adjudication", tone: "warning" as const },
        { label: "Not Eligible", value: data.not_eligible, icon: XCircle, hint: "Automatically rejected", tone: "danger" as const },
      ]
    : [];

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        eyebrow="Overview"
        title="Procurement intelligence at a glance"
        description="A consolidated view of tender evaluation activity across departments, agents, and review queues."
        actions={
          <div className="flex items-center gap-3">
            <button
              onClick={fetchData}
              disabled={loading}
              className="inline-flex items-center gap-1.5 rounded-sm border border-border px-3 py-2 text-xs font-medium hover:bg-surface disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
            <Link to="/upload" className="inline-flex items-center gap-1.5 rounded-sm bg-foreground px-3.5 py-2 text-xs font-medium text-background hover:bg-foreground/90">
              New Evaluation <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        }
      />

      {error && (
        <div className="mb-4 rounded-sm border border-status-danger/30 bg-status-danger/5 px-4 py-3 text-sm text-status-danger">
          {error} — showing cached data if available.
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {(loading ? Array(5).fill(null) : stats).map((s, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05, duration: 0.3 }}
            className="ts-card p-4"
          >
            {s ? (
              <>
                <div className="flex items-start justify-between">
                  <div className="ts-section-title">{s.label}</div>
                  <s.icon className="h-3.5 w-3.5 text-muted-foreground" />
                </div>
                <div className="mt-3 text-[26px] font-semibold tracking-tight tabular-nums">
                  <CountUp to={s.value} />
                </div>
                <div className="mt-1 text-[11px] text-muted-foreground">{s.hint}</div>
              </>
            ) : (
              <div className="h-24 animate-pulse rounded bg-surface" />
            )}
          </motion.div>
        ))}
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="ts-card lg:col-span-2 overflow-hidden">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div>
              <div className="text-sm font-semibold">Recent Evaluations</div>
              <div className="text-[11px] text-muted-foreground">Last 7 days · automatic + reviewed</div>
            </div>
            <Link to="/evaluation" className="text-[11px] font-medium text-muted-foreground hover:text-foreground">View all →</Link>
          </div>
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full text-sm">
              <thead className="bg-surface text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Bidder</th>
                  <th className="px-4 py-2.5 font-medium">Tender</th>
                  <th className="px-4 py-2.5 font-medium">Verdict</th>
                  <th className="px-4 py-2.5 font-medium text-right">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  Array(4).fill(null).map((_, i) => (
                    <tr key={i} className="border-t border-border">
                      <td colSpan={4} className="px-4 py-3">
                        <div className="h-4 animate-pulse rounded bg-surface" />
                      </td>
                    </tr>
                  ))
                ) : (data?.recent_evaluations ?? []).map((r) => (
                  <tr key={r.id} className="border-t border-border hover:bg-surface/60">
                    <td className="px-4 py-3 text-sm">{r.bidder_name || "—"}</td>
                    <td className="px-4 py-3 text-[12px] text-muted-foreground font-mono">{r.id.slice(0, 8)}…</td>
                    <td className="px-4 py-3"><StatusBadge value={r.final_verdict === "eligible" ? "Eligible" : r.final_verdict === "not_eligible" ? "Not Eligible" : "Needs Review"} /></td>
                    <td className="px-4 py-3 text-right tabular-nums text-[12px]">
                      {(r.confidence_score * 100).toFixed(0)}%
                    </td>
                  </tr>
                ))}
                {!loading && !data?.recent_evaluations?.length && (
                  <tr>
                    <td colSpan={4} className="px-4 py-6 text-center text-[12px] text-muted-foreground">
                      No evaluations yet — upload a tender to begin.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="ts-card">
          <div className="border-b border-border px-4 py-3">
            <div className="text-sm font-semibold">System Status</div>
            <div className="text-[11px] text-muted-foreground">Live backend health</div>
          </div>
          <div className="px-4 py-4 space-y-3">
            {[
              { label: "API Gateway", ok: !error },
              { label: "Agent Engine", ok: !error },
              { label: "Vector Store", ok: !error },
              { label: "Database", ok: !error },
            ].map((svc) => (
              <div key={svc.label} className="flex items-center justify-between text-sm">
                <span>{svc.label}</span>
                <div className="flex items-center gap-1.5">
                  <span className={`h-1.5 w-1.5 rounded-full ${svc.ok ? "bg-status-success animate-pulse-soft" : "bg-status-danger"}`} />
                  <span className="text-[11px] text-muted-foreground">{svc.ok ? "Online" : "Error"}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
