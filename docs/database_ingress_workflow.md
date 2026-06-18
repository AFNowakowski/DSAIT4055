# Database Ingress Workflow

## Required dump files

The ingress requires these four Stack Overflow XML files in one directory:

- `Tags.xml`
- `Posts.xml`
- `Comments.xml`
- `Votes.xml`

`Comments.sql` alone is not enough for ingress because comments reference
answers, and answers reference questions and tags.

## Start MySQL

From the repository root:

```bash
docker compose -f src/compose.yml up -d
docker compose -f src/compose.yml ps
```

On a new Docker volume, MySQL automatically executes
`src/db/schema.sql`. Wait until the service reports `healthy`.

The schema initialization scripts run only when the MySQL data volume is empty.
For an existing volume, inspect the tables with:

```bash
docker compose -f src/compose.yml exec mysql \
  mysql -udsait4055dbuser '-pdsait4055dbuserPA55?1' \
  -P 6767 -e "USE dsait4055db; SHOW TABLES;"
```

If the database exists but has no tables, apply the schema manually:

```bash
docker compose -f src/compose.yml exec -T mysql \
  mysql -uroot -psomehardROOTPASSWD21 -P 6767 dsait4055db \
  < src/db/schema.sql
```

## Run ingress

Install dependencies:

```bash
venv/bin/pip install -r requirements.txt
```

Then provide the directory containing the four XML files:

```bash
venv/bin/python src/dump-ingress/load.py \
  --data-dir /absolute/path/to/stackoverflow-dump
```

The script loads:

1. selected stable and ephemeral tags
2. matching questions
3. answers belonging to those questions
4. comments belonging to those answers
5. accepted, upvote, downvote, and bounty vote events

Do not rerun ingress against a populated database: inserts use primary keys and
are not currently resume-safe. For a clean reload, explicitly remove the
project volume and start again:

```bash
docker compose -f src/compose.yml down
docker volume rm src_mysql_data
docker compose -f src/compose.yml up -d
```

Removing the volume permanently deletes the local database.

## Verify the loaded data

```bash
docker compose -f src/compose.yml exec mysql \
  mysql -udsait4055dbuser '-pdsait4055dbuserPA55?1' -P 6767 \
  -e "USE dsait4055db;
      SELECT COUNT(*) AS posts FROM Posts;
      SELECT COUNT(*) AS comments FROM Comments;
      SELECT COUNT(*) AS unclassified
      FROM Comments
      WHERE hl_IndicatedDeprecation IS NULL;"
```

After this succeeds, continue with `docs/comment_nlp_workflow.md`.
