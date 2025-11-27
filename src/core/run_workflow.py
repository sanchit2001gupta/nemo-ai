import logging

from src.core.workflow import nemo_workflow
from src.core.data_analyst_workflow import data_analyst_workflow
from src.utils.github_utils import GitHubRepoCloner, GitHubPRManager, parse_github_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_nemo_agent_workflow(github_link: str, jira_story: str, jira_story_id: str, is_data_analysis_task: bool) -> dict:
    """Runs the Agentic Workflow."""
    # Extract repo details
    clone_url, project_name = parse_github_url(github_link)

    # Clone repo
    clone_repo = GitHubRepoCloner(repo_url=clone_url, project_name=project_name)
    clone_repo.run()

    # Run AI workflow
    if is_data_analysis_task:
        logger.info("Running data analyst workflow.")
        result = await data_analyst_workflow(
            project_name=project_name,
            jira_story=jira_story,
            jira_story_id=jira_story_id
        )
    else:
        logger.info("Running nemo workflow.")
        result = await nemo_workflow(
            project_name=project_name,
            jira_story=jira_story,
            jira_story_id=jira_story_id
        )

    # Create PR
    github_manager = GitHubPRManager(
        project_name=project_name,
        repo_url=clone_url,
        story_id=jira_story_id
    )
    pr_status = github_manager.run_pull_request_workflow()
    return {
        "result": result,
        "pr_status": pr_status
    }
