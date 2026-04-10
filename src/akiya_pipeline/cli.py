"""コマンドラインインターフェース。

例:
  # CKANから取得して正規化・突合し JSON/JSONL を出力
  akiya-pipeline build --fetch --out-dir dist

  # ローカルCSVを使う
  akiya-pipeline build \
      --registered data/raw/01_tourokubukken.csv \
      --closed data/raw/02_seiyakubukken.csv --out-dir dist
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import pipeline, sources


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="akiya-pipeline", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="正規化・突合して JSON/JSONL を出力")
    b.add_argument("--fetch", action="store_true", help="CKANから元CSVを取得する")
    b.add_argument("--raw-dir", default="data/raw", help="元CSVの取得/参照先ディレクトリ")
    b.add_argument("--registered", help="登録物件CSVのパス（--fetch 時は不要）")
    b.add_argument("--closed", help="成約物件CSVのパス（--fetch 時は不要）")
    b.add_argument("--out-dir", default="dist", help="出力ディレクトリ")
    b.add_argument("--year", type=int, default=sources.DATASET_YEAR, help="出力ファイル名の年度")

    args = parser.parse_args(argv)
    if args.command == "build":
        return _build(args)
    return 1


def _build(args: argparse.Namespace) -> int:
    raw_dir = Path(args.raw_dir)
    if args.fetch:
        reg = sources.download(sources.REGISTERED, raw_dir)
        clo = sources.download(sources.CLOSED, raw_dir)
    else:
        reg = Path(args.registered or raw_dir / sources.REGISTERED.filename)
        clo = Path(args.closed or raw_dir / sources.CLOSED.filename)

    for p in (reg, clo):
        if not p.exists():
            print(f"error: 元CSVが見つかりません: {p}（--fetch で取得できます）", file=sys.stderr)
            return 2

    records = pipeline.build(reg, clo)
    summary = pipeline.summarize(records)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pipeline.write_json(records, out_dir / f"akiya-{args.year}.json")
    pipeline.write_jsonl(records, out_dir / f"akiya-{args.year}.jsonl")
    (out_dir / "manifest.json").write_text(
        json.dumps(pipeline.manifest(records), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"出力先: {out_dir}/akiya-{args.year}.json / .jsonl / manifest.json")
    print("件数:", json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
