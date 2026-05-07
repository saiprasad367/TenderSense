export type Verdict = "Eligible" | "Not Eligible" | "Needs Review";
export type AgentStatus = "Idle" | "Running" | "Done";

export const tender = {
  id: "TND-2026-0481",
  title: "Construction of Regional Highway Bridge — NH-44 Corridor",
  authority: "Ministry of Road Transport & Highways, Govt. of India",
  estimatedValue: "₹ 248.50 Cr",
  publishedOn: "2026-03-12",
  closingOn: "2026-04-28",
  category: "Civil Works — Infrastructure",
};

export interface Bidder {
  id: string;
  name: string;
  registration: string;
  finance: Verdict;
  technical: Verdict;
  compliance: Verdict;
  validation: Verdict;
  fraudFlag: "None" | "Low" | "Medium" | "High";
  riskScore: number;
  verdict: Verdict;
  bidAmount: string;
}

export const bidders: Bidder[] = [
  { id: "B-001", name: "Larsen Infra Constructions Ltd.", registration: "CIN-U45200MH1998PLC", finance: "Eligible", technical: "Eligible", compliance: "Eligible", validation: "Eligible", fraudFlag: "None", riskScore: 12, verdict: "Eligible", bidAmount: "₹ 232.10 Cr" },
  { id: "B-002", name: "Shapoorji Pallonji Engineering Pvt. Ltd.", registration: "CIN-U45201GJ2001PTC", finance: "Eligible", technical: "Eligible", compliance: "Needs Review", validation: "Eligible", fraudFlag: "Low", riskScore: 28, verdict: "Needs Review", bidAmount: "₹ 241.75 Cr" },
  { id: "B-003", name: "Gammon Bridges & Structures Ltd.", registration: "CIN-U45203DL2005PLC", finance: "Eligible", technical: "Eligible", compliance: "Eligible", validation: "Eligible", fraudFlag: "None", riskScore: 9, verdict: "Eligible", bidAmount: "₹ 245.20 Cr" },
  { id: "B-004", name: "Apex Civil Works Pvt. Ltd.", registration: "CIN-U45204UP2012PTC", finance: "Not Eligible", technical: "Eligible", compliance: "Eligible", validation: "Needs Review", fraudFlag: "Medium", riskScore: 54, verdict: "Not Eligible", bidAmount: "₹ 215.40 Cr" },
  { id: "B-005", name: "Meridian Build-Tech Co.", registration: "CIN-U45205KA2015PTC", finance: "Eligible", technical: "Needs Review", compliance: "Eligible", validation: "Eligible", fraudFlag: "Low", riskScore: 31, verdict: "Needs Review", bidAmount: "₹ 238.90 Cr" },
  { id: "B-006", name: "Veridian Highways Pvt. Ltd.", registration: "CIN-U45206TN2017PTC", finance: "Eligible", technical: "Eligible", compliance: "Eligible", validation: "Eligible", fraudFlag: "None", riskScore: 14, verdict: "Eligible", bidAmount: "₹ 244.55 Cr" },
  { id: "B-007", name: "Sunrise Constructions India", registration: "CIN-U45207RJ2019PTC", finance: "Needs Review", technical: "Eligible", compliance: "Needs Review", validation: "Eligible", fraudFlag: "Medium", riskScore: 47, verdict: "Needs Review", bidAmount: "₹ 226.80 Cr" },
  { id: "B-008", name: "BlackStone Infra Holdings", registration: "CIN-U45208WB2020PTC", finance: "Not Eligible", technical: "Not Eligible", compliance: "Not Eligible", validation: "Not Eligible", fraudFlag: "High", riskScore: 86, verdict: "Not Eligible", bidAmount: "₹ 198.30 Cr" },
];

export interface CriterionEvidence {
  criterion: string;
  requirement: string;
  extracted: string;
  source: string;
  page: number;
  decision: Verdict;
  explanation: string;
}

export const criteriaByBidder: Record<string, CriterionEvidence[]> = {
  "B-001": [
    { criterion: "Annual Turnover (3-yr avg)", requirement: "≥ ₹ 150 Cr", extracted: "₹ 187.4 Cr", source: "AuditedFinancials_FY24.pdf", page: 4, decision: "Eligible", explanation: "Average of FY22, FY23, FY24 audited turnover exceeds threshold by 24.9%." },
    { criterion: "Net Worth (Positive)", requirement: "Positive net worth, last FY", extracted: "₹ 412.1 Cr", source: "BalanceSheet_FY24.pdf", page: 2, decision: "Eligible", explanation: "Positive net worth confirmed; ratio analysis shows healthy solvency." },
    { criterion: "Similar Project Experience", requirement: "≥ 2 bridge projects > ₹100 Cr in last 7 yrs", extracted: "4 projects (Yamuna Bridge, Coastal Span, NH-7 Flyover, Beas Crossing)", source: "ExperienceCertificates.pdf", page: 11, decision: "Eligible", explanation: "Four eligible projects identified, all certified by competent authorities." },
    { criterion: "ISO 9001:2015 Certification", requirement: "Valid ISO certificate", extracted: "Valid until 2027-08-15", source: "ISO_Certificate.pdf", page: 1, decision: "Eligible", explanation: "Certificate verified against issuing body registry." },
    { criterion: "GST Compliance", requirement: "No defaults in last 3 yrs", extracted: "0 defaults", source: "GST_PortalExtract.pdf", page: 1, decision: "Eligible", explanation: "GSTIN active, all returns filed on time." },
  ],
  "B-008": [
    { criterion: "Annual Turnover (3-yr avg)", requirement: "≥ ₹ 150 Cr", extracted: "₹ 38.2 Cr", source: "Financials_FY24.pdf", page: 3, decision: "Not Eligible", explanation: "Reported turnover is 74% below the threshold." },
    { criterion: "Similar Project Experience", requirement: "≥ 2 bridge projects > ₹100 Cr", extracted: "1 project listed; not certified", source: "ProjectList.pdf", page: 6, decision: "Not Eligible", explanation: "Only 1 project listed without a competent-authority certificate." },
    { criterion: "Document Authenticity", requirement: "Documents must match issuing-authority records", extracted: "Mismatched signatures on 2 certificates", source: "ExperienceCertificates.pdf", page: 9, decision: "Not Eligible", explanation: "Cross-verification with authority registry failed; signatures appear inconsistent across documents." },
  ],
};

export const recentEvaluations = [
  { id: "TND-2026-0481", title: "NH-44 Bridge Corridor", bidders: 8, completed: "2 min ago", verdict: "3 Eligible / 3 Review / 2 Rejected" },
  { id: "TND-2026-0479", title: "Smart City Water Pipeline — Phase II", bidders: 12, completed: "1 hr ago", verdict: "5 Eligible / 4 Review / 3 Rejected" },
  { id: "TND-2026-0476", title: "Solar Rooftop Procurement — DDA", bidders: 6, completed: "4 hr ago", verdict: "4 Eligible / 1 Review / 1 Rejected" },
  { id: "TND-2026-0470", title: "Metro Coach Refurbishment", bidders: 9, completed: "Yesterday", verdict: "6 Eligible / 2 Review / 1 Rejected" },
];

export const activityTimeline = [
  { time: "10:42", actor: "Orchestrator", action: "Started evaluation of TND-2026-0481" },
  { time: "10:43", actor: "Finance Agent", action: "Parsed audited financials for 8 bidders" },
  { time: "10:44", actor: "Technical Agent", action: "Cross-referenced project experience" },
  { time: "10:45", actor: "Fraud Agent", action: "Flagged BlackStone Infra Holdings (risk: 86)" },
  { time: "10:46", actor: "Compliance Agent", action: "Validated ISO and GST records" },
  { time: "10:47", actor: "Validation Agent", action: "Final cross-check completed" },
  { time: "10:47", actor: "Orchestrator", action: "Verdicts published — awaiting human review" },
];

export const auditTrail = [
  { ts: "2026-04-28 10:42:11", agent: "Orchestrator", action: "EVAL_START", io: "tender_id=TND-2026-0481, bidders=8" },
  { ts: "2026-04-28 10:42:14", agent: "Finance", action: "EXTRACT_TURNOVER", io: "bidder=B-001 → ₹187.4Cr (3-yr avg)" },
  { ts: "2026-04-28 10:42:18", agent: "Technical", action: "MATCH_EXPERIENCE", io: "bidder=B-001 → 4 eligible projects" },
  { ts: "2026-04-28 10:42:21", agent: "Compliance", action: "VERIFY_ISO", io: "bidder=B-002 → expired since 2025-11-02" },
  { ts: "2026-04-28 10:42:25", agent: "Fraud", action: "DETECT_DUPLICATE", io: "bidder=B-008 → matched B-004 project list (cosine 0.94)" },
  { ts: "2026-04-28 10:42:29", agent: "Validation", action: "CROSS_CHECK", io: "bidder=B-008 → signature mismatch, 2 certificates" },
  { ts: "2026-04-28 10:42:33", agent: "Orchestrator", action: "PUBLISH_VERDICT", io: "8 verdicts published" },
];

export const fraudCase = {
  bidder: bidders.find(b => b.id === "B-008")!,
  flags: [
    { label: "Document inconsistency", detail: "Signatures on Experience Certificates pp. 9 and 11 differ from authorized signatory specimen." },
    { label: "Duplicate project claim", detail: "Project ‘Coastal Span — Phase 2’ also claimed by bidder B-004; same commencement date and value." },
    { label: "Suspicious formatting", detail: "Audited Financials show font and DPI mismatch consistent with edited PDFs." },
    { label: "Turnover anomaly", detail: "Declared turnover diverges from MCA filings by 312%." },
  ],
};

export const agents = [
  { key: "orchestrator", name: "Orchestrator", role: "Coordinates agents and publishes final verdicts" },
  { key: "finance", name: "Finance Agent", role: "Validates turnover, net worth, solvency" },
  { key: "tech", name: "Technical Agent", role: "Matches project experience and capability" },
  { key: "compliance", name: "Compliance Agent", role: "Checks ISO, GST, statutory certificates" },
  { key: "validation", name: "Validation Agent", role: "Cross-references documents and registries" },
  { key: "fraud", name: "Fraud Agent", role: "Detects anomalies, duplication and tampering" },
] as const;
