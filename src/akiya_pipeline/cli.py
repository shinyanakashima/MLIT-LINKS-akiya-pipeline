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

    c = sub.add_parser("classify", help="STRONG_POINTS をAI分類して tags を付与")
    c.add_argument("--in", dest="in_path", required=True, help="入力JSON（build の出力）")
    c.add_argument("--out", dest="out_path", help="出力JSON（既定: 入力を上書き）")
    c.add_argument("--provider", default="anthropic", choices=["anthropic", "openai"],
                   help="AIプロバイダ（既定: anthropic）")
    c.add_argument("--model", default=None, help="使用モデル（既定: プロバイダ標準）")
    c.add_argument("--limit", type=int, default=None, help="先頭N件のみ分類（試行・コスト制御）")
    c.add_argument("--poll-interval", type=float, default=30.0, help="バッチ完了ポーリング間隔（秒）")
    c.add_argument("--dry-run", action="store_true", help="API送信せず対象件数とサンプルだけ表示")

    args = parser.parse_args(argv)
    if args.command == "build":
        return _build(args)
    if args.command == "classify":
        return _classify(args)
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


_KEY_ENV = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}


def _classify(args: argparse.Namespace) -> int:
    import os

    from . import classify

    in_path = Path(args.in_path)
    if not in_path.exists():
        print(f"error: 入力JSONが見つかりません: {in_path}", file=sys.stderr)
        return 2
    records = json.loads(in_path.read_text(encoding="utf-8"))
    model = args.model or classify.DEFAULT_MODELS[args.provider]

    targets = classify.classifiable(records)
    if args.limit is not None:
        targets = targets[: args.limit]
    print(f"分類対象: {len(targets)} 件（全{len(records)}件中、STRONG_POINTS 非空）"
          f", provider={args.provider}, model={model}")

    if args.dry_run:
        if targets:
            preview = classify.request_preview(targets[0], provider=args.provider, model=model)
            print("dry-run: API送信は行いません。サンプルrequest:")
            print(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0

    key_env = _KEY_ENV[args.provider]
    if not os.environ.get(key_env):
        print(f"error: {key_env} が未設定です（--dry-run なら不要）", file=sys.stderr)
        return 2

    clf = classify.make_classifier(args.provider, model=model)
    tags_by_id = clf.classify(targets, poll_interval=args.poll_interval)
    n = classify.apply_tags(records, tags_by_id)
    print(f"タグ付与: {n} 件")

    out_path = Path(args.out_path) if args.out_path else in_path
    out_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"出力先: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
