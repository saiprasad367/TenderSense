-- ============================================================
-- TenderSense AI — Supabase Database Schema
-- Run this in the Supabase SQL Editor
-- ============================================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================
-- TABLES
-- ============================================================

-- Users (extends Supabase auth.users)
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email       TEXT UNIQUE NOT NULL,
    full_name   TEXT NOT NULL DEFAULT '',
    role        TEXT NOT NULL DEFAULT 'viewer'
                CHECK (role IN ('admin', 'senior_officer', 'evaluation_officer', 'viewer')),
    department  TEXT NOT NULL DEFAULT '',
    phone       TEXT,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Tenders
CREATE TABLE IF NOT EXISTS tenders (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_number         TEXT UNIQUE NOT NULL,
    title                 TEXT NOT NULL,
    department            TEXT NOT NULL DEFAULT '',
    tender_type           TEXT NOT NULL DEFAULT 'construction'
                          CHECK (tender_type IN ('construction', 'supply', 'services', 'consultancy')),
    tender_document_url   TEXT NOT NULL DEFAULT '',
    tender_document_path  TEXT NOT NULL DEFAULT '',
    criteria              JSONB NOT NULL DEFAULT '{}',
    issue_date            DATE,
    submission_deadline   TIMESTAMPTZ,
    estimated_value       NUMERIC(18, 2),
    language              TEXT DEFAULT 'english',
    status                TEXT DEFAULT 'active'
                          CHECK (status IN ('draft', 'active', 'evaluation_in_progress', 'completed', 'archived')),
    uploaded_by           UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    updated_at            TIMESTAMPTZ DEFAULT NOW()
);

-- Bidders
CREATE TABLE IF NOT EXISTS bidders (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_id          UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    company_name       TEXT NOT NULL,
    gstin              TEXT NOT NULL,
    pan                TEXT NOT NULL,
    cin                TEXT,
    email              TEXT NOT NULL,
    phone              TEXT,
    address            JSONB,
    declared_turnover  JSONB,        -- [fy1_value, fy2_value, fy3_value]
    declared_net_worth NUMERIC(18, 2),
    declared_projects  JSONB,
    bid_amount         NUMERIC(18, 2),
    extracted_data     JSONB,
    evaluation_status  TEXT DEFAULT 'pending'
                       CHECK (evaluation_status IN ('pending', 'in_progress', 'completed', 'escalated')),
    submitted_at       TIMESTAMPTZ DEFAULT NOW(),
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    updated_at         TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tender_id, gstin)
);

-- Documents
CREATE TABLE IF NOT EXISTS documents (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bidder_id      UUID NOT NULL REFERENCES bidders(id) ON DELETE CASCADE,
    document_type  TEXT NOT NULL DEFAULT 'other'
                   CHECK (document_type IN (
                       'balance_sheet', 'ca_certificate', 'gst_certificate',
                       'pan_card', 'project_completion', 'work_order',
                       'iso_certificate', 'labour_license', 'other'
                   )),
    file_name      TEXT NOT NULL,
    file_url       TEXT NOT NULL,
    file_path      TEXT NOT NULL,
    file_size      BIGINT,
    mime_type      TEXT,
    ocr_status     TEXT DEFAULT 'pending'
                   CHECK (ocr_status IN ('pending', 'processing', 'completed', 'failed')),
    ocr_text       TEXT,
    ocr_confidence NUMERIC(5, 4),
    extracted_data JSONB,
    is_signed      BOOLEAN,
    is_valid       BOOLEAN,
    expiry_date    DATE,
    issue_date     DATE,
    checksum       TEXT NOT NULL DEFAULT '',
    uploaded_at    TIMESTAMPTZ DEFAULT NOW(),
    processed_at   TIMESTAMPTZ,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Evaluations (agent verdicts)
CREATE TABLE IF NOT EXISTS evaluations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_id           UUID NOT NULL REFERENCES tenders(id),
    bidder_id           UUID NOT NULL REFERENCES bidders(id),
    final_verdict       TEXT CHECK (final_verdict IN ('eligible', 'not_eligible', 'needs_review')),
    confidence_score    NUMERIC(5, 4),
    finance_verdict     JSONB,
    tech_verdict        JSONB,
    compliance_verdict  JSONB,
    validation_verdict  JSONB,
    fraud_verdict       JSONB,
    explanation_chain   JSONB,
    evidence_references JSONB,
    needs_human_review  BOOLEAN DEFAULT FALSE,
    review_reason       TEXT DEFAULT '',
    human_verdict       TEXT,
    human_notes         TEXT,
    reviewed_by         UUID REFERENCES users(id),
    reviewed_at         TIMESTAMPTZ,
    evaluated_at        TIMESTAMPTZ DEFAULT NOW(),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tender_id, bidder_id)
);

-- Audit logs (append-only, enforced via RLS)
CREATE TABLE IF NOT EXISTS audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type     TEXT NOT NULL,
    entity_id       UUID NOT NULL,
    action          TEXT NOT NULL,
    user_id         UUID REFERENCES users(id),
    user_email      TEXT,
    user_role       TEXT,
    ip_address      TEXT,
    user_agent      TEXT,
    old_value       JSONB,
    new_value       JSONB,
    llm_prompt      TEXT,
    llm_response    TEXT,
    llm_model       TEXT,
    llm_tokens_used INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_tenders_status     ON tenders(status);
CREATE INDEX IF NOT EXISTS idx_tenders_dept       ON tenders(department);
CREATE INDEX IF NOT EXISTS idx_tenders_created    ON tenders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bidders_tender     ON bidders(tender_id);
CREATE INDEX IF NOT EXISTS idx_bidders_eval_st    ON bidders(evaluation_status);
CREATE INDEX IF NOT EXISTS idx_bidders_gstin      ON bidders(gstin);
CREATE INDEX IF NOT EXISTS idx_documents_bidder   ON documents(bidder_id);
CREATE INDEX IF NOT EXISTS idx_documents_ocr      ON documents(ocr_status);
CREATE INDEX IF NOT EXISTS idx_evals_tender       ON evaluations(tender_id);
CREATE INDEX IF NOT EXISTS idx_evals_bidder       ON evaluations(bidder_id);
CREATE INDEX IF NOT EXISTS idx_evals_verdict      ON evaluations(final_verdict);
CREATE INDEX IF NOT EXISTS idx_evals_review       ON evaluations(needs_human_review) WHERE needs_human_review = TRUE;
CREATE INDEX IF NOT EXISTS idx_audit_entity       ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_created      ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user         ON audit_logs(user_id);

-- FTS indexes
CREATE INDEX IF NOT EXISTS idx_docs_fts  ON documents USING gin(to_tsvector('english', coalesce(ocr_text, '')));
CREATE INDEX IF NOT EXISTS idx_tend_fts  ON tenders   USING gin(to_tsvector('english', title));

-- ============================================================
-- ROW-LEVEL SECURITY
-- ============================================================

ALTER TABLE users       ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenders     ENABLE ROW LEVEL SECURITY;
ALTER TABLE bidders     ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents   ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs  ENABLE ROW LEVEL SECURITY;

-- Service role bypasses all RLS (backend uses service role key)
-- Anon/auth users get department-filtered views

DROP POLICY IF EXISTS "users_select_own" ON users;
CREATE POLICY "users_select_own" ON users
    FOR SELECT USING (id = auth.uid());

DROP POLICY IF EXISTS "dept_tenders_select" ON tenders;
CREATE POLICY "dept_tenders_select" ON tenders
    FOR SELECT USING (
        (SELECT role FROM users WHERE id = auth.uid()) = 'viewer' AND status IN ('active', 'evaluation_in_progress', 'completed')
        OR department = (SELECT department FROM users WHERE id = auth.uid())
        OR (SELECT role FROM users WHERE id = auth.uid()) = 'admin'
    );

DROP POLICY IF EXISTS "officer_tenders_insert" ON tenders;
CREATE POLICY "officer_tenders_insert" ON tenders
    FOR INSERT WITH CHECK (
        (SELECT role FROM users WHERE id = auth.uid())
        IN ('admin', 'senior_officer', 'evaluation_officer')
    );

DROP POLICY IF EXISTS "bidders_select" ON bidders;
CREATE POLICY "bidders_select" ON bidders
    FOR SELECT USING (
        email = (SELECT email FROM users WHERE id = auth.uid())
        OR EXISTS (
            SELECT 1 FROM tenders t
            WHERE t.id = bidders.tender_id
            AND (
                t.department = (SELECT department FROM users WHERE id = auth.uid())
                OR (SELECT role FROM users WHERE id = auth.uid()) = 'admin'
            )
        )
    );

DROP POLICY IF EXISTS "audit_logs_insert_all" ON audit_logs;
CREATE POLICY "audit_logs_insert_all" ON audit_logs
    FOR INSERT WITH CHECK (TRUE);

DROP POLICY IF EXISTS "audit_logs_select_admin" ON audit_logs;
CREATE POLICY "audit_logs_select_admin" ON audit_logs
    FOR SELECT USING (
        (SELECT role FROM users WHERE id = auth.uid()) IN ('admin', 'senior_officer')
        OR user_id = auth.uid()
    );

-- ============================================================
-- STORAGE BUCKETS (run in Supabase dashboard or via API)
-- ============================================================
-- INSERT INTO storage.buckets (id, name, public) VALUES ('tender-documents', 'tender-documents', false);
-- INSERT INTO storage.buckets (id, name, public) VALUES ('bidder-documents', 'bidder-documents', false);

-- ============================================================
-- TRIGGER: auto-update updated_at
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tenders_updated_at ON tenders;
CREATE TRIGGER tenders_updated_at     BEFORE UPDATE ON tenders     FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS bidders_updated_at ON bidders;
CREATE TRIGGER bidders_updated_at     BEFORE UPDATE ON bidders     FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS evaluations_updated_at ON evaluations;
CREATE TRIGGER evaluations_updated_at BEFORE UPDATE ON evaluations FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- TRIGGER: auto-sync auth.users to public.users
-- ============================================================
CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.users (id, email, full_name, role, department)
  VALUES (
    new.id, 
    new.email, 
    COALESCE(new.raw_user_meta_data->>'full_name', ''),
    COALESCE(new.raw_user_meta_data->>'role', 'viewer'),
    COALESCE(new.raw_user_meta_data->>'department', '')
  )
  ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    full_name = EXCLUDED.full_name,
    role = EXCLUDED.role,
    department = EXCLUDED.department;
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
