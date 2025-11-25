import os
import shutil
import subprocess
from urllib.parse import urlparse

from github import Github, Auth
from utils.aws_secrets import get_github_pat_from_secrets_manager

GIHUB_SECRET_ARN = 'arn:aws:secretsmanager:us-east-1:{aws_account_id}:secret:github_personal_access_token-mhV2eN'

class GitHubPRManager:
    def __init__(self, project_name, repo_url, story_id, base_branch="main"):
        self.project_name = project_name
        self.repo_url = repo_url
        self.story_id = story_id
        self.base_branch = base_branch

        self.repo_path = f"/tmp/{self.project_name}"
        self.aws_account_id = os.getenv("AWS_ACCOUNT_ID")
        self.secret_arn = GIHUB_SECRET_ARN.format(aws_account_id=self.aws_account_id)
        self.token = get_github_pat_from_secrets_manager(secret_arn=self.secret_arn)
        auth = Auth.Token(self.token)
        self.github_client = Github(auth=auth)

    def run_cmd(self, cmd, cwd=None):
        print(f"$ {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
        if result.returncode != 0:
            print(f"Command failed: {result} {result.stderr.strip()}")
            raise RuntimeError(f"Command failed: {result} {result.stderr.strip()}")
        return result.stdout.strip()

    def clean_tmp_directory(self):
        if not os.path.exists(self.repo_path):
            print(f"⚠️ Repo path does not exist: {self.repo_path}")
            return

        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file.endswith(".bak"):
                    full_path = os.path.join(root, file)
                    os.remove(full_path)
                    print(f"🧹 Deleted backup file: {full_path}")

    def get_pr_body(self):
        pr_md_file = os.path.join(self.repo_path, f"{self.story_id}.md")
        if os.path.exists(pr_md_file):
            with open(pr_md_file, "r", encoding="utf-8") as f:
                pr_body = f.read().strip()
            os.remove(pr_md_file)
            print(f"🧹 Deleted PR markdown file: {pr_md_file}")
            return pr_body
        return f"This PR was generated automatically for `{self.story_id}`."

    def commit_and_push(self):
        new_branch = f"feature/{self.story_id}"

        self.run_cmd(["git", "config", "user.email", "nemo-ai@example.com"], cwd=self.repo_path)
        self.run_cmd(["git", "config", "user.name", "nemo-ai"], cwd=self.repo_path)

        self.run_cmd(["git", "checkout", "-b", new_branch], cwd=self.repo_path)
        self.run_cmd(["git", "status"], cwd=self.repo_path)
        self.run_cmd(["git", "add", "."], cwd=self.repo_path)
        self.run_cmd(["git", "commit", "-m", f"{self.story_id}: automated changes"], cwd=self.repo_path)

        remote_url_with_token = f"https://{self.token}@{self.repo_url.split('https://')[1]}"
        self.run_cmd(["git", "remote", "set-url", "origin", remote_url_with_token], cwd=self.repo_path)
        self.run_cmd(["git", "push", "-u", "origin", new_branch], cwd=self.repo_path)

        return new_branch

    def create_pr(self, pr_body):
        repo_name = self.repo_url.split("github.com/")[-1].replace(".git", "")
        repo = self.github_client.get_repo(repo_name)
        new_branch = f"feature/{self.story_id}"
        pr_title = f"[{self.story_id}] - Nemo AI"

        pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=new_branch,
            base=self.base_branch,
        )
        print(f"✅ PR created: {pr.html_url}")
        return pr.html_url

    def run_pull_request_workflow(self):
        self.clean_tmp_directory()
        pr_body = self.get_pr_body()
        self.commit_and_push()
        pr_url = self.create_pr(pr_body)
        return {
            "statusCode": 200,
            "body": f"✅ Pull request created: {pr_url}"
        }

class GitHubRepoCloner:
    def __init__(self, repo_url: str, project_name: str, base_branch: str = "main"):
        self.repo_url = repo_url
        self.project_name = project_name
        self.base_branch = base_branch
        self.repo_path = f"/tmp/{self.project_name}"

        self.aws_account_id = os.getenv("AWS_ACCOUNT_ID")
        self.secret_arn = GIHUB_SECRET_ARN.format(aws_account_id=self.aws_account_id)
        self.token = get_github_pat_from_secrets_manager(secret_arn=self.secret_arn)

    def run_cmd(self, cmd, cwd=None):
        print(f"$ {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
        if result.returncode != 0:
            print(f"❌ Command failed: {result.stderr.strip()}")
            raise RuntimeError(f"Command failed: {result.stderr.strip()}")
        return result.stdout.strip()

    def clone_repo(self):
        if os.path.exists(self.repo_path):
            print(f"🧹 Cleaning old repo at {self.repo_path}...")
            shutil.rmtree(self.repo_path)

        remote_url_with_token = f"https://{self.token}@{self.repo_url.split('https://')[1]}"
        self.run_cmd(["git", "clone", remote_url_with_token, self.repo_path])
        self.run_cmd(["git", "checkout", self.base_branch], cwd=self.repo_path)
        self.run_cmd(["git", "pull", "origin", self.base_branch], cwd=self.repo_path)

        print(f"📁 Repo cloned to: {self.repo_path}")
        return self.repo_path

    def validate_repo(self):
        if not os.path.exists(self.repo_path):
            raise FileNotFoundError(f"Cloning failed. Directory {self.repo_path} does not exist.")

        if not any(os.scandir(self.repo_path)):
            raise RuntimeError(f"Repo exists at {self.repo_path}, but it is empty.")

        print(f"✅ Repo at {self.repo_path} exists and contains files.")
        return True

    def run(self):
        self.clone_repo()
        self.validate_repo()

def parse_github_url(github_url: str):
    """
    Given a GitHub web URL (e.g. https://github.com/user/repo), return:
    - the .git clone URL
    - the project name (repo name)

    Returns:
        (clone_url, project_name)
    """
    # Ensure no trailing slash
    github_url = github_url.rstrip("/")

    # Extract project name from path
    parsed = urlparse(github_url)
    path_parts = parsed.path.strip("/").split("/")
    
    if len(path_parts) != 2:
        raise ValueError("Invalid GitHub URL format. Expected: https://github.com/user/repo")

    project_name = path_parts[-1]
    clone_url = f"{github_url}.git" if not github_url.endswith(".git") else github_url

    return clone_url, project_name
