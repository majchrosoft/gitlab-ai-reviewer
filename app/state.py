import sqlite3
from pathlib import Path


class State:
    def __init__(self, db_path):
        Path(db_path).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.db = sqlite3.connect(
            db_path
        )

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS merge_requests (
                project_id INTEGER NOT NULL,
                mr_iid INTEGER NOT NULL,
                last_sha TEXT,
                last_review_at TEXT,
                PRIMARY KEY (project_id, mr_iid)
            )
        """)

        self.db.commit()

    def get_sha(
        self,
        project_id,
        mr_iid,
    ):
        row = self.db.execute(
            """
            SELECT last_sha
            FROM merge_requests
            WHERE project_id = ?
              AND mr_iid = ?
            """,
            (
                project_id,
                mr_iid,
            ),
        ).fetchone()

        return row[0] if row else None

    def save_review(
        self,
        project_id,
        mr_iid,
        sha,
    ):
        self.db.execute(
            """
            INSERT INTO merge_requests
                (
                    project_id,
                    mr_iid,
                    last_sha,
                    last_review_at
                )
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(project_id, mr_iid)
            DO UPDATE SET
                last_sha = excluded.last_sha,
                last_review_at = excluded.last_review_at
            """,
            (
                project_id,
                mr_iid,
                sha,
            ),
        )

        self.db.commit()
