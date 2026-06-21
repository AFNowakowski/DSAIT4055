"""Read Comments_labeled_all_candidates.sql and apply hl_IndicatedDeprecation
to the already-imported Comments table via batch UPDATE."""

from __future__ import annotations

import argparse
import re
import pymysql

ROW_RE = re.compile(
    r"VALUES\s*\((\d+),\s*\d+,\s*\d+,\s*.*?,\s*'[^']*',\s*(?:null|'[^']*'),\s*(?:null|\d+),\s*(\d+)\)",
    re.DOTALL,
)

BATCH = 5_000


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sql", default="C:/Users/migel/Downloads/Comments_labeled_all_candidates.sql")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6767)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default="password")
    parser.add_argument("--database", default="dsait4055db")
    args = parser.parse_args()

    conn = pymysql.connect(
        host=args.host, port=args.port, user=args.user,
        password=args.password, database=args.database,
        charset="utf8mb4", autocommit=False,
    )

    updates: list[tuple[int, int]] = []
    total = 0

    def flush():
        nonlocal total
        if not updates:
            return
        with conn.cursor() as cur:
            cur.executemany(
                "UPDATE Comments SET hl_IndicatedDeprecation = %s WHERE Id = %s",
                [(label, cid) for cid, label in updates],
            )
        conn.commit()
        total += len(updates)
        print(f"  updated {total:,} rows...", end="\r")
        updates.clear()

    with open(args.sql, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = ROW_RE.search(line)
            if not m:
                continue
            comment_id = int(m.group(1))
            label = int(m.group(2))
            updates.append((comment_id, label))
            if len(updates) >= BATCH:
                flush()

    flush()
    conn.close()
    print(f"\nDone. Total rows updated: {total:,}")


if __name__ == "__main__":
    main()
