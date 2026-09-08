# GitLab AI Reviewer

AI-powered automated code reviewer for GitLab Merge Requests, designed primarily for local machines and self-hosted LLMs.

The reviewer periodically checks open GitLab Merge Requests, analyzes changes using a local LLM running through Ollama, validates the generated findings against the actual diff, and posts inline review comments directly to GitLab.

## Features

- Reviews all open Merge Requests from configured GitLab projects
- Skips Draft Merge Requests
- Reviews only added/modified lines
- Uses a self-hosted LLM through Ollama
- Validates LLM-reported file and line numbers against the actual diff
- Posts inline GitLab discussions on problematic lines
- Prevents duplicate comments for the same commit, file and line
- Remembers the last reviewed commit using SQLite
- Supports multiple GitLab projects
- Can run unattended from cron
- Logs every review run to a local log file
- Keeps repository clones locally for efficient subsequent runs

## How it works

For each configured GitLab project:

1. Fetch open Merge Requests.
2. Skip Merge Requests marked as Draft.
3. Check whether the current MR commit was already reviewed.
4. Fetch the MR changes.
5. Split large diffs into reviewable chunks.
6. Send each chunk to the configured LLM.
7. Validate the returned issues against the actual diff.
8. Post valid findings as inline GitLab comments.
9. Save the reviewed commit SHA in SQLite.

A new commit on an existing Merge Request automatically causes that MR to be reviewed again.

## Requirements

- Linux/macOS
- Python 3.12+
- Git
- GitLab account with an API token
- GitLab SSH access for repository cloning
- Ollama
- A code-capable LLM available in Ollama

The project itself only requires:

- `python-gitlab`
- `python-dotenv`
- `httpx`

## Installation

Clone the repository:

```bash
git clone git@github.com:majchrosoft/gitlab-ai-reviewer.git
cd gitlab-ai-reviewer
python3 -m venv .venv
source .venv/bin/activate

Install dependencies:

pip install -r requirements.txt
Configuration

Create .env:

GITLAB_URL=https://gitlab.example.com
GITLAB_TOKEN=YOUR_GITLAB_TOKEN

GITLAB_PROJECTS=https://gitlab.example.com/group/project

OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=your-model
Multiple projects

Projects can be separated with semicolons:

GITLAB_PROJECTS=https://gitlab.example.com/group/project-one;https://gitlab.example.com/group/project-two

Project IDs are not required. Normal GitLab project URLs are used.

GitLab token

The GitLab token needs sufficient permissions to:

read Merge Requests
read repository changes
create Merge Request discussions/comments

The exact permissions depend on the GitLab version and authentication configuration.

Never commit .env or expose the token publicly.

Ollama

Make sure Ollama is running:

ollama list

Pull or install the model you want to use, then configure its name in .env.

Example:

OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=kenevo/DeepSeek-V4-Flash-UD-Q4_K_XL:latest

The reviewer communicates with Ollama using its HTTP API.

Running manually

Activate the environment:

source .venv/bin/activate

Run the reviewer:

python app/main.py

Logs are written to:

logs/reviewer.log

The reviewer also writes logs to stdout.

Running with cron

Example: run every hour:

0 * * * * cd /home/majcher/gitlab-ai-reviewer && /home/majcher/gitlab-ai-reviewer/.venv/bin/python app/main.py >> /home/majcher/gitlab-ai-reviewer/logs/cron.log 2>&1

Using the absolute Python path ensures cron uses the project's virtual environment rather than the system Python.

Local data

The application creates:

data/
    reviewer.db

logs/
    reviewer.log
    cron.log

repos/
    ...

These directories are intentionally excluded from Git.

The SQLite database stores the last reviewed commit for each Merge Request.

Review policy

The LLM is instructed to report only concrete problems introduced by the Merge Request.

It should not report:

existing problems in unchanged code
general code quality issues
formatting
style preferences
refactoring suggestions
theoretical problems without concrete impact

Every finding must reference an added or modified line.

The application performs an additional validation step before posting a finding to GitLab.

Duplicate prevention

Each posted comment contains an internal marker based on:

commit SHA
file
line

This prevents the reviewer from posting the same finding repeatedly when the same commit is processed again.

The reviewer does not perform global semantic deduplication. The same type of problem may therefore be reported independently at multiple locations when appropriate.

Current limitations

The current version intentionally keeps the workflow simple.

Not currently implemented:

replying to existing review comments
automatically resolving discussions
automatically closing Merge Requests
human approval workflows
semantic duplicate detection across different locations
web UI
distributed workers
Project structure
gitlab-ai-reviewer/
├── app/
│   ├── main.py
│   ├── gitlab_client.py
│   ├── git_repo.py
│   ├── state.py
│   ├── llm.py
│   ├── prompts.py
│   ├── chunker.py
│   ├── review_validator.py
│   └── diff_position.py
├── data/
├── logs/
├── repos/
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
License

License information will be added when the project is published.
