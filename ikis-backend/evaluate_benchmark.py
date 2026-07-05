"""
Benchmark evaluation for IKIS's Expert Query (RAG) endpoint.

Runs a small set of domain questions — grounded in the facts actually present
in sample_docs/ once uploaded — against the live backend, scores each answer
by keyword coverage (an automated proxy, not a substitute for real domain-
expert grading), times the response, and compares against a naive keyword
search baseline over the same corpus to give an honest picture of what "faster
than traditional search" does and doesn't mean here.

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

BENCHMARK = [
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


def query_rag(question):
    start = time.time()
    resp = requests.post(
        f"{BACKEND_URL}/api/query",
        json={"query": question, "include_citations": True},
        timeout=120,
    )
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


def score_answer(answer_text, expected_keywords):
    lowered = answer_text.lower()
    hits = [kw for kw in expected_keywords if kw.lower() in lowered]
    return hits, len(hits) > 0


def main():
    rows = []
    total_rag_time = 0.0
    total_search_time = 0.0
    passed = 0

    for case in BENCHMARK:
        question = case["question"]
        expected = case["expected_keywords"]

        result, rag_time = query_rag(question)
        answer = result.get("answer", "")
        confidence = result.get("confidence", 0.0)
        hits, ok = score_answer(answer, expected)

        _, search_time = naive_keyword_search(expected)

        total_rag_time += rag_time
        total_search_time += search_time
        passed += int(ok)

        rows.append({
            "question": question,
            "answer": answer,
            "confidence": confidence,
            "expected": expected,
            "hits": hits,
            "pass": ok,
            "rag_time": rag_time,
            "search_time": search_time,
            "negative_control": case.get("is_negative_control", False),
        })
        print(f"{'PASS' if ok else 'FAIL'}  ({rag_time:.1f}s, conf={confidence:.2f})  {question}")

    n = len(BENCHMARK)
    with open("BENCHMARK_RESULTS.md", "w", encoding="utf-8") as f:
        f.write("# IKIS Expert Query — Benchmark Results\n\n")
        f.write(
            f"Automated keyword-coverage proxy over {n} questions grounded in the uploaded "
            f"sample_docs/ corpus — **not** a substitute for real domain-expert grading, but a "
            f"repeatable regression check. Pass = at least one expected keyword found in the "
            f"answer (or, for the negative control, an honest \"not found\" response).\n\n"
        )
        f.write(f"**Score: {passed}/{n} passed** · avg RAG response time: {total_rag_time/n:.1f}s\n\n")
        f.write("## Time-to-answer vs. traditional (keyword) search\n\n")
        f.write(
            f"- Naive SQL keyword search across the same corpus: avg {total_search_time/n*1000:.0f}ms "
            f"to *locate* candidate documents — but returns raw document matches, not an answer. "
            f"A person still has to open each match and read it to find the actual fact.\n"
            f"- RAG endpoint: avg {total_rag_time/n:.1f}s to return a synthesized, cited answer "
            f"directly addressing the question.\n"
            f"- Honest takeaway: keyword search is faster at the *retrieval* step in raw milliseconds; "
            f"RAG is faster at *time to a usable answer*, because it skips the manual read-and-synthesize "
            f"step entirely. The comparison that matters isn't search-ms vs answer-s, it's \"minutes of "
            f"manual cross-referencing\" vs \"{total_rag_time/n:.0f} seconds\".\n\n"
        )
        f.write("## Results\n\n")
        f.write("| # | Question | Pass | Confidence | RAG time | Matched keywords |\n")
        f.write("|---|---|---|---|---|---|\n")
        for i, r in enumerate(rows, 1):
            tag = " (negative control)" if r["negative_control"] else ""
            f.write(
                f"| {i} | {r['question']}{tag} | {'✅' if r['pass'] else '❌'} | "
                f"{r['confidence']:.2f} | {r['rag_time']:.1f}s | {', '.join(r['hits']) or '—'} |\n"
            )
        f.write("\n## Full answers\n\n")
        for i, r in enumerate(rows, 1):
            f.write(f"**{i}. {r['question']}**\n\n{r['answer']}\n\n---\n\n")

    print(f"\nScore: {passed}/{n} passed. Written to BENCHMARK_RESULTS.md")


if __name__ == "__main__":
    main()
