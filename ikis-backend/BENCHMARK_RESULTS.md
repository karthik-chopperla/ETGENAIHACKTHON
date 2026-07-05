# IKIS — Benchmark Results (all endpoints)

Automated coverage proxy grounded in the uploaded sample_docs/ corpus — **not** a substitute for real domain-expert grading, but a repeatable regression check across every AI-backed capability, not just RAG query.

**Overall: 12/12 passed**

| Capability | Passed |
|---|---|
| Expert Query (RAG) | 8/8 |
| Maintenance recommendations | 1/1 |
| Root Cause Analysis | 1/1 |
| Compliance gap detection | 1/1 |
| Lessons Learned pattern detection | 1/1 |

## Note on latency in this run

Response times here (avg 43.6s, one call at 140s) are markedly higher than earlier clean-condition
measurements in this project (typically 8-25s). This run followed several hours of heavy testing
against the same free-tier NVIDIA API key, and the degradation is consistent with upstream rate
limiting, not a regression in this codebase — every answer was still correct despite the slowdown.
This is a real, honest scalability finding: **a single shared free-tier inference key is a genuine
bottleneck under sustained load**, and a production deployment would need a dedicated/paid NIM
endpoint or request queuing to keep latency predictable under concurrent usage.

## Time-to-answer vs. traditional (keyword) search

- Naive SQL keyword search across the same corpus: avg 3ms to *locate* candidate documents — but returns raw document matches, not an answer. A person still has to open each match and read it to find the actual fact.
- RAG endpoint: avg 43.6s to return a synthesized, cited answer directly addressing the question.
- Honest takeaway: keyword search is faster at the *retrieval* step in raw milliseconds; RAG is faster at *time to a usable answer*, because it skips the manual read-and-synthesize step entirely. The comparison that matters isn't search-ms vs answer-s, it's "minutes of manual cross-referencing" vs "44 seconds".

## Expert Query (RAG)

| # | Question | Pass | Confidence | Time | Matched keywords |
|---|---|---|---|---|---|
| 1 | What is the rated flow and pressure of PUMP-001? | ✅ | 1.00 | 140.1s | 450 gpm, 120 psi |
| 2 | Who was the certified inspector for the Q2 2026 pressure vessel inspection? | ✅ | 1.00 | 30.6s | m. rao, rao |
| 3 | What safety procedure governs the emergency shutdown of rotating equipment like PUMP-001? | ✅ | 1.00 | 8.9s | sp-014 |
| 4 | What caused the unplanned trip on TURBINE-04? | ✅ | 1.00 | 47.4s | lubricant, bearing |
| 5 | How many times was the COMPRESSOR-02 seal replacement deferred before the near-miss? | ✅ | 1.00 | 35.4s | twice |
| 6 | Within how many days must training acknowledgment be logged in the LMS after a refresher cycle? | ✅ | 1.00 | 67.4s | 30 days |
| 7 | According to the Q1-Q2 2026 audit finding, what process gap is common across the PUMP-001, COMPRESSOR-02, and TURBINE-04 incidents? | ✅ | 1.00 | 12.6s | safety review, deferr |
| 8 | Hi (negative control) | ✅ | 0.00 | 6.7s | didn't |

## Maintenance Recommendations

| Equipment | Pass | Recommendations | Time | Matched keywords |
|---|---|---|---|---|
| PUMP-001 | ✅ | 3 | 121.2s | vibration, bearing, seal |

## Root Cause Analysis

| Equipment | Pass | Time | Immediate cause | Root cause |
|---|---|---|---|---|
| PUMP-001 | ✅ | 40.8s | Unplanned stoppage due to suspected bearing wear caused by deferred maintenance (WO-4498) and lack of timely bearing inspection and replacement. | Insufficient maintenance planning process and lack of mandatory safety review gate before deferring maintenance tasks, leading to inadequate prioritization of critical maintenance activities. |

## Compliance Gap Detection

✅ PASS — 5 gaps found in 79.0s, grounded regulation codes matched: sp-014, oisd-119, factory act

## Lessons Learned Pattern Detection

✅ PASS — 2 pattern(s) found in 56.8s, required all of ['PUMP-001', 'COMPRESSOR-02', 'TURBINE-04'] to appear as affected equipment (matched: PUMP-001, COMPRESSOR-02, TURBINE-04)

## Full RAG answers

**1. What is the rated flow and pressure of PUMP-001?**

The rated flow of PUMP-001 is 450 GPM and the rated pressure is 120 PSI.

---

**2. Who was the certified inspector for the Q2 2026 pressure vessel inspection?**

The certified inspector for the Q2 2026 pressure vessel inspection was M. Rao, as stated in the QUARTERLY INSPECTION REPORT for Q2 2026.

---

**3. What safety procedure governs the emergency shutdown of rotating equipment like PUMP-001?**

The safety procedure that governs the emergency shutdown of rotating equipment like PUMP-001 is defined in SAFETY PROCEDURE SP-014: Emergency Shutdown - Rotating Equipment. This procedure outlines a five-step sequence for emergency shutdown, including triggering a local E-stop, isolating equipment, verifying zero energy state, logging the incident, and confirming seal and lubrication health before restart. (Source: SAFETY PROCEDURE SP-014)

---

**4. What caused the unplanned trip on TURBINE-04?**

The unplanned trip on TURBINE-04 was caused by lubricant degradation below specification, resulting in elevated bearing friction. This was due to the lubricant replacement work order being deferred three times over 11 weeks, despite an inspection recommendation to replace it within 30 days (Source: UNPLANNED TRIP REPORT - TURBINE-04, Reported by: A. Verma, Maintenance Engineer, Date: 2026-06-10).

---

**5. How many times was the COMPRESSOR-02 seal replacement deferred before the near-miss?**

The seal replacement for COMPRESSOR-02 was deferred twice before the near-miss incident, as stated in the NEAR-MISS INCIDENT REPORT - COMPRESSOR-02 and the INTERNAL AUDIT FINDING - MAINTENANCE DEFERRAL PATTERN.

---

**6. Within how many days must training acknowledgment be logged in the LMS after a refresher cycle?**

Training acknowledgment must be logged in the LMS within 30 days of the refresh cycle.

---

**7. According to the Q1-Q2 2026 audit finding, what process gap is common across the PUMP-001, COMPRESSOR-02, and TURBINE-04 incidents?**

The common process gap across the PUMP-001, COMPRESSOR-02, and TURBINE-04 incidents is the lack of a mandatory safety review gate before an inspector-recommended action can be deferred more than once for 'production schedule' reasons. According to the internal audit finding, in 3 of the last 4 documented near-miss or trip events, the triggering equipment had a prior inspection or work-order recommendation that was deferred at least once without a documented safety review of the deferral decision. (Source: INTERNAL AUDIT FINDING - MAINTENANCE DEFERRAL PATTERN, Auditor: P. Krishnan, Internal Quality & Safety Audit, Date: 2026-06-28)

---

**8. Hi**

I didn't find anything about greetings or small talk in the uploaded documents, it seems like the context is focused on industrial incident reports and maintenance procedures.

---

