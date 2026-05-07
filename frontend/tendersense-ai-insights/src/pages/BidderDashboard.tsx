import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { listTenders, type Tender } from '@/lib/api';
import { api } from '@/lib/api';
import { motion } from 'framer-motion';
import { PageHeader } from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { FileText, ArrowRight, Clock, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

interface Application {
  id: string;
  tender_id: string;
  company_name: string;
  evaluation_status: string;
  tender?: {
    title: string;
    tender_number: string;
  };
}

const BidderDashboard = () => {
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!user?.email) return;
    const fetchData = async () => {
      try {
        const [tendersRes, appsRes] = await Promise.all([
          listTenders({ status: 'active', limit: 20 }),
          api.get<Application[]>(`/bidders?email=${encodeURIComponent(user.email ?? '')}`),
        ]);
        setTenders(tendersRes.tenders ?? []);
        setApplications(Array.isArray(appsRes) ? appsRes : []);
      } catch (err) {
        toast.error(err instanceof Error ? err.message : 'Failed to load bidder portal');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [user]);

  const evalStatusBadge = (status: string) => {
    if (status === 'completed') return <StatusBadge value="Eligible" />;
    if (status === 'escalated')  return <StatusBadge value="Needs Review" />;
    if (status === 'in_progress') return <StatusBadge value="Running" />;
    return <StatusBadge value="Idle" />;
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader
        eyebrow="Bidder Portal"
        title="Open opportunities"
        description="Browse active tenders, submit bids, and track your application status in real time."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Tenders list */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between mb-1">
            <div className="ts-section-title">Active Tenders</div>
            <div className="text-[11px] text-muted-foreground">{tenders.length} available</div>
          </div>

          {tenders.length === 0 ? (
            <div className="ts-card px-4 py-10 text-center text-sm text-muted-foreground">
              No active tenders at this time. Check back soon.
            </div>
          ) : (
            tenders.map((tender, i) => {
              const alreadyApplied = applications.some((a) => a.tender_id === tender.id);
              return (
                <motion.div
                  key={tender.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="ts-card p-4"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">
                        {tender.tender_number} · {tender.department}
                      </div>
                      <div className="mt-0.5 text-sm font-semibold leading-snug">{tender.title}</div>
                      <div className="mt-2 flex items-center gap-3 text-[11px] text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {tender.submission_deadline
                            ? `Deadline: ${new Date(tender.submission_deadline).toLocaleDateString('en-IN')}`
                            : 'No deadline set'}
                        </span>
                        {tender.estimated_value && (
                          <span className="flex items-center gap-1">
                            <FileText className="h-3 w-3" />
                            ₹{(tender.estimated_value / 1e7).toFixed(2)} Cr
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="shrink-0 flex flex-col items-end gap-2">
                      {alreadyApplied ? (
                        <div className="flex items-center gap-1.5 rounded-sm bg-surface border border-border px-3 py-1.5 text-[11px] font-medium text-status-success">
                          <CheckCircle2 className="h-3 w-3" /> Applied
                        </div>
                      ) : (
                        <button
                          onClick={() => navigate(`/bidder/apply/${tender.id}`)}
                          className="inline-flex items-center gap-1.5 rounded-sm bg-foreground px-3 py-1.5 text-[12px] font-medium text-background hover:bg-foreground/90"
                        >
                          Apply <ArrowRight className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                </motion.div>
              );
            })
          )}
        </div>

        {/* Applications history */}
        <div className="space-y-3">
          <div className="ts-section-title mb-1">My Applications</div>
          {applications.length === 0 ? (
            <div className="ts-card px-4 py-8 text-center text-sm text-muted-foreground">
              No bids submitted yet.
            </div>
          ) : (
            applications.map((app, i) => (
              <motion.div
                key={app.id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className="ts-card p-4"
              >
                <div className="font-mono text-[10px] text-muted-foreground">{app.id.slice(0, 8)}</div>
                <div className="mt-0.5 text-sm font-medium truncate">
                  {app.tender?.title ?? 'Tender Application'}
                </div>
                <div className="mt-2 flex items-center justify-between">
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Status</div>
                  {evalStatusBadge(app.evaluation_status)}
                </div>
              </motion.div>
            ))
          )}

          <div className="ts-card p-4 bg-foreground text-background mt-4">
            <div className="text-sm font-semibold">Need assistance?</div>
            <div className="text-[11px] mt-1 text-background/70">
              Contact the Karnataka Government Procurement Helpdesk.
            </div>
            <a
              href="mailto:procurement@karnataka.gov.in"
              className="mt-3 inline-flex items-center gap-1.5 rounded-sm border border-background/20 px-3 py-1.5 text-[12px] font-medium hover:bg-background/10"
            >
              Contact Support
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BidderDashboard;
