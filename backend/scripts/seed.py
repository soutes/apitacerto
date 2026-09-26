"""Carga inicial do banco sem internet (HW3 etapa 4).

Exporta o banco local (SQLite, ja com o scraping da CBF e as estatisticas
calculadas) para um arquivo versionado, e carrega esse arquivo num banco
vazio (Postgres no Docker Compose / Kubernetes). Assim container, CI e teste
nunca dependem da API da CBF estar no ar.

Uso:
    uv run python scripts/seed.py export            # apitacerto.db -> seed/apitacerto.json.gz
    DATABASE_URL=postgresql+psycopg://... python scripts/seed.py load
    DATABASE_URL=postgresql+psycopg://... python scripts/seed.py load --replace

`load` e idempotente: banco que ja tem jogos nao e tocado. `--replace` apaga
tudo e recarrega (uma transacao so) -- pra levar pra producao dado que nao
vem do scraping semanal, como as temporadas antigas do Transfermarkt.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

from sqlalchemy import Engine, func, select, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ no path

from app.db import Base, engine as default_engine, ensure_schema  # noqa: E402
from app.models import Fixture  # noqa: E402

SEED_FILE = Path(__file__).resolve().parents[1] / "seed" / "apitacerto.json.gz"
FORMAT_VERSION = 1


def _tables():
    return Base.metadata.sorted_tables  # pais antes dos filhos (FKs)


def export_seed(engine: Engine, path: Path = SEED_FILE) -> dict[str, int]:
    ensure_schema(bind=engine)
    data: dict[str, list[dict]] = {}
    with engine.connect() as conn:
        for table in _tables():
            pk = list(table.primary_key.columns)
            rows = conn.execute(select(table).order_by(*pk)).mappings().all()
            data[table.name] = [dict(r) for r in rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    # mtime=0 e sem nome no cabecalho: mesmo banco -> mesmo arquivo, sem
    # diff falso no git
    with open(path, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as fh:
        fh.write(json.dumps({"format": FORMAT_VERSION, "tables": data},
                            ensure_ascii=False, sort_keys=True).encode("utf-8"))
    return {name: len(rows) for name, rows in data.items()}


def load_seed(engine: Engine, path: Path = SEED_FILE, replace: bool = False) -> dict[str, int] | None:
    """Carrega o arquivo num banco vazio. Devolve None se o banco ja tinha
    jogos (nada e alterado), a menos que replace=True."""
    ensure_schema(bind=engine)
    if not replace:
        with engine.connect() as conn:
            if conn.scalar(select(func.count()).select_from(Fixture.__table__)):
                return None

    with gzip.open(path, "rb") as fh:
        doc = json.loads(fh.read().decode("utf-8"))
    if doc.get("format") != FORMAT_VERSION:
        raise SystemExit(f"formato de seed desconhecido: {doc.get('format')}")

    counts = {}
    with engine.begin() as conn:
        if replace:
            for table in reversed(_tables()):  # filhos antes dos pais (FKs)
                conn.execute(table.delete())
        for table in _tables():
            rows = doc["tables"].get(table.name, [])
            for start in range(0, len(rows), 5000):
                conn.execute(table.insert(), rows[start:start + 5000])
            counts[table.name] = len(rows)
        if engine.dialect.name == "postgresql":
            # ids vieram explicitos do arquivo: a sequence precisa andar junto,
            # senao o proximo scraping tenta reusar id 1
            for table in _tables():
                if "id" in table.c and table.c.id.primary_key:
                    conn.execute(text(
                        f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                        f"COALESCE((SELECT MAX(id) FROM {table.name}), 0) + 1, false)"
                    ))
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["export", "load"])
    parser.add_argument("--file", type=Path, default=SEED_FILE)
    parser.add_argument("--replace", action="store_true", help="load: apaga o banco e recarrega")
    args = parser.parse_args()

    if args.action == "export":
        counts = export_seed(default_engine, args.file)
        print(f"exportado para {args.file}: {counts}")
        return

    counts = load_seed(default_engine, args.file, replace=args.replace)
    if counts is None:
        print("banco ja tem jogos, seed nao aplicado")
    else:
        print(f"seed carregado: {counts}")


if __name__ == "__main__":
    main()
