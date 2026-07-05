# IKIS Expert Query — Benchmark Results

Automated keyword-coverage proxy over 8 questions grounded in the uploaded sample_docs/ corpus — **not** a substitute for real domain-expert grading, but a repeatable regression check. Pass = at least one expected keyword found in the answer (or, for the negative control, an honest "not found" response).

**Score: 8/8 passed** · avg RAG response time: 15.4s

## Time-to-answer vs. traditional (keyword) search

- Naive SQL keyword search across the same corpus: avg 2ms to *locate* candidate documents — but returns raw document matches, not an answer. A person still has to open each match and read it to find the actual fact.
- RAG endpoint: avg 15.4s to return a synthesized, cited answer directly addressing the question.
- Honest takeaway: keyword search is faster at the *retrieval* step in raw milliseconds; RAG is faster at *time to a usable answer*, because it skips the manual read-and-synthesize step entirely. The comparison that matters isn't search-ms vs answer-s, it's "minutes of manual cross-referencing" vs "15 seconds".

## Results

| # | Question | Pass | Confidence | RAG time | Matched keywords |
|---|---|---|---|---|---|
| 1 | What is the rated flow and pressure of PUMP-001? | ✅ | 1.00 | 13.2s | 450 gpm, 120 psi |
| 2 | Who was the certified inspector for the Q2 2026 pressure vessel inspection? | ✅ | 1.00 | 38.0s | m. rao, rao |
| 3 | What safety procedure governs the emergency shutdown of rotating equipment like PUMP-001? | ✅ | 1.00 | 11.5s | sp-014 |
| 4 | What caused the unplanned trip on TURBINE-04? | ✅ | 1.00 | 10.4s | lubricant, bearing |
| 5 | How many times was the COMPRESSOR-02 seal replacement deferred before the near-miss? | ✅ | 1.00 | 8.2s | twice |
| 6 | Within how many days must training acknowledgment be logged in the LMS after a refresher cycle? | ✅ | 1.00 | 5.9s | 30 days |
| 7 | According to the Q1-Q2 2026 audit finding, what process gap is common across the PUMP-001, COMPRESSOR-02, and TURBINE-04 incidents? | ✅ | 1.00 | 11.4s | safety review, deferr |
| 8 | Hi (negative control) | ✅ | 0.00 | 24.7s | didn't |

## Full answers

**1. What is the rated flow and pressure of PUMP-001?**

The rated flow of PUMP-001 is 450 GPM and the rated pressure is 120 PSI, as stated in the EQUIPMENT MANUAL: Centrifugal Pump CP-2000 (PUMP-001) under section 1. OVERVIEW.

---

**2. Who was the certified inspector for the Q2 2026 pressure vessel inspection?**

The certified inspector for the Q2 2026 pressure vessel inspection was M. Rao, as mentioned in the QUARTERLY INSPECTION REPORT - Q2 2026.

---

**3. What safety procedure governs the emergency shutdown of rotating equipment like PUMP-001?**

The safety procedure governing the emergency shutdown of rotating equipment like PUMP-001 is defined in Safety Procedure SP-014: Emergency Shutdown - Rotating Equipment. This procedure outlines the steps to be taken in case of a vibration alarm, seal failure, or unplanned high-temperature event, including triggering a local E-stop, isolating the equipment, verifying zero energy state, logging the incident, and notifying the plant safety lead. The procedure also requires annual refresher training for all operators.

---

**4. What caused the unplanned trip on TURBINE-04?**

The unplanned trip on TURBINE-04 was caused by the degradation of the lubricant below specification, resulting in elevated bearing friction. This was due to the lubricant replacement being deferred three times over 11 weeks for 'production schedule priority' reasons, despite a lubrication system inspection (WO-3390, 2026-03-15) recommending replacement within 30 days. (Source: UNPLANNED TRIP REPORT - TURBINE-04)

---

**5. How many times was the COMPRESSOR-02 seal replacement deferred before the near-miss?**

The COMPRESSOR-02 seal replacement was deferred twice before the near-miss incident. (Source: NEAR-MISS INCIDENT REPORT - COMPRESSOR-02, INTERNAL AUDIT FINDING - MAINTENANCE DEFERRAL PATTERN)

---

**6. Within how many days must training acknowledgment be logged in the LMS after a refresher cycle?**

Training acknowledgment must be logged in the LMS within 30 days of the refresh cycle.

---

**7. According to the Q1-Q2 2026 audit finding, what process gap is common across the PUMP-001, COMPRESSOR-02, and TURBINE-04 incidents?**

According to the Q1-Q2 2026 audit finding, the common process gap across the PUMP-001, COMPRESSOR-02, and TURBINE-04 incidents is the lack of a mandatory safety review gate before an inspector-recommended action can be deferred more than once for 'production schedule' reasons. (Source: INTERNAL AUDIT FINDING - MAINTENANCE DEFERRAL PATTERN, Auditor: P. Krishnan, Internal Quality & Safety Audit, Date: 2026-06-28)

---

**8. Hi**

I didn't find anything about a greeting or small talk topic in the uploaded documents, so I'm not sure how to respond to 'Hi'.

---

