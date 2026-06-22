import argparse
import logging
import os

import pandas as pd
import pymysql

ID_COLUMNS = ["Id", "PostTypeId", "hl_FirstAcceptedAnswerId"]
BOOL_COLUMNS = ["hl_IsStableBucket", "hl_IsEphemeralBucket"]
DATE_COLUMNS = [
    "hl_FirstAcceptedAnswerCreationDate",
    "hl_FirstAcceptedAnswerOvertakeDate",
    "hl_FirstAcceptedAnswerFirstObsoleteCommentDate",
    "hl_FirstAcceptedAnswerDeathDate",
    "hl_FirstAcceptedAnswerFirstVelocityFlipDate",
    "hl_FirstAcceptedAnswerFirstBountyAfterAcceptanceDate",
]

COLUMNS = [
    "Id",
    "PostTypeId",
    "hl_IsStableBucket",
    "hl_IsEphemeralBucket",
    "hl_FirstAcceptedAnswerId",
    "hl_FirstAcceptedAnswerCreationDate",
    "hl_FirstAcceptedAnswerOvertakeDate",
    "hl_FirstAcceptedAnswerFirstObsoleteCommentDate",
    "hl_FirstAcceptedAnswerDeathDate",
    "hl_FirstAcceptedAnswerFirstVelocityFlipDate",
    "hl_FirstAcceptedAnswerFirstBountyAfterAcceptanceDate",
]

QUERY = f"SELECT {', '.join(COLUMNS)} FROM Posts WHERE PostTypeId = 1"

# Resolve paths relative to this file so the script works from any CWD.
HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.normpath(os.path.join(HERE, "..", "..", ".env"))


def load_env(path):
    if not os.path.exists(path):
        raise Exception(f"No .env file at {path}")
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip("'\""))


def parse_args():
    p = argparse.ArgumentParser(description="Export type-1 posts (questions).")
    p.add_argument("--host", default=os.environ.get("MYSQL_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.environ.get("MYSQL_PORT", "6767")))
    p.add_argument("--user", default=os.environ.get("MYSQL_USER", "root"))
    p.add_argument("--password", default=os.environ.get("MYSQL_PASSWORD", ""))
    p.add_argument("--database", default=os.environ.get("MYSQL_DB", "stackoverflow"))
    p.add_argument("--format", choices=["parquet", "csv", "json"], default="parquet")
    p.add_argument(
        "--out",
        default=None,
        help="Output path. Defaults to ./posts_type1.<format> next to this script.",
    )
    return p.parse_args()


def fetch(conn):
    """Run the query and return a typed DataFrame."""
    with conn.cursor() as cur:
        cur.execute(QUERY)
        rows = cur.fetchall()

    df = pd.DataFrame(rows, columns=COLUMNS)

    # Nullable integer ids (hl_FirstAcceptedAnswerId can be NULL).
    for col in ID_COLUMNS:
        df[col] = df[col].astype("Int64")
    # TINYINT(1) 0/1/NULL -> nullable boolean.
    for col in BOOL_COLUMNS:
        df[col] = df[col].astype("boolean")
    # DATETIME -> datetime64 (NaT for NULL).
    for col in DATE_COLUMNS:
        df[col] = pd.to_datetime(df[col])

    return df


def write(df, fmt, out):
    if out is None:
        out = os.path.join(HERE, f"posts_type1.{fmt}")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)

    if fmt == "parquet":
        df.to_parquet(out, index=False)
    elif fmt == "csv":
        # ISO-8601 dates; empty cells for NULL/NaT.
        df.to_csv(out, index=False, date_format="%Y-%m-%dT%H:%M:%S")
    elif fmt == "json":
        # date_format='iso' keeps datetimes readable; records is row-oriented.
        df.to_json(out, orient="records", date_format="iso", indent=2)
    return out


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    load_env(ENV_PATH)
    args = parse_args()

    conn = pymysql.connect(
        host=args.host, port=args.port, user=args.user,
        password=args.password, database=args.database,
        charset="utf8mb4", autocommit=True,
    )
    try:
        logging.info("Querying type-1 posts ...")
        df = fetch(conn)
    finally:
        conn.close()

    out = write(df, args.format, args.out)
    logging.info("Exported %d rows x %d cols -> %s", len(df), len(df.columns), out)


if __name__ == "__main__":
    main()
