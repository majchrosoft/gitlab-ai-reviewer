import re


HUNK_RE = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@"
)


def get_new_line_positions(diff):
    """
    Returns:
        new_file_line -> diff position information
    """

    positions = {}

    old_line = None
    new_line = None

    for raw_line in diff.splitlines():
        match = HUNK_RE.match(raw_line)

        if match:
            old_line = int(match.group(1))
            new_line = int(match.group(3))
            continue

        if old_line is None or new_line is None:
            continue

        if raw_line.startswith("\\"):
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            positions[new_line] = {
                "new_line": new_line,
                "old_line": None,
                "line_type": "added",
            }

            new_line += 1
            continue

        if raw_line.startswith("-") and not raw_line.startswith("---"):
            old_line += 1
            continue

        positions[new_line] = {
            "new_line": new_line,
            "old_line": old_line,
            "line_type": "context",
        }

        old_line += 1
        new_line += 1

    return positions
