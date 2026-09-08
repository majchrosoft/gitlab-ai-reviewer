import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from gitlab_client import GitLabClient
from git_repo import GitRepository
from state import State
from llm import LLM
from prompts import review_diff_chunk
from chunker import chunk_changes
from review_validator import validate_issues


def setup_logging(base_dir):
    log_dir = Path(base_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("reviewer")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(
        log_dir / "reviewer.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def review_marker(sha, issue):
    return (
        f"<!-- klickcheck-reviewer:"
        f"{sha}:"
        f"{issue['file']}:"
        f"{issue['line']}"
        f" -->"
    )


def existing_markers(discussions):
    markers = set()

    for discussion in discussions:
        for note in discussion.attributes.get("notes", []):
            body = note.get("body", "")

            start = body.find(
                "<!-- klickcheck-reviewer:"
            )
            end = body.find("-->", start)

            if start >= 0 and end >= 0:
                markers.add(
                    body[start:end + 3].strip()
                )

    return markers


def format_comment(issue, marker):
    severity = issue.get(
        "severity",
        "medium",
    ).upper()

    return f"""{marker}

**{severity}**

{issue["comment"]}

**Reason:** {issue["reason"]}
"""


def review_merge_request(
    gitlab,
    repo,
    state,
    llm,
    project,
    mr,
    logger,
):
    project_name = project.path_with_namespace

    previous_sha = state.get_sha(
        project.id,
        mr.iid,
    )

    logger.info(
        "PROJECT | %s | MR !%s | current_sha=%s | previous_sha=%s",
        project_name,
        mr.iid,
        mr.sha,
        previous_sha or "none",
    )

    if previous_sha == mr.sha:
        logger.info(
            "PROJECT | %s | MR !%s | SKIP | SHA unchanged",
            project_name,
            mr.iid,
        )
        return

    logger.info(
        "PROJECT | %s | MR !%s | CHECKOUT | %s",
        project_name,
        mr.iid,
        mr.sha,
    )

    repo.checkout(mr.sha)

    changes = gitlab.get_changes(
        project,
        mr.iid,
    )

    chunks = chunk_changes(
        changes,
        max_chars=30000,
    )

    logger.info(
        "PROJECT | %s | MR !%s | REVIEW | chunks=%s",
        project_name,
        mr.iid,
        len(chunks),
    )

    discussions = gitlab.get_discussions(
        project,
        mr.iid,
    )

    markers = existing_markers(
        discussions
    )

    all_issues = []

    for chunk in chunks:
        logger.info(
            "PROJECT | %s | MR !%s | CHUNK | %s | %s/%s",
            project_name,
            mr.iid,
            chunk["file"],
            chunk["chunk"],
            chunk["chunks_total"],
        )

        prompt = review_diff_chunk(
            mr,
            chunk,
        )

        try:
            result = llm.review(prompt)
            review = json.loads(result)
        except Exception as exc:
            logger.error(
                "PROJECT | %s | MR !%s | LLM_ERROR | %s | %s",
                project_name,
                mr.iid,
                chunk["file"],
                exc,
            )
            continue

        issues = review.get(
            "issues",
            [],
        )

        valid, rejected = validate_issues(
            issues,
            chunk,
        )

        logger.info(
            "PROJECT | %s | MR !%s | CHUNK_RESULT | %s | valid=%s | rejected=%s",
            project_name,
            mr.iid,
            chunk["file"],
            len(valid),
            len(rejected),
        )

        all_issues.extend(valid)

    if not all_issues:
        logger.info(
            "PROJECT | %s | MR !%s | NO_ISSUES",
            project_name,
            mr.iid,
        )

    posted = 0
    skipped = 0
    failed = 0

    for issue in all_issues:
        marker = review_marker(
            mr.sha,
            issue,
        )

        if marker in markers:
            logger.info(
                "PROJECT | %s | MR !%s | COMMENT_SKIP | %s:%s",
                project_name,
                mr.iid,
                issue["file"],
                issue["line"],
            )

            skipped += 1
            continue

        body = format_comment(
            issue,
            marker,
        )

        try:
            gitlab.create_diff_discussion(
                project=project,
                iid=mr.iid,
                body=body,
                file=issue["file"],
                old_path=issue.get("old_path")
                or issue["file"],
                line=issue["line"],
            )

            markers.add(marker)
            posted += 1

            logger.info(
                "PROJECT | %s | MR !%s | COMMENT_POSTED | %s:%s | severity=%s",
                project_name,
                mr.iid,
                issue["file"],
                issue["line"],
                issue.get(
                    "severity",
                    "medium",
                ),
            )

        except Exception as exc:
            failed += 1

            logger.error(
                "PROJECT | %s | MR !%s | COMMENT_ERROR | %s:%s | %s",
                project_name,
                mr.iid,
                issue["file"],
                issue["line"],
                exc,
            )

    logger.info(
        "PROJECT | %s | MR !%s | FINISHED | issues=%s | posted=%s | skipped=%s | failed=%s",
        project_name,
        mr.iid,
        len(all_issues),
        posted,
        skipped,
        failed,
    )

    if failed == 0:
        state.save_review(
            project.id,
            mr.iid,
            mr.sha,
        )

        logger.info(
            "PROJECT | %s | MR !%s | STATE_SAVED | sha=%s",
            project_name,
            mr.iid,
            mr.sha,
        )
    else:
        logger.warning(
            "PROJECT | %s | MR !%s | STATE_NOT_SAVED",
            project_name,
            mr.iid,
        )


def main():
    load_dotenv()

    base_dir = os.path.dirname(
        os.path.dirname(__file__)
    )

    logger = setup_logging(
        base_dir
    )

    logger.info(
        "========== REVIEW RUN START =========="
    )

    try:
        gitlab = GitLabClient()

        repo_base_dir = Path(
            base_dir
        ) / "repos"

        repo_base_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        state = State(
            os.path.join(
                base_dir,
                "data",
                "reviewer.db",
            )
        )

        llm = LLM()

        for project in gitlab.projects:
            project_name = (
                project.path_with_namespace
            )

            logger.info(
                "PROJECT | %s | START",
                project_name,
            )

            repo_name = (
                project_name
                .replace("/", "__")
            )

            repo_path = (
                repo_base_dir /
                repo_name
            )

            repo = GitRepository(
                repo_path,
                project.ssh_url_to_repo,
            )

            try:
                repo.ensure_repository()
                repo.fetch()

                merge_requests = (
                    gitlab.get_open_merge_requests(
                        project
                    )
                )

                logger.info(
                    "PROJECT | %s | OPEN_MRS | count=%s",
                    project_name,
                    len(merge_requests),
                )

                for mr in merge_requests:
                    if mr.draft:
                        logger.info(
                            "PROJECT | %s | MR !%s | SKIP | Draft",
                            project_name,
                            mr.iid,
                        )
                        continue

                    try:
                        review_merge_request(
                            gitlab,
                            repo,
                            state,
                            llm,
                            project,
                            mr,
                            logger,
                        )
                    except Exception as exc:
                        logger.exception(
                            "PROJECT | %s | MR !%s | FATAL_ERROR | %s",
                            project_name,
                            mr.iid,
                            exc,
                        )

                logger.info(
                    "PROJECT | %s | FINISHED",
                    project_name,
                )

            except Exception as exc:
                logger.exception(
                    "PROJECT | %s | FATAL_ERROR | %s",
                    project_name,
                    exc,
                )

    except Exception as exc:
        logger.exception(
            "RUN | FATAL_ERROR | %s",
            exc,
        )
        raise

    finally:
        logger.info(
            "========== REVIEW RUN END =========="
        )


if __name__ == "__main__":
    main()
