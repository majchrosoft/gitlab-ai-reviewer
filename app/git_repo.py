import subprocess
from pathlib import Path


class GitRepository:
    def __init__(self, path, remote_url):
        self.path = Path(path)
        self.remote_url = remote_url

    def ensure_repository(self):
        if (self.path / ".git").exists():
            return

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        subprocess.run(
            [
                "git",
                "clone",
                self.remote_url,
                str(self.path),
            ],
            check=True,
        )

    def fetch(self):
        subprocess.run(
            ["git", "fetch", "--all", "--prune"],
            cwd=self.path,
            check=True,
        )

    def checkout(self, sha):
        subprocess.run(
            [
                "git",
                "checkout",
                "--detach",
                sha,
            ],
            cwd=self.path,
            check=True,
        )

    def current_sha(self):
        result = subprocess.run(
            [
                "git",
                "rev-parse",
                "HEAD",
            ],
            cwd=self.path,
            check=True,
            capture_output=True,
            text=True,
        )

        return result.stdout.strip()
