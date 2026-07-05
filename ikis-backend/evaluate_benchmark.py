"""
Benchmark evaluation for IKIS — covers every AI-backed endpoint, not just RAG.

Runs domain questions/checks grounded in the facts actually present in
sample_docs/ once uploaded, against the live backend. Each capability is
scored by keyword/content coverage (an automated proxy, not a substitute for
real domain-expert grading), and timed. Also compares RAG time-to-answer
against a naive keyword search baseline over the same corpus, to give an
honest picture of what "faster than traditional search" does and doesn't
mean here.

Prerequisites: backend running at BACKEND_URL with all 7 sample_docs/ files
already uploaded (see sample_data.py + README Quick Start).

Run: python evaluate_benchmark.py
Writes: BENCHMARK_RESULTS.md
"""

import time
import sqlite3
import requests

BACKEND_URL = "http://localhost:8000"
DB_PATH = "ikis.db"

RAG_BENCHMARK = [
    {
        "question": "What is the rated flow and pressure of PUMP-001?",
        "expected_keywords": ["450 gpm", "120 psi"],
    },
    {
        "question": "Who was the certified inspector for the Q2 2026 pressure vessel inspection?",
        "expected_keywords": ["m. rao", "rao"],
    },
    {
        "question": "What safety procedure governs the emergency shutdown of rotating equipment like PUMP-001?",
        "expected_keywords": ["sp-014"],
    },
    {
        "question": "What caused the unplanned trip on TURBINE-04?",
        "expected_keywords": ["lubricant", "bearing"],
    },
    {
        "question": "How many times was the COMPRESSOR-02 seal replacement deferred before the near-miss?",
        "expected_keywords": ["twice", "two"],
    },
    {
        "question": "Within how many days must training acknowledgment be logged in the LMS after a refresher cycle?",
        "expected_keywords": ["30 days"],
    },
    {
        "question": "According to the Q1-Q2 2026 audit finding, what process gap is common across the PUMP-001, COMPRESSOR-02, and TURBINE-04 incidents?",
        "expected_keywords": ["safety review", "deferr"],
    },
    {
        "question": "Hi",
        "expected_keywords": ["don't", "didn't", "no information", "not find", "not have"],
        "is_negative_control": True,
    },
]

MAINTENANCE_BENCHMARK = [
    {
        "equipment_id": "PUMP-001",
        "expected_keywords": ["vibration", "bearing", "seal"],
    },
]

RCA_BENCHMARK = [
    {
        "equipment_id": "PUMP-001",
        "expected_immediate_keywords": ["stoppage", "bearing"],
        "expected_root_keywords": ["deferr", "safety review", "production"],
    },
]

# Compliance gaps are LLM-generated each run and non-deterministic in exact
# wording, so this checks for presence of *any* regulation code we know is
# grounded in the uploaded corpus, not an exact match.
COMPLIANCE_BENCHMARK = {
    "expected_any_of": ["sp-014", "oisd-119", "factory act", "oisd-std-137"],
}

# The known genuine cross-document pattern spans these three equipment IDs.
LESSONS_BENCHMARK = {
    "expected_equipment": ["PUMP-001", "COMPRESSOR-02", "TURBINE-04"],
}


def query_rag(question):
    start = time.time()
    resp = requests.post(
        f"{BACKEND_URL}/api/query",
        json={"query": question, "include_citations": True},
        timeout=240,
    )
    elapsed = time.time() - start
    resp.raise_for_status()
    return resp.json(), elapsed


def query_maintenance(equipment_id):
    start = time.time()
    resp = requests.get(f"{BACKEND_URL}/api/maintenance/recommendations/{equipment_id}", timeout=240)
    elapsed = time.time() - start
    resp.raise_for_status()
    return resp.json(), elapsed


def query_rca(equipment_id):
    start = time.time()
    resp = requests.get(f"{BACKEND_URL}/api/maintenance/rca/{equipment_id}", timeout=240)
    elapsed = time.time() - start
    resp.raise_for_status()
    return resp.json(), elapsed


def query_compliance():
    start = time.time()
    resp = requests.get(f"{BACKEND_URL}/api/compliance/gaps", timeout=240)
    elapsed = time.time() - start
    resp.raise_for_status()
    return resp.json(), elapsed


def query_lessons_learned():
    start = time.time()
    resp = requests.get(f"{BACKEND_URL}/api/lessons-learned/patterns", timeout=240)
    elapsed = time.time() - start
    resp.raise_for_status()
    return resp.json(), elapsed


def naive_keyword_search(keywords):
    """Baseline: how long does it take to just locate matching documents
    (no synthesis, no answer — the user would still have to read them)?"""
    start = time.time()
    conn = sqlite3.connect(DB_PATH)
    matches = []
    for kw in keywords:
        rows = conn.execute(
            "SELECT id FROM documents WHERE lower(content) LIKE ?", (f"%{kw.lower()}%",)
        ).fetchall()
        matches.extend(r[0] for r in rows)
    conn.close()
    elapsed = time.time() - start
    return sorted(set(matches)), elapsed


def score_text(text, expected_keywords):
    lowered = text.lower()
    hits = [kw for kw in expected_keywords if kw.lower() in lowered]
    return hits, len(hits) > 0


def run_rag_benchmark():
    rows = []
    total_rag_time = 0.0
    total_search_time = 0.0
    passed = 0
    for case in RAG_BENCHMARK:
        question = case["question"]
        expected = case["expected_keywords"]
        result, rag_time = query_rag(question)
        answer = result.get("answer", "")
        confidence = result.get("confidence", 0.0)
        hits, ok = score_text(answer, expected)
        _, search_time = naive_keyword_search(expected)
        total_rag_time += rag_time
        total_search_time += search_time
        passed += int(ok)
        rows.append({
            "question": question, "answer": answer, "confidence": confidence,
            "hits": hits, "pass": ok, "rag_time": rag_time,
            "negative_control": case.get("is_negative_control", False),
        })
        print(f"[RAG] {'PASS' if ok else 'FAIL'}  ({rag_time:.1f}s, conf={confidence:.2f})  {question}")
    return rows, passed, len(RAG_BENCHMARK), total_rag_time, total_search_time


def run_maintenance_benchmark():
    rows = []
    passed = 0
    for case in MAINTENANCE_BENCHMARK:
        eq = case["equipment_id"]
        result, elapsed = query_maintenance(eq)
        recs = result.get("recommendations", [])
        combined = " ".join(f"{r.get('action', '')} {' '.join(r.get('supporting_evidence', []))}" for r in recs)
        hits, ok = score_text(combined, case["expected_keywords"])
        passed += int(ok)
        rows.append({"equipment_id": eq, "recommendation_count": len(recs), "hits": hits, "pass": ok, "time": elapsed})
        print(f"[Maintenance] {'PASS' if ok else 'FAIL'}  ({elapsed:.1f}s, {len(recs)} recs)  {eq}")
    return rows, passed, len(MAINTENANCE_BENCHMARK)


def run_rca_benchmark():
    rows = []
    passed = 0
    for case in RCA_BENCHMARK:
        eq = case["equipment_id"]
        result, elapsed = query_rca(eq)
        report = result.get("report") or {}
        imm_hits, imm_ok = score_text(report.get("immediate_cause", ""), case["expected_immediate_keywords"])
        root_hits, root_ok = score_text(report.get("root_cause", ""), case["expected_root_keywords"])
        ok = imm_ok and root_ok
        passed += int(ok)
        rows.append({
            "equipment_id": eq, "pass": ok, "time": elapsed,
            "immediate_cause": report.get("immediate_cause", ""),
            "root_cause": report.get("root_cause", ""),
            "immediate_hits": imm_hits, "root_hits": root_hits,
        })
        print(f"[RCA] {'PASS' if ok else 'FAIL'}  ({elapsed:.1f}s)  {eq}")
    return rows, passed, len(RCA_BENCHMARK)


def run_compliance_benchmark():
    result, elapsed = query_compliance()
    gaps = result.get("gaps", [])
    combined = " ".join(f"{g.get('regulation_code', '')} {g.get('requirement', '')}" for g in gaps)
    hits, ok = score_text(combined, COMPLIANCE_BENCHMARK["expected_any_of"])
    print(f"[Compliance] {'PASS' if ok else 'FAIL'}  ({elapsed:.1f}s, {len(gaps)} gaps)")
    return {"gaps_found": len(gaps), "hits": hits, "pass": ok, "time": elapsed}, int(ok), 1


def run_lessons_learned_benchmark():
    result, elapsed = query_lessons_learned()
    patterns = result.get("patterns", [])
    all_equipment = " ".join(" ".join(p.get("affected_equipment", [])) for p in patterns)
    hits, ok = score_text(all_equipment.upper(), [e.upper() for e in LESSONS_BENCHMARK["expected_equipment"]])
    ok = len(hits) == len(LESSONS_BENCHMARK["expected_equipment"])  # require ALL three, not just one
    print(f"[Lessons Learned] {'PASS' if ok else 'FAIL'}  ({elapsed:.1f}s, {len(patterns)} patterns)")
    return {"patterns_found": len(patterns), "hits": hits, "pass": ok, "time": elapsed}, int(ok), 1


def main():
    rag_rows, rag_passed, rag_n, total_rag_time, total_search_time = run_rag_benchmark()
    time.sleep(5)
    maint_rows, maint_passed, maint_n = run_maintenance_benchmark()
    time.sleep(5)
    rca_rows, rca_passed, rca_n = run_rca_benchmark()
    time.sleep(5)
    compliance_result, compliance_passed, compliance_n = run_compliance_benchmark()
    time.sleep(5)
    lessons_result, lessons_passed, lessons_n = run_lessons_learned_benchmark()

    total_passed = rag_passed + maint_passed + rca_passed + compliance_passed + lessons_passed
    total_n = rag_n + maint_n + rca_n + compliance_n + lessons_n

    with open("BENCHMARK_RESULTS.md", "w", encoding="utf-8") as f:
        f.write("# IKIS — Benchmark Results (all endpoints)\n\n")
        f.write(
            "Automated coverage proxy grounded in the uploaded sample_docs/ corpus — **not** a "
            "substitute for real domain-expert grading, but a repeatable regression check across "
            "every AI-backed capability, not just RAG query.\n\n"
        )
        f.write(f"**Overall: {total_passed}/{total_n} passed**\n\n")
        f.write("| Capability | Passed |\n|---|---|\n")
        f.write(f"| Expert Query (RAG) | {rag_passed}/{rag_n} |\n")
        f.write(f"| Maintenance recommendations | {maint_passed}/{maint_n} |\n")
        f.write(f"| Root Cause Analysis | {rca_passed}/{rca_n} |\n")
        f.write(f"| Compliance gap detection | {compliance_passed}/{compliance_n} |\n")
        f.write(f"| Lessons Learned pattern detection | {lessons_passed}/{lessons_n} |\n\n")

        f.write("## Time-to-answer vs. traditional (keyword) search\n\n")
        f.write(
            f"- Naive SQL keyword search across the same corpus: avg {total_search_time/rag_n*1000:.0f}ms "
            f"to *locate* candidate documents — but returns raw document matches, not an answer. "
            f"A person still has to open each match and read it to find the actual fact.\n"
            f"- RAG endpoint: avg {total_rag_time/rag_n:.1f}s to return a synthesized, cited answer "
            f"directly addressing the question.\n"
            f"- Honest takeaway: keyword search is faster at the *retrieval* step in raw milliseconds; "
            f"RAG is faster at *time to a usable answer*, because it skips the manual read-and-synthesize "
            f"step entirely. The comparison that matters isn't search-ms vs answer-s, it's \"minutes of "
            f"manual cross-referencing\" vs \"{total_rag_time/rag_n:.0f} seconds\".\n\n"
        )

        f.write("## Expert Query (RAG)\n\n")
        f.write("| # | Question | Pass | Confidence | Time | Matched keywords |\n|---|---|---|---|---|---|\n")
        for i, r in enumerate(rag_rows, 1):
            tag = " (negative control)" if r["negative_control"] else ""
            f.write(f"| {i} | {r['question']}{tag} | {'✅' if r['pass'] else '❌'} | {r['confidence']:.2f} | {r['rag_time']:.1f}s | {', '.join(r['hits']) or '—'} |\n")

        f.write("\n## Maintenance Recommendations\n\n")
        f.write("| Equipment | Pass | Recommendations | Time | Matched keywords |\n|---|---|---|---|---|\n")
        for r in maint_rows:
            f.write(f"| {r['equipment_id']} | {'✅' if r['pass'] else '❌'} | {r['recommendation_count']} | {r['time']:.1f}s | {', '.join(r['hits']) or '—'} |\n")

        f.write("\n## Root Cause Analysis\n\n")
        f.write("| Equipment | Pass | Time | Immediate cause | Root cause |\n|---|---|---|---|---|\n")
        for r in rca_rows:
            f.write(f"| {r['equipment_id']} | {'✅' if r['pass'] else '❌'} | {r['time']:.1f}s | {r['immediate_cause']} | {r['root_cause']} |\n")

        f.write("\n## Compliance Gap Detection\n\n")
        f.write(
            f"{'✅ PASS' if compliance_result['pass'] else '❌ FAIL'} — {compliance_result['gaps_found']} gaps "
            f"found in {compliance_result['time']:.1f}s, grounded regulation codes matched: "
            f"{', '.join(compliance_result['hits']) or 'none'}\n\n"
        )

        f.write("## Lessons Learned Pattern Detection\n\n")
        f.write(
            f"{'✅ PASS' if lessons_result['pass'] else '❌ FAIL'} — {lessons_result['patterns_found']} pattern(s) "
            f"found in {lessons_result['time']:.1f}s, required all of "
            f"{LESSONS_BENCHMARK['expected_equipment']} to appear as affected equipment "
            f"(matched: {', '.join(lessons_result['hits']) or 'none'})\n\n"
        )

        f.write("## Full RAG answers\n\n")
        for i, r in enumerate(rag_rows, 1):
            f.write(f"**{i}. {r['question']}**\n\n{r['answer']}\n\n---\n\n")

    print(f"\nOverall: {total_passed}/{total_n} passed. Written to BENCHMARK_RESULTS.md")


if __name__ == "__main__":
    main()
