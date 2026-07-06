# IKIS — User Guide

**Unified Asset & Operations Brain** — everything needed to actually use the app: what
it's for, how to work each tab, and what to upload to get real results out of it.

**Live app:** https://ikis-frontend.onrender.com
**Live API:** https://ikis-backend.onrender.com

---

## Purpose

In asset-intensive industries, equipment knowledge is scattered across 7-12
disconnected systems — P&IDs in one place, work orders in another, procedures in a
third. Nobody can see the full picture of an asset's history, so decisions get made
without it.

| | |
|---|---|
| **35%** | of engineer time spent searching for information instead of using it |
| **18-22%** | of unplanned downtime linked to incomplete equipment history |
| **25%** | of experienced industrial talent retiring in the next decade, taking undocumented knowledge with them |

IKIS unifies that scattered knowledge — ingesting documents of any format, extracting
what's in them, and making it queryable and actionable at the point someone actually
needs it.

## Theme

Built for the **AI for Industrial Knowledge Intelligence: Unified Asset & Operations
Brain** challenge (ET AI Hackathon 2026):

`Industrial Intelligence` · `Document Management` · `Knowledge Engineering` · `Quality`

---

## How to use it

### 1. Upload documents

Go to the **Documents** tab first — everything else depends on having something in
the knowledge base. Pick the category closest to what you're uploading, then choose a
file.

> Try: upload the sample documents in `ikis-backend/sample_docs/` (see table below)
> to see real extraction happen immediately.

### 2. Ask a question

In **Expert Query**, ask about anything in what you just uploaded — equipment specs,
procedures, regulations, failure history. You get a synthesized answer with cited
sources and a confidence score, not just a list of matching documents.

> Try: *"What maintenance action should be taken for PUMP-001 and why?"*

### 3. Check maintenance risk

In **Maintenance**, pick an equipment tag and get predictive recommendations grounded
in its real document history. Click **Run Root Cause Analysis** for a deeper report
that separates the immediate cause from the underlying root cause.

### 4. Scan for compliance gaps

In **Compliance**, click **Scan for gaps**. If you've uploaded a "Regulatory Pack"
document, gaps are grounded in its actual text; otherwise you'll see clearly-labeled
representative examples. The same scan also surfaces **Quality Deviations** —
measurable readings (vibration, temperature) that drift from a stated baseline.

### 5. Find systemic patterns

**Lessons Learned** needs at least two "Incident / Near-Miss" uploads that share a
real underlying cause — then **Scan for patterns** surfaces the pattern no single
report would reveal on its own, with a recommended action.

---

## What documents to give it

**Important: these categories are just examples.** IKIS is not limited to these 7
sample files — it works with *any* document of these formats: text (`.txt`), PDF
(`.pdf`), or an image (`.png`/`.jpg`/`.jpeg`/`.webp`/`.bmp`, read via vision-model
OCR). Upload your organization's actual documents the same way.

| Category | Upload | What makes it useful |
|---|---|---|
| 📕 Equipment Manual | OEM manuals, spec sheets | Rated values (flow, pressure), maintenance schedules, known failure modes |
| 🔧 P&ID / Scanned Form | A photo/scan of a form, tag plate, or simple diagram — or a text/PDF description | Read via vision OCR — works well for printed/handwritten text and simple flow layouts |
| 📋 Maintenance Record | Work order logs with dates, technician names, readings | Specific numeric readings so Quality Deviations has something real to compare against a baseline |
| 📜 Regulatory Pack | Real safety procedures or regulation excerpts | Grounds Compliance gap detection in your real text instead of representative examples |
| 🚨 Incident / Near-Miss | Incident reports, near-miss logs, audit findings | Upload **at least two** that share a root cause — that's what Lessons Learned needs |

**Best results come from specificity.** Documents with named equipment tags (e.g.
`PUMP-001`), dates, and numbers extract and cross-reference far better than vague
prose — the knowledge graph links documents together by exactly these entities.

### Ready-made sample set

Don't have real documents handy? `ikis-backend/sample_docs/` has 7 that already share
a genuine cross-document pattern (a deferred-maintenance issue traceable across three
different equipment), so every tab has something real to demonstrate on:

| File | Upload as |
|---|---|
| `CP2000_Equipment_Manual.txt` | Equipment Manual |
| `PUMP001_Maintenance_Log.txt` | Maintenance Record |
| `SafetyProcedure_ShutdownEmergency.txt` | Regulatory Pack |
| `InspectionReport_Q2_2026.txt` | Maintenance Record |
| `IncidentReport_COMPRESSOR02_NearMiss.txt` | Incident / Near-Miss |
| `IncidentReport_TURBINE04_Trip.txt` | Incident / Near-Miss |
| `AuditFinding_Q1Q2_2026_MaintenanceDeferrals.txt` | Incident / Near-Miss |

Don't have the files locally? Run `python sample_data.py` inside `ikis-backend/` to
regenerate them.

**Minimum to see everything work:** all 7. Fewer uploads mean some tabs (especially
Lessons Learned, which needs 2+ incident reports) will fall back to empty or
generic/representative output — not broken, just nothing real to work with yet.

---

## Things to expect on the live deployment

- **First request after idle time is slow (~30-50+ seconds).** Render's free tier
  spins the backend down after inactivity; the first request wakes it back up.
- **Responses can be slow under heavy use (30-140+ seconds).** This is genuine
  NVIDIA free-tier API rate limiting under sustained load, not a bug — correctness
  holds, latency doesn't. See `ikis-backend/BENCHMARK_RESULTS.md` for real numbers.
- **Uploaded documents don't survive a redeploy.** The free-tier deployment has no
  persistent disk — a code redeploy wipes the knowledge base back to empty. Re-upload
  after any redeploy.
- **It's one shared instance.** Everyone using the live link shares the same
  knowledge base and the same API rate limit — not a private sandbox per visitor.

---

*IKIS — Industrial Knowledge Intelligence System · ET AI Hackathon 2026*
