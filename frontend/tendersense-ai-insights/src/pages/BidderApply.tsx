import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getTender, uploadBidder, type Tender } from '../lib/api';
import { motion } from 'framer-motion';
import { PageHeader } from '@/components/PageHeader';
import { UploadCloud, FileText, CheckCircle2, ChevronLeft, Building2, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const BidderApply = () => {
  const { tenderId } = useParams<{ tenderId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [tender, setTender] = useState<Tender | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [files, setFiles] = useState<File[]>([]);

  const [form, setForm] = useState({
    company_name: '',
    gstin: '',
    pan: '',
    cin: '',
    phone: '',
    bid_amount: '',
    turnover1: '',
    turnover2: '',
    turnover3: '',
    net_worth: '',
  });

  useEffect(() => {
    if (!tenderId) return;
    getTender(tenderId)
      .then((t) => setTender(t))
      .catch(() => {
        toast.error('Failed to load tender details');
        navigate('/bidder');
      })
      .finally(() => setLoading(false));
  }, [tenderId]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) setFiles(Array.from(e.target.files));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenderId) return;
    if (files.length === 0) {
      toast.error('Please upload at least one supporting document (PDF)');
      return;
    }
    if (!form.gstin.trim() || !form.pan.trim() || !form.company_name.trim()) {
      toast.error('Company Name, GSTIN, and PAN are required');
      return;
    }

    setSubmitting(true);
    const fd = new FormData();
    fd.append('company_name', form.company_name);
    fd.append('gstin', form.gstin);
    fd.append('pan', form.pan);
    fd.append('email', user?.email ?? '');
    if (form.cin)        fd.append('cin', form.cin);
    if (form.phone)      fd.append('phone', form.phone);
    if (form.bid_amount) fd.append('bid_amount', form.bid_amount);
    if (form.net_worth)  fd.append('declared_net_worth', form.net_worth);

    const turnovers = [
      parseFloat(form.turnover1) || 0,
      parseFloat(form.turnover2) || 0,
      parseFloat(form.turnover3) || 0,
    ].filter((v) => v > 0);
    if (turnovers.length > 0) {
      fd.append('declared_turnover', JSON.stringify(turnovers));
    }

    files.forEach((f) => fd.append('documents', f));

    try {
      await uploadBidder(tenderId, fd);          // uses awaited authHeaders() ✓
      toast.success('Bid submitted successfully! OCR processing started in background.');
      navigate('/bidder');
    } catch (err: any) {
      toast.error(err.message ?? 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const field = (
    label: string,
    key: keyof typeof form,
    opts?: { required?: boolean; type?: string; placeholder?: string; colSpan?: boolean }
  ) => (
    <div className={`${opts?.colSpan ? 'sm:col-span-2' : ''}`}>
      <label className="ts-section-title block mb-1">
        {label} {opts?.required && <span className="text-status-danger">*</span>}
      </label>
      <input
        required={opts?.required}
        type={opts?.type ?? 'text'}
        placeholder={opts?.placeholder}
        value={form[key]}
        onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
        className="w-full rounded-sm border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
      />
    </div>
  );

  return (
    <div className="mx-auto max-w-[860px]">
      <button
        onClick={() => navigate('/bidder')}
        className="mb-5 inline-flex items-center gap-1 text-[12px] text-muted-foreground hover:text-foreground"
      >
        <ChevronLeft className="h-3.5 w-3.5" /> Back to portal
      </button>

      <PageHeader
        eyebrow={tender?.tender_number ?? ''}
        title="Submit tender bid"
        description={tender?.title ?? 'Loading tender details…'}
      />

      <form onSubmit={handleSubmit} className="space-y-5 mt-4">
        {/* Company info */}
        <div className="ts-card p-5">
          <div className="flex items-center gap-2 text-sm font-semibold mb-4">
            <Building2 className="h-4 w-4" /> Company Information
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {field('Registered Company Name', 'company_name', { required: true, colSpan: true })}
            {field('GSTIN', 'gstin', { required: true, placeholder: '29ABCDE1234F1Z5' })}
            {field('PAN', 'pan', { required: true, placeholder: 'ABCDE1234F' })}
            {field('CIN (optional)', 'cin')}
            {field('Phone', 'phone', { type: 'tel' })}
          </div>
        </div>

        {/* Financial details */}
        <div className="ts-card p-5">
          <div className="flex items-center gap-2 text-sm font-semibold mb-4">
            <FileText className="h-4 w-4" /> Financial &amp; Bid Details
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {field('Total Bid Amount (₹)', 'bid_amount', { required: true, type: 'number', placeholder: '0', colSpan: true })}
            {field('FY 2023-24 Turnover (₹)', 'turnover1', { type: 'number', placeholder: '0' })}
            {field('FY 2022-23 Turnover (₹)', 'turnover2', { type: 'number', placeholder: '0' })}
            {field('FY 2021-22 Turnover (₹)', 'turnover3', { type: 'number', placeholder: '0' })}
            {field('Latest Net Worth (₹)', 'net_worth', { type: 'number', placeholder: '0', colSpan: true })}
          </div>
        </div>

        {/* Document upload */}
        <div className="ts-card p-5">
          <div className="flex items-center gap-2 text-sm font-semibold mb-4">
            <UploadCloud className="h-4 w-4" /> Supporting Documents (PDF)
          </div>
          <label
            htmlFor="doc-upload"
            className="flex cursor-pointer flex-col items-center justify-center rounded-sm border border-dashed border-border bg-surface px-6 py-10 text-center hover:bg-surface/80 transition-colors"
          >
            <UploadCloud className="h-8 w-8 text-muted-foreground mb-3" />
            <div className="text-sm font-medium">Click to browse documents</div>
            <div className="mt-1 text-[11px] text-muted-foreground">
              GST Certificate, PAN, Balance Sheet, ISO, Experience Certificates — PDF only
            </div>
            <input
              id="doc-upload"
              type="file"
              multiple
              accept=".pdf"
              className="hidden"
              onChange={handleFileChange}
            />
          </label>

          {files.length > 0 && (
            <motion.ul
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 space-y-1.5"
            >
              {files.map((f, i) => (
                <li key={i} className="flex items-center gap-2 rounded-sm border border-border bg-background px-3 py-2 text-sm">
                  <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="flex-1 truncate">{f.name}</span>
                  <CheckCircle2 className="h-3.5 w-3.5 text-status-success shrink-0" />
                  <span className="text-[10px] tabular-nums text-muted-foreground">{(f.size / 1024).toFixed(0)} KB</span>
                </li>
              ))}
            </motion.ul>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={() => navigate('/bidder')}
            className="rounded-sm border border-border px-4 py-2 text-sm hover:bg-surface"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center gap-1.5 rounded-sm bg-foreground px-5 py-2 text-sm font-medium text-background hover:bg-foreground/90 disabled:opacity-60"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {submitting ? 'Submitting…' : 'Submit Final Bid'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default BidderApply;
