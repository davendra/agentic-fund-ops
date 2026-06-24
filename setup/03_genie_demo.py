#!/usr/bin/env python
"""Stage 6 (showcase) - ask the Genie Space natural-language questions.

Genie translates each question to SQL over the governed silver tables; we run the
SQL to capture the answer. Saves a transcript (question -> generated SQL -> answer)
to reports/genie-demo.json for the writeup.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fundops_lib as fo  # noqa: E402

QUESTIONS = [
    "What is the total capital called across all funds, by currency?",
    "Which 5 distributions had the largest total proceeds? Show the fund and amount.",
    "How many capital calls and distributions were processed per fund?",
    "Which documents failed a validation check? Show the file and check name.",
]


def attachment_sql(att) -> str | None:
    q = getattr(att, "query", None)
    if q is not None:
        return getattr(q, "query", None)
    return None


def attachment_text(att) -> str | None:
    t = getattr(att, "text", None)
    if t is not None:
        return getattr(t, "content", None)
    return None


def main() -> int:
    w = fo.client()
    spaces = list(w.genie.list_spaces().spaces or [])
    space = next((s for s in spaces if "Fund-Ops" in (s.title or "")), None)
    if not space:
        print("no Fund-Ops Genie space found"); return 1
    sid = space.space_id
    print(f"Genie space: {space.title} ({sid})\n")

    transcript = {"space_id": sid, "space_title": space.title, "exchanges": []}
    for q in QUESTIONS:
        print(f"Q: {q}")
        try:
            msg = w.genie.start_conversation_and_wait(sid, q)
        except Exception as e:  # noqa: BLE001
            print(f"   (genie error: {str(e)[:120]})\n")
            transcript["exchanges"].append({"question": q, "error": str(e)[:200]})
            continue
        sql, text = None, None
        for att in (msg.attachments or []):
            sql = sql or attachment_sql(att)
            text = text or attachment_text(att)
        answer_rows = None
        if sql:
            try:
                rows = fo.run_sql(sql, timeout_s=120)
                answer_rows = rows[:10]
            except Exception as e:  # noqa: BLE001
                answer_rows = [["(sql execution error)", str(e)[:100]]]
        print(f"   SQL: {(sql or '(none)')[:200]}")
        if text:
            print(f"   Genie: {text[:200]}")
        if answer_rows:
            for r in answer_rows[:5]:
                print("   -> " + " | ".join(str(x)[:30] for x in r))
        print()
        transcript["exchanges"].append(
            {"question": q, "generated_sql": sql, "genie_text": text, "answer_sample": answer_rows}
        )

    (Path(__file__).resolve().parents[1] / "reports" / "genie-demo.json").write_text(
        json.dumps(transcript, indent=2, default=str)
    )
    ok = sum(1 for e in transcript["exchanges"] if e.get("generated_sql"))
    print(f"captured {ok}/{len(QUESTIONS)} NL->SQL exchanges -> reports/genie-demo.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
