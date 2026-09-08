import re


HUNK_RE = re.compile(
    r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@"
)


def get_added_lines(diff):
    """
    Returns:
        new_file_line_number -> added line content
    """

    added_lines = {}

    current_line = None

    for line in diff.splitlines():
        match = HUNK_RE.match(line)

        if match:
            current_line = int(match.group(1))
            continue

        if current_line is None:
            continue

        if line.startswith("+") and not line.startswith("+++"):
            added_lines[current_line] = line[1:]
            current_line += 1
            continue

        if line.startswith("-") and not line.startswith("---"):
            continue

        current_line += 1

    return added_lines


def validate_issues(issues, chunk):
    added_lines = get_added_lines(chunk["diff"])

    valid = []
    rejected = []

    for issue in issues:
        file = issue.get("file")
        line = issue.get("line")

        if file != chunk["file"]:
            rejected.append(
                {
                    "issue": issue,
                    "reason": "Wrong file.",
                }
            )
            continue

        if line not in added_lines:
            rejected.append(
                {
                    "issue": issue,
                    "reason": "Line is not an added line.",
                }
            )
            continue

        valid.append(issue)

    return valid, rejected
