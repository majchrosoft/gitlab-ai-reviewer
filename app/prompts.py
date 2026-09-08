def review_diff_chunk(mr, chunk):
    return f"""
You are reviewing a GitLab Merge Request.

Repository: klickcheck-legacy-backend
Merge Request: !{mr.iid}
Title: {mr.title}

IMPORTANT:
You are NOT reviewing the file.
You are NOT reviewing the existing code in general.
You are reviewing ONLY lines that were ADDED or MODIFIED by this Merge Request.

The diff uses standard unified diff format.

Lines beginning with:
    + 
are NEW/MODIFIED lines and are the ONLY lines that may be reported as issues.

Lines beginning with:
    -
are OLD lines and must NOT be reported.

Lines beginning with a space are unchanged context and must NOT be reported.

A problem in existing unchanged code is NOT a review issue unless the new/modified lines introduced, triggered, or materially changed that problem.

FILE:
{chunk["file"]}

DIFF:
{chunk["diff"]}

Review ONLY the added/modified lines.

Look only for concrete problems introduced by these changed lines:
- bugs
- incorrect behavior
- security problems
- data corruption
- race conditions
- performance problems
- broken contracts
- missing error handling
- production-impacting problems

Do NOT report:
- problems in unchanged code
- problems merely visible in the surrounding context
- file-level observations
- general code quality
- style
- formatting
- refactoring suggestions
- theoretical concerns

Every reported issue MUST point to an actual ADDED/MODIFIED line beginning with '+'.

Return ONLY valid JSON:

{{
  "issues": [
    {{
      "file": "{chunk["file"]}",
      "line": 123,
      "side": "new",
      "severity": "critical",
      "comment": "Short GitLab review comment.",
      "reason": "Explain exactly why the changed line introduces a concrete problem."
    }}
  ]
}}

Rules:
1. "line" MUST be the NEW-file line number from an added line.
2. The referenced line MUST actually begin with '+' in the diff.
3. Never report an unchanged context line.
4. Never report a removed '-' line.
5. Never report a problem with the file as a whole.
6. If no added/modified line contains a concrete problem, return:
   {{"issues":[]}}

Be conservative.
It is better to return no issue than to report a problem that was not introduced by this MR.
"""
