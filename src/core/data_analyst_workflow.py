import os
import logging
import json
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional

import boto3
from botocore.config import Config
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
from strands import Agent, tool
from strands.models import BedrockModel

from prompt.agent_prompt import data_analyst_prompt

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

session = boto3.Session()

class FileHandler:
    """Handles file operations for the data analyst workflow."""

    @staticmethod
    def fetch_files(project_dir: str, supported_extensions: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """Detect and read all supported files in the project directory."""
        supported_extensions = supported_extensions or ['.csv', '.json']
        if not os.path.isdir(project_dir):
            raise ValueError(f"Project directory does not exist: {project_dir}")

        files_to_create = []
        for root, _, files in os.walk(project_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext not in supported_extensions:
                    continue
                try:
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    relative_path = os.path.relpath(file_path, project_dir)
                    files_to_create.append({"path": f"nemo_files/{relative_path}", "text": content})
                except Exception as e:
                    logger.info(f"Error reading file {file_path}: {e}")
        return files_to_create

class CodeInterpreterSession:
    """Manages the AWS Bedrock Code Interpreter session."""

    def __init__(self, session_timeout: int = 1200):
        self.session_timeout = session_timeout
        self.client: Optional[CodeInterpreter] = None
        self.code_interpreter_id = self.get_or_create_code_interpreter_id()

    def start(self) -> None:
        """Start the Code Interpreter session."""
        self.client = CodeInterpreter(region="us-east-1", session=session)
        self.client.start(session_timeout_seconds=self.session_timeout, identifier=self.code_interpreter_id)
        logger.info(f"Code Interpreter session started in us-east-1")

    def stop(self) -> None:
        """Stop the Code Interpreter session."""
        if self.client:
            self.client.stop()
            logger.info("Code Interpreter session stopped successfully!")

    def get_or_create_code_interpreter_id(self, interpreter_name: str = "nemo_ai_code_interpreter_v1") -> str:
        """Get or create the Code Interpreter session ID."""
        agentcore_control_client = session.client(
            'bedrock-agentcore-control',
            region_name='us-east-1',
            endpoint_url=f"https://bedrock-agentcore-control.us-east-1.amazonaws.com"
        )

        for ci in agentcore_control_client.list_code_interpreters()["codeInterpreterSummaries"]:
            if ci.get('name') == interpreter_name:
                return ci.get('codeInterpreterId')
        
        resp = agentcore_control_client.create_code_interpreter(
            name=interpreter_name,
            description="Sandbox Environment for Nemo AI Code Interpreter",
            networkConfiguration={"networkMode": "PUBLIC"}
        )
        return resp["codeInterpreterId"]

    def invoke_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Invoke a tool in the Code Interpreter sandbox."""
        if not self.client:
            raise RuntimeError("Code Interpreter session not started")

        response = self.client.invoke(tool_name, arguments)
        for event in response["stream"]:
            return json.dumps(event["result"])
        return "{}"

    def upload_files(self, files_to_create: List[Dict[str, str]]) -> None:
        """Upload files into the Code Interpreter sandbox."""
        result = self.invoke_tool("writeFiles", {"content": files_to_create})
        return result

    def list_files(self, directory_path: str = 'nemo_files/') -> None:
        """List all files in the Code Interpreter sandbox."""
        listing_result = self.invoke_tool("listFiles", {"directoryPath": directory_path})
        return json.loads(listing_result)
    
    def collect_all_files(self, base_path: str = "nemo_files/") -> list:
        """Recursively collect all file URIs in sandbox, excluding directories."""
        file_uris = []

        def recurse(directory_path):
            logger.info(f"Listing: {directory_path}")
            listing = self.list_files(directory_path)

            if listing.get("isError"):
                logger.warning(f"Error listing directory: {directory_path}")
                return

            for item in listing.get("content", []):
                uri = item.get("uri")
                description = item.get("description", "")
                if description == "File":
                    file_uris.append(uri)
                elif description == "Directory":
                    # Parse the path from URI
                    parsed = urlparse(uri)
                    sub_path = parsed.path.lstrip("/")  # Remove leading '/'
                    recurse(sub_path)

        recurse(base_path)
        return file_uris

    def export_files(self, output_dir: str) -> None:
        """Export all files from the sandbox environment into the local directory."""
        
        logger.info(f"Exporting files from sandbox to {output_dir}")
        
        file_uris = self.collect_all_files()
        if not file_uris:
            logger.info("No files found in sandbox.")
            return

        logger.info(f"Total files found: {len(file_uris)}")

        response = self.client.invoke("readFiles", { "paths": file_uris })
        
        for event in response["stream"]:
            result = event.get("result", {})
            content_list = result.get("content", [])

            for item in content_list:
                if item.get("type") != "resource":
                    continue

                resource = item["resource"]
                uri = resource.get("uri", "")
                mime_type = resource.get("mimeType", "")
                text_data = resource.get("text", None)
                blob_data = resource.get("blob")
                
                # Extract file name from URI like 'file:///nemo_files/strong_pokemon.csv'
                parsed_uri = urlparse(uri)
                file_name = os.path.basename(parsed_uri.path)
                local_path = os.path.join(output_dir, file_name)

                # Save text files (CSV, etc.)
                if mime_type.startswith("text") and text_data is not None:
                    with open(local_path, "w", encoding="utf-8") as f:
                        f.write(text_data)
                    logger.info(f"✅ Saved text file: {local_path}")

                # Save binary files (images, etc.)
                elif (mime_type.startswith("image") or mime_type == "application/pdf") and blob_data is not None:
                    with open(local_path, "wb") as f:
                        f.write(blob_data)
                    logger.info(f"🖼️ Saved binary file: {local_path}")
                else:
                    logger.info(f"⚠️ Skipped unsupported or empty file: {uri}")
        return True

class DataAnalystAgent:
    """Agent for data analysis using AWS Bedrock and Code Interpreter."""

    def __init__(self, code_interpreter_session: CodeInterpreterSession, project_name: str, jira_story_id: str):
        self.code_interpreter_session = code_interpreter_session 
        self.project_name = project_name
        self.jira_story_id = jira_story_id
        self.agent = self._setup_agent()
    
    def _setup_agent(self) -> Agent:
        """Set up the Strands agent with the model and tools."""
        model = BedrockModel(
            model_id = 'us.anthropic.claude-sonnet-4-20250514-v1:0',
            boto_session = session,
            boto_client_config = Config(
                retries={'max_attempts': 5, 'mode': 'standard'},
                read_timeout=180
            )
        )
        system_prompt = data_analyst_prompt.format(
            project_name=self.project_name,
            jira_story_id=self.jira_story_id
        )

        @tool
        def execute_python(code: str, description: str = "") -> str:
            """Execute Python code in the sandbox."""
            if description:
                code = f"# {description}\n{code}"
            logger.info(f"\nGenerated Code: {code}")
            response = self.code_interpreter_session.client.invoke("executeCode", {
                "code": code,
                "language": "python",
                "clearContext": False
            })
            for event in response["stream"]:
                res = json.dumps(event["result"])
                logger.info(f"==>> res of execute_python: {res}")
                return res
            return "{}"

        @tool
        def execute_command(command: str, description: str = "") -> str:
            """Execute a shell command inside the sandbox interpreter."""
            logger.info(f"\n[{description}] Running command inside Sandbox: {command}")
            response = self.code_interpreter_session.client.invoke("executeCommand", {
                "command": command
            })

            for event in response["stream"]:
                return json.dumps(event["result"])

            return "{}"

        return Agent(
            model=model,
            tools=[execute_python, execute_command],
            system_prompt=system_prompt
        )

    async def run(self, jira_story: str) -> str:
        """Process a Jira story using the agent and stream the response."""
        response_text = ""
        async for event in self.agent.stream_async(jira_story):
            if "data" in event:
                chunk = event["data"]
                response_text += chunk
                print(chunk, end="")
        return response_text

class DataAnalystWorkflow:
    """Main workflow for data analysis tasks."""

    def __init__(self, project_name: str, jira_story_id: str, session_timeout: int = 1200):
        self.project_name = project_name
        self.jira_story_id = jira_story_id
        self.project_path = f"/tmp/{project_name}"
        self.code_interpreter_session = CodeInterpreterSession(session_timeout=session_timeout)
        self.agent: Optional[DataAnalystAgent] = None

    def setup(self) -> None:
        """Set up the workflow with necessary components."""
        self.code_interpreter_session.start()

        files_to_create = FileHandler.fetch_files(self.project_path)
        if not files_to_create:
            raise ValueError(f"Could not read data from {self.project_path}")

        self.code_interpreter_session.upload_files(files_to_create)

        self.agent = DataAnalystAgent(
            code_interpreter_session=self.code_interpreter_session,
            project_name=self.project_name,
            jira_story_id=self.jira_story_id
        )

    async def start_analysis(self, jira_story: str) -> str:
        """Start the analysis for the provided Jira story."""
        logger.info(f"\n\nProcessing Jira Story: {jira_story}\n")
        return await self.agent.run(jira_story)

    def export_outputs(self) -> None:
        """Export sandbox outputs to the project path."""
        self.code_interpreter_session.export_files(self.project_path)

    def cleanup(self) -> None:
        """Clean up resources used by the workflow."""
        self.code_interpreter_session.stop()

async def data_analyst_workflow(project_name: str, jira_story: str, jira_story_id: str):
    """Run the full data analyst workflow."""
    workflow = DataAnalystWorkflow(project_name, jira_story_id)
    try:
        workflow.setup()
        response_text = await workflow.start_analysis(jira_story)
        logger.info(f"\n\nComplete Response Text:\n{response_text}\n")
        workflow.export_outputs()
        return {"response_text": response_text, "project_path": workflow.project_path}
    finally:
        workflow.cleanup()
