import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { PageHeader } from "@/components/PageHeader";
import { ChevronDown, Loader2, RefreshCw } from "lucide-react";
import { getAuditLogs, type AuditLog } from "@/lib/api";
import { toast } from "sonner";

export default function Audit() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState<string | null>(null);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const res = await getAuditLogs({ limit: 100 });
      setLogs(res.logs);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchLogs(); }, []);

  return (
    <div className="mx-auto max-w-[1200px]">
      <PageHeader
        eyebrow="Traceability"
        title="Audit trail"
        description="Every agent action and human decision is recorded — immutable, timestamped, forensic-grade."
        actions={
          <button onClick={fetchLogs} disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-sm border border-border px-3 py-2 text-xs font-medium hover:bg-surface disabled:opacity-50">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
          </button>
        }
      />

      {loading ? (
        <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      ) : (
        <div className="ts-card overflow-hidden">
          <div className="grid grid-cols-12 border-b border-border bg-surface px-4 py-2.5 text-[11px] uppercase tracking-wider text-muted-foreground">
            <div className="col-span-3">Timestamp</div>
            <div className="col-span-2">Actor</div>
            <div className="col-span-3">Action</div>
            <div className="col-span-4">Entity</div>
          </div>
          {logs.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-muted-foreground">No audit logs yet.</div>
          ) : (
            <ul>
              {logs.map((row) => (
                <li key={row.id} className="border-b border-border last:border-0">
                  <button onClick={() => setOpen(open === row.id ? null : row.id)}
                    className="grid w-full grid-cols-12 items-center px-4 py-3 text-left text-sm hover:bg-surface/60">
                    <div className="col-span-3 ts-mono text-[12px] text-muted-foreground">
                      {new Date(row.created_at).toLocaleString("en-IN")}
                    </div>
                    <div className="col-span-2 font-medium">{row.user_email?.split("@")[0] ?? "System"}</div>
                    <div className="col-span-3 ts-mono text-[12px]">{row.action}</div>
                    <div className="col-span-3 truncate text-[12px] text-muted-foreground">
                      {row.entity_type}:{row.entity_id?.slice(0, 8)}
                    </div>
                    <div className="col-span-1 flex justify-end">
                      <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${open === row.id ? "rotate-180" : ""}`} />
                    </div>
                  </button>
                  {open === row.id && (
                    <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="overflow-hidden">
                      <pre className="ts-mono text-[11px] leading-5 bg-background border-t border-border px-4 py-3 text-foreground/85 whitespace-pre-wrap">
                        {JSON.stringify({ ...row }, null, 2)}
                      </pre>
                    </motion.div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
