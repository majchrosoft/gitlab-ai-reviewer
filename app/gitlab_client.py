import os
from urllib.parse import urlparse

import gitlab


class GitLabClient:
    def __init__(self):
        self.client = gitlab.Gitlab(
            os.environ["GITLAB_URL"],
            private_token=os.environ["GITLAB_TOKEN"],
        )

        self.client.auth()

        self.projects = []

        for project_url in os.environ["GITLAB_PROJECTS"].split(";"):
            project_url = project_url.strip()

            if not project_url:
                continue

            project = self._get_project(project_url)

            self.projects.append(project)

    def _get_project(self, project_url):
        parsed = urlparse(project_url)

        if not parsed.path:
            raise ValueError(
                f"Invalid GitLab project URL: {project_url}"
            )

        project_path = parsed.path.strip("/")

        if project_path.endswith(".git"):
            project_path = project_path[:-4]

        return self.client.projects.get(
            project_path
        )

    def get_open_merge_requests(self, project):
        return project.mergerequests.list(
            state="opened",
            get_all=True,
        )

    def get_merge_request(self, project, iid):
        return project.mergerequests.get(iid)

    def get_discussions(self, project, iid):
        mr = self.get_merge_request(
            project,
            iid,
        )

        return mr.discussions.list(
            get_all=True,
        )

    def get_changes(self, project, iid):
        mr = self.get_merge_request(
            project,
            iid,
        )

        return mr.changes()

    def create_diff_discussion(
        self,
        project,
        iid,
        body,
        file,
        old_path,
        line,
    ):
        mr = self.get_merge_request(
            project,
            iid,
        )

        diff_refs = mr.diff_refs

        position = {
            "base_sha": diff_refs["base_sha"],
            "start_sha": diff_refs["start_sha"],
            "head_sha": diff_refs["head_sha"],
            "position_type": "text",
            "new_path": file,
            "old_path": old_path or file,
            "new_line": line,
        }

        return mr.discussions.create(
            {
                "body": body,
                "position": position,
            }
        )
