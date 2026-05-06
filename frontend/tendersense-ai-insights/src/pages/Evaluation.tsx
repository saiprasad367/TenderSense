import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Loader2, Terminal, ChevronRight, AlertCircle } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { VerdictTable } from "@/components/VerdictTable";
import { streamEvaluation, getEvaluationResults, type SSEUpdate, type BidderEval } from "@/lib/api";
import { toast } from "sonner";

const AGENT_KEYS = ["document_indexing", "validation", "finance", "tech", "compliance", "fraud", "synthesize"] as const;
const AGENT_META: Record<string, { name: string; role: string }> = {
  document_indexing: { name: "Document Indexer", role: "Embeds documents into vector store" },
  validation: { name: "Validation Agent", role: "Checks document completeness and signatures" },
  finance: { name: "Finance Agent", role: "Validates turnover, net worth, solvency" },
  tech: { name: "Technical Agent", role: "Matches project experience and capability" },
  compliance: { name: "Compliance Agent", role: "Checks ISO, GST, statutory certificates" },
  fraud: { name: "Fraud Agent", role: "Detects anomalies, duplication and tampering" },
  synthesize: { name: "Orchestrator", role: "Coordinates agents and publishes final verdicts" },
};

type AgentState = { status: "Idle" | "Running" | "Done" | "Error"; progress: number; output: string };

export default function Evaluation() {
  const [searchParams] = useSearchParams();
  const tenderId = searchParams.get("tender_id");

  const [agentStates, setAgentStates] = useState<Record<string, AgentState>>(
    Object.fromEntries(AGENT_KEYS.map((k) => [k, { status: "Idle", progress: 0, output: "Waiting…" }]))
  );
  const [logs, setLogs] = useState<string[]>([]);
  const [completed, setCompleted] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<BidderEval[]>([]);
  const [activeResult, setActiveResult] = useState<string | null>(null);
  const logsRef = useRef<HTMLDivElement>(null);
  const stopRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (logsRef.current) logsRef.current.scrollTop = logsRef.current.scrollHeight;
  }, [logs]);

  const startEvaluation = () => {
    if (!tenderId) {
      setError("No tender ID provided. Upload a tender first.");
      return;
    }
    setRunning(true);
    setError(null);
    setCompleted(false);
    setLogs([]);

    const stop = streamEvaluation(
      tenderId,
      (update: SSEUpdate) => {
        const ts = new Date().toLocaleTimeString("en-IN", { hour12: false });
        const logLine = `[${ts}] [${update.agent ?? update.type}] ${update.message ?? update.status ?? JSON.stringify(update)}`;
        setLogs((prev) => [...prev, logLine]);

        if (update.type === "agent_start" && update.agent) {
          setAgentStates((prev) => ({
            ...prev,
            [update.agent!]: { status: "Running", progress: 10, output: update.message ?? "Running…" },
          }));
        }
        if (update.type === "agent_complete" && update.agent) {
          setAgentStates((prev) => ({
            ...prev,
            [update.agent!]: {
              status: "Done",
              progress: 100,
              output: `${update.status?.toUpperCase() ?? "Done"} · conf ${((update.confidence ?? 0) * 100).toFixed(0)}%`,
            },
          }));
        }
        if (update.type === "agent_warning" && update.agent) {
          setAgentStates((prev) => ({
            ...prev,
            [update.agent!]: { status: "Error", progress: 100, output: update.message ?? "Warning" },
          }));
        }
        if (update.type === "evaluation_complete") {
          toast.success(`Verdict: ${update.verdict} (${((update.confidence ?? 0) * 100).toFixed(0)}% confidence)`);
        }
      },
      async () => {
        setRunning(false);
        setCompleted(true);
        // Fetch results
        if (tenderId) {
          try {
            const res = await getEvaluationResults(tenderId);
            setResults(res.results);
          } catch (e) {
            console.error("Failed to fetch results:", e);
          }
        }
      },
      (err) => {
        setRunning(false);
        setError(err.message);
        toast.error(err.message);
      },
    );
    stopRef.current = stop;
  };

  const overallPct = Math.round(
    (Object.values(agentStates).reduce((s, a) => s + a.progress, 0) / (AGENT_KEYS.length * 100)) * 100
  );

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        eyebrow={tenderId ?? "No tender selected"}
        title="Live multi-agent evaluation"
        description="Real-time Claude Sonnet 4 evaluation with 5 specialist agents"
        actions={
          <div className="flex items-center gap-3 text-xs">
            {!running && !completed && (
              <button
                onClick={startEvaluation}
                disabled={!tenderId}
                className="inline-flex items-center gap-1.5 rounded-sm bg-foreground px-3.5 py-2 text-xs font-medium text-background hover:bg-foreground/90 disabled:opacity-50"
              >
                {tenderId ? "Run Evaluation" : "Upload tender first"}
              </button>
            )}
            {running && (
              <>
                <div className="text-muted-foreground">Overall</div>
                <div className="h-1.5 w-40 overflow-hidden rounded-full bg-surface border border-border">
                  <motion.div className="h-full bg-foreground" animate={{ width: `${overallPct}%` }} />
                </div>
                <div className="tabular-nums font-medium w-9">{overallPct}%</div>
                <button onClick={() => { stopRef.current?.(); setRunning(false); }} className="text-status-danger text-[11px]">
                  Stop
                </button>
              </>
            )}
          </div>
        }
      />

      {error && (
        <div className="mb-4 flex items-center gap-2 rounded-sm border border-status-danger/30 bg-status-danger/5 px-4 py-3 text-sm text-status-danger">
          <AlertCircle className="h-4 w-4 shrink-0" />{error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        {/* Results list */}
        <div className="lg:col-span-3 ts-card overflow-hidden">
          <div className="border-b border-border px-4 py-3">
            <div className="text-sm font-semibold">Bidders</div>
            <div className="text-[11px] text-muted-foreground">{results.length} evaluated</div>
          </div>
          <ul className="max-h-[520px] overflow-y-auto scrollbar-thin">
            {results.length === 0 ? (
              <li className="px-4 py-6 text-center text-[12px] text-muted-foreground">
                {running ? "Evaluation in progress…" : "No results yet"}
              </li>
            ) : results.map((r) => (
              <li key={r.id}>
                <button
                  onClick={() => setActiveResult(r.id)}
                  className={`flex w-full items-start gap-2 px-4 py-3 text-left border-b border-border hover:bg-surface/60 ${activeResult === r.id ? "bg-surface" : ""}`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-[12px] font-mono text-muted-foreground">{r.bidder_id.slice(0, 8)}</div>
                    <div className="text-sm truncate">{r.bidder_name}</div>
                    <div className="mt-1">
                      <StatusBadge value={r.final_verdict === "eligible" ? "Eligible" : r.final_verdict === "not_eligible" ? "Not Eligible" : "Needs Review"} />
                    </div>
                  </div>
                  <ChevronRight className="h-3.5 w-3.5 text-muted-foreground mt-1" />
                </button>
              </li>
            ))}
          </ul>
        </div>

        {/* Agent grid */}
        <div className="lg:col-span-6 grid grid-cols-1 sm:grid-cols-2 gap-3 content-start">
          {AGENT_KEYS.map((key, i) => {
            const a = agentStates[key];
            const meta = AGENT_META[key];
            return (
              <motion.div key={key} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }} className="ts-card p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-semibold">{meta.name}</div>
                    <div className="text-[11px] text-muted-foreground">{meta.role}</div>
                  </div>
                  <StatusBadge value={a.status} />
                </div>
                <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-surface">
                  <motion.div className={`h-full ${a.status === "Error" ? "bg-status-danger" : "bg-foreground"}`} animate={{ width: `${a.progress}%` }} />
                </div>
                <div className="mt-3 flex items-center gap-2 text-[12px] text-muted-foreground">
                  {a.status === "Running" && <Loader2 className="h-3 w-3 animate-spin" />}
                  <span className="truncate">{a.output}</span>
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Log stream */}
        <div className="lg:col-span-3 ts-card overflow-hidden flex flex-col">
          <div className="border-b border-border px-4 py-3 flex items-center gap-2">
            <Terminal className="h-3.5 w-3.5" />
            <div className="text-sm font-semibold">Agent stream</div>
            <span className={`ml-auto h-1.5 w-1.5 rounded-full ${running ? "bg-status-success animate-pulse-soft" : "bg-border"}`} />
          </div>
          <div ref={logsRef} className="ts-mono text-[11px] leading-5 px-3 py-3 max-h-[520px] overflow-y-auto scrollbar-thin bg-background">
            {logs.map((l, i) => (
              <div key={i} className="text-foreground/85">
                <span className="text-muted-foreground mr-2">{String(i + 1).padStart(2, "0")}</span>{l}
              </div>
            ))}
            {logs.length === 0 && <div className="text-muted-foreground">waiting for stream …</div>}
          </div>
        </div>
      </div>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: completed ? 1 : 0.45, y: 0 }} className="mt-6">
        <div className="mb-3 flex items-end justify-between">
          <div>
            <div className="ts-section-title">Outcome</div>
            <h2 className="text-lg font-semibold tracking-tight">Verdict summary</h2>
          </div>
          {tenderId && <Link to="/reports" className="text-xs text-muted-foreground hover:text-foreground">Generate report →</Link>}
        </div>
        {results.length > 0 ? (
          <VerdictTable evaluations={results} />
        ) : (
          <div className="ts-card px-4 py-8 text-center text-sm text-muted-foreground">
            {running ? "Evaluation in progress — results will appear here." : "Run an evaluation to see verdicts."}
          </div>
        )}
      </motion.div>
    </div>
  );
}
