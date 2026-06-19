import argparse
import logging
import os
import re
import sys

import pymysql
from lxml import etree

# case sensitive!
EPHEMERAL_TAGS = [
    "node.js",
    "npm",
    "angularjs",
    "reactjs",
    "webpack",
    "vue.js",
    "react-native",
    "flutter",
    "angular",
    "rust"
]

STABLE_TAGS = [
    "c",
    "regex",
    "sql",
    "sorting",
    "algorithm",
    "math",
    "bash",
    "recursion",
    "dynamic-programming",
    "data-structures"
]

BUCKET_QUOTA = 100_000

SELECTED_TAGS = EPHEMERAL_TAGS + STABLE_TAGS

# Vote types to keep: 1=AcceptedByOriginator 2=UpMod 3=DownMod 8=BountyStart
ALLOWED_VOTE_TYPES = {"1", "2", "3", "8"}

BATCH_POSTS = 1_000
BATCH_COMMENTS = 5_000
BATCH_SMALL = 20_000

LOG_EVERY = 500_000

_TAG_RE = re.compile(r"<([^<>]+)>")


def parse_tags(tags_attr):
    """'<a><b>' -> ['a', 'b'] ; also tolerates the newer 'a|b' format."""
    if not tags_attr:
        return []
    if tags_attr.startswith("<"):
        return _TAG_RE.findall(tags_attr)
    return [t for t in tags_attr.split("|") if t]


def to_int(value):
    return int(value) if value not in (None, "") else None


def parse_dt(value):
    """'2008-08-10T18:11:08.100' -> '2008-08-10 18:11:08' (DATETIME, no frac)."""
    if not value:
        return None
    date_part, _, time_part = value.partition("T")
    if not time_part:
        return date_part
    return f"{date_part} {time_part.split('.', 1)[0]}"


def trunc(value, n):
    """Defensively clip strings to their column width (chars, utf8mb4-safe)."""
    if value is None:
        return None
    return value[:n]


def iter_rows(path):
    """Yield each <row> element, then free memory"""
    context = etree.iterparse(
        path, events=("end",), tag="row", recover=True, huge_tree=True
    )
    for _, elem in context:
        yield elem
        elem.clear()
        parent = elem.getparent()
        if parent is not None:
            while elem.getprevious() is not None:
                del parent[0]
    del context


def post_row(elem):
    g = elem.get
    return (
        int(g("Id")),
        to_int(g("PostTypeId")),
        to_int(g("AcceptedAnswerId")),
        to_int(g("ParentId")),
        parse_dt(g("CreationDate")),
        parse_dt(g("DeletionDate")),
        to_int(g("Score")) or 0,
        to_int(g("ViewCount")),
        g("Body"),
        to_int(g("OwnerUserId")),
        trunc(g("OwnerDisplayName"), 40),
        to_int(g("LastEditorUserId")),
        trunc(g("LastEditorDisplayName"), 40),
        parse_dt(g("LastEditDate")),
        parse_dt(g("LastActivityDate")),
        trunc(g("Title"), 250),
        trunc(g("Tags"), 500),
        to_int(g("AnswerCount")),
        to_int(g("CommentCount")),
        to_int(g("FavoriteCount")),
        parse_dt(g("ClosedDate")),
        parse_dt(g("CommunityOwnedDate")),
    )


POSTS_SQL = (
    "INSERT INTO Posts (Id, PostTypeId, AcceptedAnswerId, ParentId, CreationDate, "
    "DeletionDate, Score, ViewCount, Body, OwnerUserId, OwnerDisplayName, "
    "LastEditorUserId, LastEditorDisplayName, LastEditDate, LastActivityDate, "
    "Title, Tags, AnswerCount, CommentCount, FavoriteCount, ClosedDate, "
    "CommunityOwnedDate) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,"
    "%s,%s,%s,%s,%s,%s,%s)"
)
TAGS_SQL = (
    "INSERT INTO Tags (Id, TagName, Count, ExcerptPostId, WikiPostId) "
    "VALUES (%s,%s,%s,%s,%s)"
)
POSTTAGS_SQL = "INSERT INTO PostTags (PostId, TagId) VALUES (%s,%s)"
COMMENTS_SQL = (
    "INSERT INTO Comments (Id, PostId, Score, Text, CreationDate, "
    "UserDisplayName, UserId) VALUES (%s,%s,%s,%s,%s,%s,%s)"
)
VOTES_SQL = (
    "INSERT INTO Votes (Id, PostId, VoteTypeId, UserId, CreationDate, "
    "BountyAmount) VALUES (%s,%s,%s,%s,%s,%s)"
)


class BatchInserter:
    def __init__(self, conn, sql, batch_size, label):
        self.conn = conn
        self.sql = sql
        self.batch_size = batch_size
        self.label = label
        self.rows = []
        self.total = 0

    def add(self, row):
        self.rows.append(row)
        if len(self.rows) >= self.batch_size:
            self.flush()

    def flush(self):
        if not self.rows:
            return
        with self.conn.cursor() as cur:
            cur.executemany(self.sql, self.rows)
        self.conn.commit()
        self.total += len(self.rows)
        self.rows.clear()


def load_tags(conn, path):
    """Insert only the selected tags; return {lower(name): tag_id}."""
    name_to_id = {}
    ins = BatchInserter(conn, TAGS_SQL, BATCH_SMALL, "tags")
    for elem in iter_rows(path):
        name = elem.get("TagName")
        if name is None or name.lower() not in SELECTED_TAGS:
            continue
        tid = int(elem.get("Id"))
        name_to_id[name.lower()] = tid
        ins.add((
            tid,
            trunc(name, 35),
            to_int(elem.get("Count")) or 0,
            to_int(elem.get("ExcerptPostId")),
            to_int(elem.get("WikiPostId")),
        ))
    ins.flush()
    logging.info("Tags inserted: %d", ins.total)
    return name_to_id


def load_questions(conn, path, tag_id_by_name):
    """Type-1, not deleted, >=1 selected tag. Returns set of inserted IDs."""
    posts = BatchInserter(conn, POSTS_SQL, BATCH_POSTS, "questions")
    ptags = BatchInserter(conn, POSTTAGS_SQL, BATCH_SMALL, "posttags")
    ephemeral_count = 0
    stable_count = 0
    ids = set()
    scanned = 0
    for elem in iter_rows(path):
        if (ephemeral_count >= BUCKET_QUOTA) and (stable_count >= BUCKET_QUOTA):
            break
        scanned += 1
        if scanned % LOG_EVERY == 0:
            logging.info("  ...scanned %d posts, bucket counts: %d;%d (questions pass)", scanned, ephemeral_count,
                         stable_count)
        if elem.get("PostTypeId") != "1":
            continue
        if elem.get("DeletionDate") is not None:  # require DeletionDate == null
            continue
        created = elem.get("CreationDate")
        if created is None or created < "2015-01-01":  # questions from 2015-01-01 on
            continue
        tags = parse_tags(elem.get("Tags"))
        matched = [t for t in tags if t.lower() in SELECTED_TAGS]
        if not matched:
            continue
        is_ephemeral = [t for t in tags if t.lower() in EPHEMERAL_TAGS]
        is_stable = [t for t in tags if t.lower() in STABLE_TAGS]

        if is_ephemeral:
            if ephemeral_count >= BUCKET_QUOTA:
                continue

        if is_stable:
            if stable_count >= BUCKET_QUOTA:
                continue

        if is_ephemeral:
            ephemeral_count += 1
        if is_stable:
            stable_count += 1

        pid = int(elem.get("Id"))
        posts.add(post_row(elem))
        ids.add(pid)
        for t in matched:
            ptags.add((pid, tag_id_by_name[t.lower()]))
    posts.flush()
    ptags.flush()
    logging.info("Questions inserted: %d | PostTags inserted: %d",
                 posts.total, ptags.total)
    return ids


def load_answers(conn, path, post_ids):
    """Type-2 whose ParentId is an already-loaded question. Grows post_ids."""
    posts = BatchInserter(conn, POSTS_SQL, BATCH_POSTS, "answers")
    scanned = 0
    ids = set()
    for elem in iter_rows(path):
        scanned += 1
        if scanned % LOG_EVERY == 0:
            logging.info("  ...scanned %d posts (answers pass)", scanned)
        if elem.get("PostTypeId") != "2":
            continue
        parent = to_int(elem.get("ParentId"))
        if parent is None or parent not in post_ids:
            continue
        posts.add(post_row(elem))
        ids.add(int(elem.get("Id")))
    posts.flush()
    logging.info("Answers inserted: %d", posts.total)
    return ids


def load_comments(conn, path, answer_ids):
    ins = BatchInserter(conn, COMMENTS_SQL, BATCH_COMMENTS, "comments")
    scanned = 0
    for elem in iter_rows(path):
        scanned += 1
        if scanned % LOG_EVERY == 0:
            logging.info("  ...scanned %d comments", scanned)
        pid = to_int(elem.get("PostId"))
        if pid is None or pid not in answer_ids:
            continue
        ins.add((
            int(elem.get("Id")),
            pid,
            to_int(elem.get("Score")) or 0,
            elem.get("Text"),
            parse_dt(elem.get("CreationDate")),
            trunc(elem.get("UserDisplayName"), 30),
            to_int(elem.get("UserId")),
        ))
    ins.flush()
    logging.info("Comments inserted: %d", ins.total)


def load_votes(conn, path, post_ids, answer_ids):
    ins = BatchInserter(conn, VOTES_SQL, BATCH_SMALL, "votes")
    scanned = 0
    for elem in iter_rows(path):
        scanned += 1
        if scanned % LOG_EVERY == 0:
            logging.info("  ...scanned %d votes", scanned)
        vt = elem.get("VoteTypeId")
        if vt not in ALLOWED_VOTE_TYPES:
            continue
        pid = to_int(elem.get("PostId"))
        if pid is None or ((pid not in post_ids) and pid not in answer_ids):
            continue
        if vt == "8" and pid not in post_ids:
            continue
        if vt in {"1", "2", "3"} and pid not in answer_ids:
            continue
        ins.add((
            int(elem.get("Id")),
            pid,
            int(vt),
            to_int(elem.get("UserId")),
            parse_dt(elem.get("CreationDate")),
            to_int(elem.get("BountyAmount")),
        ))
    ins.flush()
    logging.info("Votes inserted: %d", ins.total)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
#
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", default=os.environ.get("DUMP_DIR", "/"))

    p.add_argument("--host", default=os.environ.get("MYSQL_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.environ.get("MYSQL_PORT", "6767")))
    p.add_argument("--user", default=os.environ.get("MYSQL_USER", "root"))
    p.add_argument("--password", default=os.environ.get("MYSQL_PASSWORD", ""))
    p.add_argument("--database", default=os.environ.get("MYSQL_DB", "stackoverflow"))
    return p.parse_args()


if not os.path.exists('../../.env'):
    raise Exception("No .env file")
with open('../../.env', encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip("'\""))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)
args = parse_args()

tags_path = os.path.join(args.data_dir, "Tags.xml")
posts_path = os.path.join(args.data_dir, "Posts.xml")
comments_path = os.path.join(args.data_dir, "Comments.xml")
votes_path = os.path.join(args.data_dir, "Votes.xml")

for label, path in [("Tags", tags_path), ("Posts", posts_path),
                    ("Comments", comments_path), ("Votes", votes_path)]:
    if not os.path.exists(path):
        sys.exit(f"{label}.xml not found at: {path}")

conn = pymysql.connect(
    host=args.host, port=args.port, user=args.user,
    password=args.password, database=args.database,
    charset="utf8mb4", autocommit=False,
)

try:
    with conn.cursor() as cur:
        cur.execute("SET SESSION foreign_key_checks = 0")
        cur.execute("SET SESSION unique_checks = 0")
        cur.execute("SET SESSION sql_mode = ''")  # lenient; we also clip strings
    conn.commit()

    logging.info("== Step 1, 2: tags ==")
    tag_id_by_name = load_tags(conn, tags_path)
    if not tag_id_by_name:
        sys.exit("None of the SELECTED_TAGS were found in Tags.xml; aborting.")

    logging.info("== Step 3, 4: questions + posttags ==")
    post_ids = load_questions(conn, posts_path, tag_id_by_name)

    logging.info("== Step 5: answers ==")
    answer_ids = load_answers(conn, posts_path, post_ids)

    logging.info("== Step 6: comments ==")
    load_comments(conn, comments_path, answer_ids)

    logging.info("== Step 7: votes ==")
    load_votes(conn, votes_path, post_ids, answer_ids)  # todo

    with conn.cursor() as cur:
        cur.execute("SET SESSION foreign_key_checks = 1")
        cur.execute("SET SESSION unique_checks = 1")
    conn.commit()
    logging.info("Done. Total posts loaded: %d", len(post_ids))
finally:
    conn.close()
