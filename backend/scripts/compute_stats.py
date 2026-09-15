"""Calcula a aba Dados estatisticos (spec secao 9) e grava em stat_reports.

Offline: precisa do grupo de dependencias 'analysis' (numpy/scipy/pandas/
statsmodels), que o `uv run` local ja traz (esta incluido no grupo dev). O
scripts/scrape_cbf.py tambem chama isto ao terminar.

Uso:
    uv run python scripts/compute_stats.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ no path

from app.analysis.report import compute_and_store  # noqa: E402
from app.db import SessionLocal, ensure_schema  # noqa: E402


def main() -> None:
    ensure_schema()
    started = time.time()
    with SessionLocal() as db:
        keys = compute_and_store(db)
    print(f"estatisticas gravadas: {', '.join(keys) or 'nenhuma (banco vazio)'} ({time.time() - started:.0f}s)")


if __name__ == "__main__":
    main()
