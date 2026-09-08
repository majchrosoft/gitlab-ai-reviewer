import re


HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def split_diff(diff, max_chars=30000):
    """
    Splits a single file diff into chunks without splitting a hunk.
    """

    lines = diff.splitlines()

    header = []
    hunks = []

    current_hunk = None

    for line in lines:
        if line.startswith("@@ "):
            if current_hunk is not None:
                hunks.append(current_hunk)

            current_hunk = [line]
            continue

        if current_hunk is not None:
            current_hunk.append(line)
        else:
            header.append(line)

    if current_hunk is not None:
        hunks.append(current_hunk)

    chunks = []
    current = list(header)

    for hunk in hunks:
        candidate = current + hunk

        if current != header and len("\n".join(candidate)) > max_chars:
            chunks.append("\n".join(current))
            current = list(header) + hunk
            continue

        current = candidate

    if current != header:
        chunks.append("\n".join(current))

    if not chunks:
        return [diff]

    return chunks


def chunk_changes(changes, max_chars=30000):
    """
    Converts GitLab MR changes into independent review chunks.
    """

    result = []

    for change in changes["changes"]:
        path = change["new_path"]

        diff_chunks = split_diff(
            change["diff"],
            max_chars=max_chars,
        )

        for index, diff in enumerate(diff_chunks, start=1):
            result.append(
                {
                    "file": path,
                    "old_path": change.get("old_path"),
                    "chunk": index,
                    "chunks_total": len(diff_chunks),
                    "diff": diff,
                }
            )

    return result
