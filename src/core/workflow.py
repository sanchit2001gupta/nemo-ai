import os
import re
import json
import logging
import time
import asyncio
import traceback
import subprocess
from typing import Any, Dict, List

import httpcore
import httpx
import boto3
from botocore.config import Config
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from strands import Agent, tool
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

# from ast_reader import MemoryCodeIndex
from custom_tools import editor, file_read, file_write, shell
from src.utils.change_manifest import get_manifest, format_manifest_code_diffs
from prompt.agent_prompt import (
    planner_prompt,
    senior_engineer_prompt,
    code_reviewer_prompt,
    low_system_design_engineer_prompt, 
    coding_standard_prompt,
    data_structure_algorithms_agent_prompt,
    story_scoring_prompt,
    doc_prompt,
)

# Set the environment variable
os.environ["LOG_LEVEL"] = "INFO"  # or "INFO", "WARNING", "ERROR"

logging.getLogger("strands").setLevel(logging.INFO)

# Configure Python logging
# logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# os.environ["STRANDS_TOOL_CONSOLE_MODE"] = "enabled"
# os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-e0ca3f41-8e1d-4b3d-846b-719acbb9d9a1"
# os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-60b49300-6821-4af9-80ec-44bb99b6ace0"
# os.environ["LANGFUSE_HOST"] = "http://192.168.29.166:3000"


# LANGFUSE_AUTH = base64.b64encode(
#     f"{os.environ.get('LANGFUSE_PUBLIC_KEY')}:{os.environ.get('LANGFUSE_SECRET_KEY')}".encode()
# ).decode()
# print(f"==>> LANGFUSE_AUTH: {LANGFUSE_AUTH}")

# os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = os.environ.get("LANGFUSE_HOST") + "/api/public/otel"
# os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {LANGFUSE_AUTH}"

os.environ['BYPASS_TOOL_CONSENT'] = 'True'

# strands_telemetry = StrandsTelemetry()
# strands_telemetry.setup_otlp_exporter()     # Send traces to OTLP endpoint

retry_config = Config(
    retries={
        'max_attempts': 5,
        'mode': 'standard'  # or 'adaptive'
    },
    read_timeout=180
)

session = boto3.Session()

claude_sonnet_4 = BedrockModel(
    model_id='us.anthropic.claude-sonnet-4-20250514-v1:0',
    boto_session=session,
    boto_client_config=retry_config
)

bedrock_nova_pro_model = BedrockModel(
    model_id='us.amazon.nova-pro-v1:0',
    boto_session=session,
    boto_client_config=retry_config
)

# ast_index = MemoryCodeIndex(s3_bucket='nemo-ai-ast-bucket', s3_key='asts/finance_service_agent.json')

def filter_files(directory: str, allowed_extensions: List[str] = ['.py', '.md', '.json', '.txt', '.yml', '.yaml']) -> str:
    """Return JSON string of file paths excluding .bak and irrelevant files."""
    files = []
    exclude_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env'}
    
    for root, dirs, filenames in os.walk(directory):
        # Remove excluded directories from traversal
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for filename in filenames:
            if any(filename.endswith(ext) for ext in allowed_extensions) and not filename.endswith('.bak'):
                files.append(os.path.join(root, filename))
    
    file_context = {"files": files, "total_files": len(files)}
    print(f"Filtered {len(files)} files from {directory}")
    return json.dumps(file_context, indent=2)

def extract_manifest_from_output(output: str) -> Dict:
    """Extract the change manifest JSON from the senior agent's output."""
    # Look for the prefixed JSON block
    match = re.search(r'```json\s*(\{.*?\})\s*```', output, re.DOTALL | re.IGNORECASE)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            print("Failed to parse manifest JSON.")
            return {}
    print("No manifest found in output.")
    return {}

@tool
def lint_check(changes_manifest: dict) -> dict:
    """
    Run linting checks (pylint and mypy) on only the Python files that were modified
    according to the provided `changes_json`.

    For each `.py` file in the manifest:
    - Runs `pylint --errors-only`
    - Runs `mypy`

    Returns:
      A dictionary mapping each Python file to its linting results, including:
        - return code (0 = success, nonzero = errors)
        - stdout (error messages / warnings)
    """

    try:
        py_files = {
            change["file_path"]
            for change in changes_manifest.get("changes", [])
            if change["file_path"].endswith(".py")
        }
        print("lint_check py_files", py_files)

        results: Dict[str, Any] = {"lint_results": {}}

        for f in py_files:
            results["lint_results"][f] = {}

            # Run pylint
            pylint_res = subprocess.run(
                ["pylint", "--errors-only", f],
                capture_output=True, text=True
            )
            results["lint_results"][f]["pylint"] = {
                "returncode": pylint_res.returncode,
                "stdout": pylint_res.stdout.strip(),
            }

            # Run mypy
            mypy_res = subprocess.run(
                ["mypy", f],
                capture_output=True, text=True
            )
            results["lint_results"][f]["mypy"] = {
                "returncode": mypy_res.returncode,
                "stdout": mypy_res.stdout.strip(),
            }

        return results
    except Exception as e:
        return f"Error in lint_check: {e}"

# file_context = filter_files('/tmp/finance_service_agent')
# planner_prompt = planner_prompt.format(project_name=project_name, file_context=file_context)

# planner_agent = Agent(
#     name='planner_engineer',
#     model=claude_sonnet_4,
#     system_prompt=planner_prompt,
#     tools=[
#         # query_vector_store,
#         ast_index.query_class,
#         ast_index.query_function,
#         editor,
#         file_read,
#         shell_agent
#     ],
#     callback_handler=None
# )

# senior_agent = Agent(
#     name='senior_software_engineer',
#     model=claude_sonnet_4,
#     system_prompt=senior_engineer_prompt,
#     tools=[
#         query_vector_store,
#         ast_index.query_class,
#         ast_index.query_function,
#         editor,
#         file_read,
#         file_write,
#         shell_agent,
#         *context7_tools
#     ],
#     callback_handler=None
# )

# Initialize single code reviewer agent (combines all review aspects)
code_reviewer_agent = Agent(
    name='code_reviewer',
    model=claude_sonnet_4,  # Use Claude for better code review
    system_prompt=code_reviewer_prompt,
    tools=[file_read, shell],
    callback_handler=None
)

# security_agent = Agent(
#     name='security_engineer',
#     model=bedrock_nova_pro_model,
#     system_prompt=security_engineer_prompt,
#     tools=[file_read, shell_agent],
#     callback_handler=None
# )

coding_standard_agent = Agent(
    name='coding_standard_engineer',
    model=bedrock_nova_pro_model,
    system_prompt=coding_standard_prompt,
    tools=[file_read, shell],
    callback_handler=None
)

low_system_design_agent = Agent(
    name='low_system_design_engineer',
    model=bedrock_nova_pro_model,
    system_prompt=low_system_design_engineer_prompt,
    tools=[file_read, shell],
    callback_handler=None
)

data_structure_algorithms_agent = Agent(
    name='data_structure_algorithms_agent',
    model=bedrock_nova_pro_model,
    system_prompt=data_structure_algorithms_agent_prompt,
    tools=[file_read, shell],
    callback_handler=None
)

story_scoring_agent = Agent(
    name='story_scoring_agent',
    model=bedrock_nova_pro_model,
    system_prompt=story_scoring_prompt,
    tools=[file_read, shell],
    callback_handler=None
)

review_agents = {
    # 'security_agent': security_agent,
    'coding_standard_agent': coding_standard_agent,
    'low_system_design_agent': low_system_design_agent,
    # 'library_compatibility_agent': library_compatibility_agent,
    'data_structure_algorithms_agent': data_structure_algorithms_agent,   
}

@retry(
    stop=stop_after_attempt(1),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.ReadTimeout, httpcore.ReadTimeout, Exception)),
    before_sleep=lambda retry_state: print(f"Retrying workflow, attempt {retry_state.attempt_number}...")
)
async def nemo_workflow(project_name: str, jira_story: str, jira_story_id: str) -> str:
    """Entry point for the Nemo AI workflow."""

    print("Initializing Context7 MCP client...")
    context7_mcp = MCPClient(lambda: streamablehttp_client("https://mcp.context7.com/mcp"))
    aws_documentation_mcp = MCPClient(lambda: streamablehttp_client("https://knowledge-mcp.global.api.aws"))

    try:
        with context7_mcp, aws_documentation_mcp:
            print("✅ Context7 client connected successfully")
            print("✅ AWS Documentation MCP client connected successfully")

            try:
                context7_tools = context7_mcp.list_tools_sync()
                aws_documentation_tools = aws_documentation_mcp.list_tools_sync()
                print(f"✅ AWS Documentation MCP {len(aws_documentation_tools)} tools available")
                print(f"✅ Context7 MCP {len(context7_tools)} tools available")
            except Exception as e:
                print(f"❌ Failed to load AWS Documentation MCP or Context7 MCP tools: {e}")
                raise  

            print("Step 1: Planning phase")
            repo_path = f'/tmp/{project_name}'
            file_context = filter_files(repo_path)
            
            planner_agent = Agent(
                name='planner_engineer',
                model=claude_sonnet_4,
                system_prompt=planner_prompt.format(project_name=project_name, file_context=file_context),
                tools=[file_read, shell, *aws_documentation_tools],
                callback_handler=None
            )
            plan = str(planner_agent(jira_story))
            print(f"Plan created:\\n{plan}")

            print("Step 2: Implementation phase")
            senior_agent = Agent(
                name='senior_software_engineer',
                model=claude_sonnet_4,
                system_prompt=senior_engineer_prompt.format(project_name=project_name),
                tools=[editor, file_read, file_write, shell, *context7_tools, *aws_documentation_tools],
                callback_handler=None
            )
            
            impl_task = f"""
            Jira Story: {jira_story}
            
            Implementation Plan:
            {plan}
            
            CRITICAL RULES:
            1. Implement ONLY what is specified in the Jira story
            2. Do NOT modify unrelated code
            3. Do NOT add extra features or improvements
            """
            
            change_summary = str(senior_agent(impl_task))
            print(f"Implementation completed:\\n{change_summary}")

            print("Step 3: Capturing changes via git manifest")
            change_manifest = get_manifest(project_name=project_name, py_only=True)
            
            if not change_manifest.get("changes"):
                print("No changes detected in manifest!")
                return "Workflow complete but no changes were made."
            
            print(f"Manifest captured {len(change_manifest.get('changes', []))} file changes")

            print("Step 4: Code review phase")
            
            code_diffs = format_manifest_code_diffs(change_manifest) 
            review_task = f"""Changes to review:\n{code_diffs}"""
            print(f"==>> review_task: \n{review_task}")
            
            start_time = time.perf_counter()
            feedback_results = await asyncio.gather(*[
                agent.invoke_async(review_task) for agent in review_agents.values()
            ])
            feedback = dict(zip(review_agents.keys(), map(str, feedback_results)))
            end_time = time.perf_counter()
            print(f"Review agents feedback completed in {end_time - start_time:.2f} seconds")

            for role, fb in feedback.items():
                print("role", role)
                print("feedback", fb)

            combined_feedback = '\n'.join([f"{role.upper()}: {fb}" for role, fb in feedback.items() if fb])
            print(f"Code review completed:\\n{combined_feedback}")

            print("Step 5: Incorporating review feedback")
            
            revise_task = f"""
            Jira Story: {jira_story}
            
            Original Plan: {plan}
            
            Your Implementation Summary: {change_summary}
            
            Code Review Feedback: {combined_feedback}
            
            TASK: Address the review feedback by making necessary changes.
            
            RULES:
            1. Fix only the issues mentioned in the feedback
            2. Stay within the scope of the Jira story
            """
            
            revised_summary = str(senior_agent(revise_task))
            print(f"Revisions completed:\\n{revised_summary}")
            change_summary += f"\\n\\nRevisions based on feedback:\\n{revised_summary}"
            
            # Update manifest after revisions
            change_manifest = get_manifest(project_name=project_name, py_only=True)
            code_diffs = format_manifest_code_diffs(change_manifest) 

            print("Step 6: Story scoring phase")
               
            score_task = f"""
            Jira Story: {jira_story}
            
            Implementation Plan: {plan}
            
            Changes Manifest: {code_diffs}
            
            Final Implementation Summary: {change_summary}
            
            Evaluate whether the implementation fulfills the Jira story requirements.
            Use file_read to review the actual changed code sections from the manifest.
            """
            score = str(story_scoring_agent(score_task))
            print(f"Story score: {score}")

            print("Step 7: Generating PR documentation")

            doc_agent = Agent(
                name='doc_agent',
                model=bedrock_nova_pro_model,
                system_prompt=doc_prompt.format(
                    project_name=project_name,
                    jira_story_id=jira_story_id
                ),
                tools=[file_write, file_read, shell],
                callback_handler=None
            )
            
            doc_task = f"""
            Generate PR body for Jira Story: {jira_story_id}
            
            Story Details: {jira_story}
            
            Implementation Plan: {plan}
            
            Changes Summary: {change_summary}
            
            Changes Manifest: {code_diffs}
            
            Story Score: {score}
            
            Create a comprehensive PR body markdown file at /tmp/{project_name}/{jira_story_id}.md
            """
            doc_result = str(doc_agent(doc_task))
            print(f"doc_result", doc_result)
            print("PR documentation generated successfully")
            
            return json.dumps({
                "status": "success",
                "jira_story_id": jira_story_id,
                "changes_count": len(change_manifest.get('changes', [])),
                "score": score,
                "pr_doc_path": f"/tmp/{project_name}/{jira_story_id}.md"
            }, indent=2)

    except Exception as e:
        print(f"Workflow failed: {str(e)}")
        print(traceback.format_exc())
        raise