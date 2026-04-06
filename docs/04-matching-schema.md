# 04. 登録×成約 突合スキーマ（成約フラグ生成）

登録物件（募集中）と成約物件を1つの正規化データセットに統合する方針。

## 前提（実測）

[01](01-data-source-notes.md) §3 の通り:

- 成約 1,203 件の `ID` のうち、登録 `PROPERTY_NUMBER_ID` に**一致したのは 271 件のみ**。
- 残り **932 件は登録ファイルに存在しない**（成約後に登録一覧から削除されたと解釈）。
- → 「登録レコードに成約フラグを立てる」だけでは 932 件を取りこぼす。

両ファイルは**同一ID空間**（`9000xxx`）を共有しているため、`id` で突合できる。

## 統合方針: 和集合（union）＋ status

```
登録(7,746) ─┐
             ├─ id で突合 ─→ 統一データセット
成約(1,203) ─┘
```

`id` をキーに以下の3集合に分類する。

| 集合 | 件数（実測） | `source` | `status` | レコードの作り方 |
| --- | --- | --- | --- | --- |
| 登録のみ（成約に無い） | 7,475 | `registered` | `registered` | 登録行から正規化 |
| 登録∩成約（両方にある） | 271 | `registered` | `closed` | **登録行を基にし、成約の `contract` 情報を付与** |
| 成約のみ（登録に無い） | 932 | `closed` | `closed` | 成約行から正規化 |

- 統一データセットの想定総数 ≒ **8,678 件**（7,746 ＋ 932）。
- `status` が成約フラグそのもの（`closed` = 成約済）。

### なぜ登録∩成約は「登録行ベース」か
登録行のほうが列が充実し、募集時点の正規化済み属性が揃っているため。成約側からは
`contract`（成約日・成約額）だけを取り込む。物件属性は登録を正とする。

### 同一IDが両ファイルにあるときの属性衝突
- 物件属性（面積・構造・PR文等）は**登録を優先**。
- 成約固有情報（`contract`）は**成約から取得**。
- 競合した場合の差異は `provenance` 配下に記録する余地を残す（将来拡張、必須ではない）。

## `contract` オブジェクト

`status=closed` のレコードにのみ付与。`registered` では `null`。

```jsonc
"contract": {
  "is_closed": true,
  "date": "2025-02-25",       // CONTRACT_INFO_DATE を ISO 8601 化。欠損 86.9% → null 多
  "date_raw": "02/25/25",     // 原文（MM/DD/YY）
  "amount_yen": 2000000,      // CONTRACT_INFO_AMOUNT/RENT。欠損 92.2% → null 多
  "amount_raw": "2000000"
}
```

### フィールド規約
- `is_closed`: `status=closed` なら常に true。フラグの単一情報源。
- `date`: `MM/DD/YY` を `20YY-MM-DD` に変換（[01](01-data-source-notes.md) §2.5）。パース不能/欠損→null。
  年は2桁→`2000+YY`（データセットが2025年度なので妥当）。
- `amount_yen`: 円・整数。`0`/欠損→null。
- **欠損は補完しない。** 成約日・成約額は大半が欠損である前提で利用すること。

## 突合アルゴリズム（擬似コード）

```
closed_by_id = { row.ID: row for row in seiyaku }      # 成約をIDで索引
out = []

for row in toroku:                                     # 登録を主軸に走査
    rec = normalize_registered(row)                    # [02] に従い正規化
    if rec.id in closed_by_id:
        rec.status = "closed"
        rec.contract = build_contract(closed_by_id[rec.id])
    else:
        rec.status = "registered"
        rec.contract = null
    out.append(rec)

toroku_ids = { row.PROPERTY_NUMBER_ID for row in toroku }
for row in seiyaku:                                    # 登録に無い成約のみ追加
    if row.ID not in toroku_ids:
        rec = normalize_closed(row)                    # [02] に従い正規化
        rec.status = "closed"
        rec.source = "closed"
        rec.contract = build_contract(row)
        out.append(rec)
```

### 重複・整合チェック（実装時の検証項目）
- `id` のユニーク性（統合後に重複IDが無いこと）。
- `status=closed` の件数 = `contract.is_closed=true` の件数 = 1,203（成約総数）であること。
- `status=closed` かつ `source=registered` の件数 = 271 であること。
- 成約のみ由来（`source=closed`）の件数 = 932 であること。

これらは年次更新時の回帰テストにも使う（[05](05-diff-management.md)）。
