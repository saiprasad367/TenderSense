import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PageHeader } from "@/components/PageHeader";
import { UploadCloud, FileText, X, ArrowRight, CheckCircle2, AlertCircle } from "lucide-react";
import { Link } from "react-router-dom";
import { uploadTender } from "@/lib/api";
import { toast } from "sonner";

interface UFile { id: string; name: string; size: number; progress: number; done: boolean; error?: string; }

export default function UploadScreen() {
  const [files, setFiles] = useState<UFile[]>([]);
  const [drag, setDrag] = useState(false);
  const [tenderId, setTenderId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Metadata form state
  const [meta, setMeta] = useState({
    title: "", department: "", tender_number: "",
    tender_type: "construction", issue_date: "", submission_deadline: "", estimated_value: "",
  });

  const addFiles = useCallback((list: FileList | null) => {
    if (!list) return;
    const next: UFile[] = Array.from(list).map((f) => ({
      id: crypto.randomUUID(), name: f.name, size: f.size, progress: 0, done: false,
    }));
    setFiles((prev) => [...prev, ...next]);
  }, []);

  const handleUpload = async () => {
    const tenderFile = files.find((f) => f.name.toLowerCase().endsWith(".pdf"));
    if (!tenderFile) {
      toast.error("Please add a PDF tender document first");
      return;
    }
    if (!meta.title || !meta.department) {
      toast.error("Title and Department are required");
      return;
    }

    setUploading(true);
    const form = new FormData();

    // Re-read the actual File objects from input
    const inputFiles = inputRef.current?.files;
    if (!inputFiles) { setUploading(false); return; }

    for (const f of Array.from(inputFiles)) {
      if (f.name === tenderFile.name) form.append("file", f);
    }

    Object.entries(meta).forEach(([k, v]) => { if (v) form.append(k, v); });

    try {
      // Animate progress
      setFiles((prev) => prev.map((f) => f.name === tenderFile.name ? { ...f, progress: 30 } : f));
      const result = await uploadTender(form);
      setFiles((prev) => prev.map((f) => f.name === tenderFile.name ? { ...f, progress: 100, done: true } : f));
      setTenderId(result.tender_id);
      toast.success("Tender uploaded! Criteria extracted by Claude.");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Upload failed";
      setFiles((prev) => prev.map((f) => f.name === tenderFile.name ? { ...f, error: msg } : f));
      toast.error(msg);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        eyebrow="Step 1 of 3"
        title="Upload tender document"
        description="Drop the tender notice PDF. Claude will extract eligibility criteria automatically."
      />

      {/* Metadata form */}
      <div className="ts-card mb-5 p-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="ts-section-title block mb-1">Tender Title *</label>
          <input value={meta.title} onChange={(e) => setMeta((m) => ({ ...m, title: e.target.value }))}
            className="w-full rounded-sm border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            placeholder="e.g. Construction of NH-44 Bridge" />
        </div>
        <div>
          <label className="ts-section-title block mb-1">Department *</label>
          <input value={meta.department} onChange={(e) => setMeta((m) => ({ ...m, department: e.target.value }))}
            className="w-full rounded-sm border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            placeholder="e.g. PWD Karnataka" />
        </div>
        <div>
          <label className="ts-section-title block mb-1">Tender Number</label>
          <input value={meta.tender_number} onChange={(e) => setMeta((m) => ({ ...m, tender_number: e.target.value }))}
            className="w-full rounded-sm border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            placeholder="e.g. TND-2026-0481" />
        </div>
        <div>
          <label className="ts-section-title block mb-1">Type</label>
          <select value={meta.tender_type} onChange={(e) => setMeta((m) => ({ ...m, tender_type: e.target.value }))}
            className="w-full rounded-sm border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring">
            {["construction", "supply", "services", "consultancy"].map((t) => (
              <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="ts-section-title block mb-1">Issue Date</label>
          <input type="date" value={meta.issue_date} onChange={(e) => setMeta((m) => ({ ...m, issue_date: e.target.value }))}
            className="w-full rounded-sm border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring" />
        </div>
        <div>
          <label className="ts-section-title block mb-1">Submission Deadline</label>
          <input type="datetime-local" value={meta.submission_deadline} onChange={(e) => setMeta((m) => ({ ...m, submission_deadline: e.target.value }))}
            className="w-full rounded-sm border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring" />
        </div>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); addFiles(e.dataTransfer.files); }}
        onClick={() => inputRef.current?.click()}
        className={`ts-card cursor-pointer flex flex-col items-center justify-center text-center px-6 py-14 transition-colors ${drag ? "border-foreground bg-surface" : "hover:bg-surface/60"}`}
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-sm border border-border bg-background">
          <UploadCloud className="h-5 w-5" />
        </div>
        <div className="mt-4 text-base font-medium">Drag & drop tender PDF here</div>
        <div className="mt-1 text-sm text-muted-foreground">or click to browse — PDF up to 50 MB</div>
        <input ref={inputRef} type="file" accept=".pdf" multiple className="hidden"
          onChange={(e) => addFiles(e.target.files)} />
      </div>

      <AnimatePresence>
        {files.length > 0 && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="ts-card mt-5">
            <div className="border-b border-border px-4 py-3 flex items-center justify-between">
              <div className="text-sm font-semibold">Documents queued <span className="text-muted-foreground font-normal">({files.length})</span></div>
              <button onClick={() => setFiles([])} className="text-[11px] text-muted-foreground hover:text-foreground">Clear all</button>
            </div>
            <ul className="divide-y divide-border">
              {files.map((f) => (
                <li key={f.id} className="flex items-center gap-3 px-4 py-3">
                  <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-3">
                      <div className="truncate text-sm">{f.name}</div>
                      <div className="text-[11px] text-muted-foreground tabular-nums">{(f.size / 1024).toFixed(1)} KB</div>
                    </div>
                    <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-surface">
                      <motion.div className={`h-full ${f.error ? "bg-status-danger" : "bg-foreground"}`}
                        initial={{ width: 0 }} animate={{ width: `${f.progress}%` }} transition={{ ease: "easeOut" }} />
                    </div>
                    {f.error && <div className="mt-1 text-[11px] text-status-danger">{f.error}</div>}
                  </div>
                  {f.done ? (
                    <CheckCircle2 className="h-4 w-4 text-status-success" />
                  ) : f.error ? (
                    <AlertCircle className="h-4 w-4 text-status-danger" />
                  ) : (
                    <button onClick={() => setFiles((p) => p.filter((x) => x.id !== f.id))} className="rounded-sm p-1 hover:bg-surface">
                      <X className="h-3.5 w-3.5" />
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>

      {files.length > 0 && !tenderId && (
        <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="mt-5 flex justify-end gap-3">
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="inline-flex items-center gap-1.5 rounded-sm bg-foreground px-4 py-2.5 text-sm font-medium text-background hover:bg-foreground/90 disabled:opacity-60"
          >
            {uploading ? "Uploading…" : "Upload & Extract Criteria"} <ArrowRight className="h-4 w-4" />
          </button>
        </motion.div>
      )}

      {tenderId && (
        <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="mt-5 flex justify-end">
          <Link
            to={`/evaluation?tender_id=${tenderId}`}
            className="inline-flex items-center gap-1.5 rounded-sm bg-foreground px-4 py-2.5 text-sm font-medium text-background hover:bg-foreground/90"
          >
            Start Evaluation <ArrowRight className="h-4 w-4" />
          </Link>
        </motion.div>
      )}
    </div>
  );
}
