## Nemo AI - Hack This Fall 2025 - Milestone Edition

#### Cut Your Feature Delivery Time in Half. Nemo AI converts your Jira Stories into ready-to-review GitHub Pull Requests using AgenticAI.

**An intelligent multi-agent system that autonomously converts Jira stories into ready-to-review Github Pull Request using AWS Bedrock and AgentCore.**

## Project Overview

Nemo AI is an autonomous AI agent that turns Jira stories into first draft of Pull Request — automatically. It understands your jira story, analyzes your existing codebase, and creates a GitHub Pull Request with a first draft of the solution. It works with your existing tools like Jira, Confluence, GitHub, and AWS, so it fits naturally into your development workflow.

## Architecture

### Core Engine
Core Engine — Orchestrates the complete Nemo AI workflow for both code development ("First Draft") and data analysis ("Unpaid Intern"). Built a modular, multi-agent system using AWS Bedrock and AgentCore.

### System Internals

#### Multi-Agent Workflow Architecture
The system employs a **8-agent pipeline** that processes Jira stories through distinct phases:

1. **Planner Agent** - Analyzes Jira stories and creates implementation plans
2. **Senior Engineer Agent** - Responsible for implementing the proposed solution. The only agent that modifies code.
3. **Code Reviewer Agent** - Comprehensive code review covering security, quality, and design
4. **Coding Standards Agent** - Python best practices and PEP compliance
5. **System Design Agent** - Architecture and design patterns review
6. **Algorithm Specialist** - Performance and efficiency analysis
7. **Story Scoring Agent** - Validates implementation against Jira requirements
8. **Documentation Agent** - Generates a Pull Request (PR) comment writeup based on the changes.
 
#### Dual Workflow Support
- **Code Development Workflow** (`workflow.py`) - The First Draft - Nemo AI serves as an autonomous software developer that turns Jira stories into ready-to-review pull requests. When a story moves to `In Progress`
- **Data Analyst** (`data_analyst_workflow.py`) - Nemo AI's Unpaid intern that delivers fast, accurate business insights without requiring SQL or Python skills.

## Repository Structure & Navigation

### Core Components

```
src/
├── core/                           # Main workflow orchestration
│   ├── workflow.py                 # Multi-agent code development pipeline
│   ├── data_analyst_workflow.py    # Data analysis workflow with Code Interpreter
│   └── run_workflow.py             # Workflow dispatcher and GitHub integration
├── custom_tools/                   # Strands SDK tool implementations
│   ├── editor.py                   # Code editing capabilities
│   ├── file_read.py               # File reading operations
│   ├── file_write.py              # File writing operations
│   └── shell.py                   # Shell command execution
├── prompt/                         # Agent system prompts
│   └── agent_prompt.py            # All 7 agent prompts and instructions
├── utils/                          # Utility modules
│   ├── github_utils.py            # GitHub API integration and PR management
│   ├── change_manifest.py         # Git diff tracking and change detection
│   ├── aws_secrets.py             # AWS Secrets Manager integration
│   └── otel_utils.py              # OpenTelemetry observability setup
└── ckg/                           # Code Knowledge Graph (experimental)
    ├── ast_reader.py              # Abstract Syntax Tree analysis
    └── ckg_vector_store_*.py      # Vector store implementations
```

### Entry Points

- **`main.py`** - AWS Lambda handler for SQS-triggered workflows
- **`ecs_main.py`** - ECS Fargate task for long-running workflows
- **`cdk_app.py`** - AWS CDK infrastructure deployment

### Framework
- **Strands Agents SDK**: Multi-agent workflow orchestration with async execution and tool integration
- **Model Context Protocol (MCP)**: 
  - **Context7 MCP** - Real-time library documentation and code examples
  - **AWS Knowledge MCP** - AWS service documentation and best practices
- **AgentCore Observability**: Distributed tracing and observability with OTLP export

### Development Tools
- **GitHub Integration**: Automated PR creation and repository management
- **Confluence Integration**: Fetch confluence page for additional context
- **Jira Integration**: Story parsing and requirement extraction
- **Docker**: Containerized deployment

## Quick Start

### Prerequisites
- AWS Account with Bedrock and AgentCore access
- Python 3.13+
- Docker
- AWS CDK

### Usage

#### Lambda Deployment (< 15 minutes)
```python
{
    "github_link": "https://github.com/user/repo",
    "jira_story": "Create API endpoint for user authentication",
    "jira_story_id": "AUTH-123",
    "is_data_analysis_task": False
}
```

#### ECS Task Execution (Long-running tasks)
```bash
# Set environment variables
export GITHUB_LINK="https://github.com/user/repo"
export JIRA_STORY="Analyze user engagement data and create visualizations"
export JIRA_STORY_ID="DATA-456"
export IS_DATA_ANALYSIS_TASK="true"

# Run ECS task
python ecs_main.py
```

### Architecture Decisions
- **Multi-Agent Design** - Specialized agents for different aspects of code review
- **MCP Integration** - Real-time documentation access for accurate implementations  
- **Processing** - Lambda for quick tasks, ECS for complex analysis
- **Integration** - Integrationg with Jira, Github, Confluence, external MCP Servers, Observability.

### End-to-End Workflow Process

#### Code Development Pipeline
1. **Repository Cloning** - GitHub repository is cloned to `/tmp/{project_name}`
2. **Planning Phase** - Planner agent analyzes Jira story and creates implementation plan
3. **Implementation** - Senior Engineer agent writes code using MCP documentation
4. **Change Detection** - Git manifest captures all modifications
5. **Parallel Review** - 5 specialized agents review code concurrently
6. **Revision** - Senior Engineer addresses review feedback
7. **Validation** - Story Scoring agent validates requirements fulfillment
8. **Documentation** - PR body generation with technical details
9. **GitHub Integration** - Automated PR creation with comprehensive details

#### Data Analytics Pipeline
1. **File Upload** - Data files uploaded to AgentCore Code Interpreter sandbox
2. **Analysis Execution** - Python code execution in secure environment
3. **Visualization Generation** - Charts, graphs, and reports created
4. **Export** - Results exported back to local filesystem
5. **PR Creation** - Analysis results committed to repository

## Local Development & Debugging

### Local Development
```bash
# Install dependencies
pip install -r requirements-dev.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your AWS credentials and configuration

# Run locally with test data
python main.py
```

## Contributing

This project is part of Hack This Fall 2025 - Milestone Edition.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
