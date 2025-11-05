import os
import logging
import traceback
import asyncio

from dotenv import load_dotenv

from src.core.run_workflow import run_nemo_agent_workflow

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_ecs_task():
    
    github_link = os.getenv("GITHUB_LINK")
    jira_story = os.getenv("JIRA_STORY")
    jira_story_id = os.getenv("JIRA_STORY_ID")
    is_data_analysis_task = os.getenv("IS_DATA_ANALYSIS_TASK")

    if not all([github_link, jira_story, jira_story_id, is_data_analysis_task]):
        logger.error("Missing required environment variables.")
        logger.info(f"GITHUB_LINK: {github_link}")
        logger.info(f"JIRA_STORY: {jira_story}")
        logger.info(f"JIRA_STORY_ID: {jira_story_id}")
        logger.info(f"IS_DATA_ANALYSIS_TASK: {is_data_analysis_task}")
        exit(1)
    
    try:
        is_data_analysis_task = str(is_data_analysis_task).lower() == "true"
        output = asyncio.run(run_nemo_agent_workflow(github_link=github_link, jira_story=jira_story, jira_story_id=jira_story_id, is_data_analysis_task=is_data_analysis_task))
        logger.info(f"✅ Workflow result: {output}")
        logger.info("✅ ECS Task completed successfully.")
        exit(0)
    except Exception as e:
        logger.error(f"❌ Error during ECS task: {str(e)}")
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    start_ecs_task()