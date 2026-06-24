#!/usr/bin/env python
"""Stage 1 - ingest fund documents into the Unity Catalog landing Volume.

If the full FundAdmin AI corpus is present locally, selects EVERY capital-call and
distribution PDF across all funds (the pipeline is tested over all of them) and
refreshes the committed dataset. Otherwise it uploads the dataset already committed
under corpus/landing/ - so a fresh clone runs end-to-end without the source corpus.
"""
from __future__ import annotations
import io
import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fundops_lib as fo  # noqa: E402

# Optional: point at the full FundAdmin AI sample corpus to re-select all
# call/distribution PDFs. If unset/absent, the committed corpus/landing/ is used.
CORPUS = Path(os.environ.get("FUNDOPS_CORPUS_DIR", "/nonexistent-corpus"))
REPO = Path(__file__).resolve().parents[1]
DATASET = REPO / "corpus" / "landing"


def doc_type_of(name: str) -> str | None:
    low = name.lower()
    if re.search(r"capital[-_ ]?call", low):
        return "capital_call"
    if re.search(r"capital[-_ ]?account", low):
        return "capital_account"
    if "distribution" in low:
        return "distribution"
    return None


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def refresh_dataset_from_corpus() -> None:
    """Re-select all call/distribution PDFs from the full corpus into corpus/landing."""
    all_files = [p for p in CORPUS.rglob("*") if p.is_file() and p.suffix.lower() != ".ds_store"]
    inv: dict[str, int] = {}
    for p in all_files:
        dt = doc_type_of(p.name) or "other"
        inv[dt] = inv.get(dt, 0) + 1
    (REPO / "corpus" / "full-corpus-inventory.json").write_text(json.dumps(
        {"corpus_root": str(CORPUS), "total_files": len(all_files),
         "by_type_filename_heuristic": dict(sorted(inv.items(), key=lambda kv: -kv[1])),
         "note": "Synthetic samples from the author's FundAdmin AI product. The pipeline processes "
                 "the capital_call + distribution PDFs; other types are inventoried only."}, indent=2))
    if DATASET.exists():
        shutil.rmtree(DATASET)
    DATASET.mkdir(parents=True, exist_ok=True)
    for p in sorted(CORPUS.rglob("*.pdf")):
        if doc_type_of(p.name):
            shutil.copyfile(p, DATASET / f"{slug(p.parent.name)}__{p.name}")
    print(f"corpus present: {len(all_files)} files; refreshed dataset with "
          f"{len(list(DATASET.glob('*.pdf')))} call/distribution PDFs")


def main() -> int:
    ns = fo.load_namespace()
    w = fo.client()
    vol = fo.volume_path(ns)

    if CORPUS.exists():
        refresh_dataset_from_corpus()
    else:
        print(f"corpus not found at {CORPUS}; using committed dataset corpus/landing/")

    pdfs = sorted(DATASET.glob("*.pdf"))
    if not pdfs:
        print("no PDFs to ingest"); return 1

    manifest, uploaded = [], 0
    for p in pdfs:
        dt = doc_type_of(p.name) or "distribution"
        vpath = f"{vol}/{p.name}"
        data = p.read_bytes()
        w.files.upload(vpath, io.BytesIO(data), overwrite=True)
        uploaded += 1
        manifest.append({"file": p.name, "doc_type": dt, "volume_path": vpath, "size_bytes": len(data)})
        if uploaded % 10 == 0:
            print(f"  uploaded {uploaded}/{len(pdfs)} ...", flush=True)

    by_type: dict[str, int] = {}
    for m in manifest:
        by_type[m["doc_type"]] = by_type.get(m["doc_type"], 0) + 1
    (REPO / "corpus" / "landing-manifest.json").write_text(
        json.dumps({"count": len(manifest), "by_type": by_type, "documents": manifest}, indent=2))
    (REPO / "reports" / "ingest-manifest.json").write_text(
        json.dumps({"volume": vol, "count": len(manifest), "documents": manifest}, indent=2))

    listed = list(w.files.list_directory_contents(vol))
    print(f"\nuploaded {uploaded} PDFs ({by_type}); Volume lists {len(listed)} entries at {vol}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
