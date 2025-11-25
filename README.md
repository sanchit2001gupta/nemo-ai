## Nemo AI Core Agent - AWS AI Agent Global Hackathon

#### Cut Your Feature Delivery Time in Half. Nemo AI converts your Jira Stories into ready-to-review GitHub Pull Requests using AWS Bedrock and AgentCore..

**An intelligent multi-agent system that autonomously converts Jira stories into ready-to-review Github Pull Request using AWS Bedrock and AgentCore.**

[![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock-orange)](https://aws.amazon.com/bedrock/)
[![AgentCore](https://img.shields.io/badge/AWS-AgentCore-blue)](https://aws.amazon.com/bedrock/agentcore/)
[![Strands SDK](https://img.shields.io/badge/Strands-SDK-green)](https://strands.ai/)
[![Python](https://img.shields.io/badge/Python-3.13+-blue)](https://python.org)

## Project Overview

Nemo AI is an autonomous AI agent that turns Jira stories into first draft of Pull Request — automatically. It understands your jira story, analyzes your existing codebase, and creates a GitHub Pull Request with a first draft of the solution. It works with your existing tools like Jira, Confluence, GitHub, and AWS, so it fits naturally into your development workflow.

## Architecture

### Core Engine (This Repository)
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

#### AWS Bedrock Integration
- **Claude Sonnet 4** - Primary model for complex reasoning and code generation
- **AWS Nova Pro** - Secondary model for specialized review tasks
- **AgentCore Code Interpreter** - Secure Python execution environment for data analysis 

### Nemo AI – Infrastructure Setup Order

Deploy the infrastructure repositories in the following order for end-to-end setup:

| Order | Service | Repository | Purpose |
|-------|---------|------------|---------|
| **1** | **AWS Bootstrap** | [nemo-ai-aws-infra-bootstrap](https://github.com/harshitsinghai77/nemo-ai-aws-infra-bootstrap) | Bootstraps AWS environment using CDK bootstrap command. Essential first step for CDK deployments. |
| **2** | **DynamoDB Storage** | [nemo-ai-dynamodb](https://github.com/harshitsinghai77/nemo-ai-dynamodb) | Database for Jira story ingested via Lambda. |
| **3** | **Jira Ingestion API Lambda** | [nemo-ai-jira-ingestion-api](https://github.com/harshitsinghai77/nemo-ai-jira-ingestion-api) | Exposes an API endpoint to receive Jira webhooks, processes story data, and routes tasks: publishes standard tasks to SQS or directly invokes ECS Fargate tasks for long-running operations based on Jira story description. |
| **4** | **Message Queue** | [nemo-ai-sqs](https://github.com/harshitsinghai77/nemo-ai-sqs) | Enables decoupled communication between Jira Ingestion Lambda and Core Engine Lambda using a producer-consumer architecture. |
| **5** | **Core Engine** | [**This Repository**](https://github.com/harshitsinghai77/nemo-ai-core-agent) | Supports dual execution modes: creates Lambda Docker image for SQS-triggered standard workflows (<15 min) and pushes ECS Docker image to ECR for direct Fargate task invocation on complex/long-running operations. Routing decision made by Jira Ingestion Lambda based on Jira story description. |
| **6** | **ECS Task Definitions** | [nemo-ai-ecs-fargate-core](https://github.com/harshitsinghai77/nemo-ai-ecs-fargate-core) | Contains ECS Fargate task definitions that use the Docker image pushed to ECR from the Core Engine repository. |
| **7** | **Observability** | [nemo-ai-observability-infra](https://github.com/harshitsinghai77/nemo-ai-observability-infra) | CloudWatch integration for Bedrock AgentCore Observability. Deploy last to monitor the complete system. |

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

### Key Workflow Classes

#### DataAnalystWorkflow (`data_analyst_workflow.py`)
- **FileHandler** - Manages file operations and uploads to Code Interpreter
- **CodeInterpreterSession** - AWS AgentCore Code Interpreter management
- **DataAnalystAgent** - Strands agent with Python execution tools

#### Multi-Agent Pipeline (`workflow.py`)
- **Agent Initialization** - Sets up 8 specialized agents with different models
- **MCP Integration** - Context7 and AWS Documentation MCP servers
- **Change Tracking** - Git-based manifest system for code changes
- **Review Orchestration** - Async Parallel execution of review agents

## Technology Stack

### AWS Services Architecture

#### Core AI Services
- **Amazon Bedrock**: Foundation models orchestration
  - `us.anthropic.claude-sonnet-4-20250514-v1:0` - Primary reasoning and code generation
  - `us.amazon.nova-pro-v1:0` - Specialized review tasks and analysis
  - Cross-region failover with retry configuration

- **AgentCore Code Interpreter**: Secure execution environment
  - **Code Interpreter** - Isolated Python sandbox for executing Python code
  - **Memory Service** - Persistent context across agent interactions
  - **Observability** - Built-in tracing and monitoring

#### Compute & Orchestration
- **AWS Lambda**: Event-driven serverless execution
  - Python 3.13 runtime with AWS Powertools
  - SQS trigger integration for Jira webhook processing
  - 15-minute timeout limit for standard workflows
  - Auto-scaling based on SQS queue depth
 
- **Amazon ECS Fargate**: Container orchestration for long-running tasks
  - Custom task definitions with resource allocation
  
#### Data & Messaging
- **Amazon SQS**: Asynchronous message processing
  - Standard queues for Jira webhook ingestion
  - Dead letter queues for error handling
  - Message visibility timeout configuration
  - Batch processing for improved throughput

- **Amazon DynamoDB**: NoSQL database for metadata
  - Jira story tracking and status management
  - On-demand billing with auto-scaling
  - Global secondary indexes for query optimization
 
### AI & ML Framework
- **Strands Agents SDK**: Multi-agent workflow orchestration with async execution and tool integration
- **Model Context Protocol (MCP)**: 
  - **Context7 MCP** - Real-time library documentation and code examples
  - **AWS Knowledge MCP** - AWS service documentation and best practices
- **AgentCore Observability**: Distributed tracing and observability with OTLP export


#### MCP Server Integration
```python
# Context7 MCP for library documentation
context7_mcp = MCPClient(lambda: streamablehttp_client("https://mcp.context7.com/mcp"))

# AWS Documentation MCP for service knowledge
aws_documentation_mcp = MCPClient(lambda: streamablehttp_client("https://knowledge-mcp.global.api.aws"))
```

#### Parallel Agent Execution
```python
# Concurrent review by multiple specialized agents
feedback_results = await asyncio.gather(*[
    agent.invoke_async(review_task) for agent in review_agents.values()
])
```

### Development Tools
- **GitHub Integration**: Automated PR creation and repository management
- **Jira Integration**: Story parsing and requirement extraction
- **Docker**: Containerized deployment

## Quick Start

### Prerequisites
- AWS Account with Bedrock and AgentCore access
- Python 3.13+
- Docker
- AWS CDK

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/your-username/nemo-ai-core-agent
cd nemo-ai-core-agent
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure AWS credentials**
```bash
aws configure
```

### Deploy Infrastructure with AWS CDK

Deploy the AWS infrastructure including the Lambda function with Docker image support and SQS integration using AWS CDK:

```bash
# Install CDK CLI if not already installed
npm install -g aws-cdk

# Install Python dependencies
pip install -r requirements-dev.txt

# Bootstrap your AWS environment (run once per account/region)
cdk bootstrap aws://<ACCOUNT_ID>/us-east-1

# Deploy the CDK stack
cdk deploy

### Docker Deployment Options

The project includes three Docker configurations for different environments:

#### Local Development
```bash
# Build and run local development container
docker build -f Dockerfile_local -t nemo-ai-local .
docker run -it --rm -v $(pwd):/app -v ~/.aws:/root/.aws nemo-ai-local bash
```

#### AWS Lambda Container
```bash
cdk deploy
```

#### ECS Fargate Container
```bash
# Build ECS container with OpenTelemetry support
docker build -f Dockerfile_ECS -t nemo-ai-ecs .
# Deploy to ECR and update ECS service
docker tag nemo-ai-ecs:latest <account>.dkr.ecr.us-east-1.amazonaws.com/nemo-ai-ecs:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/nemo-ai-ecs:latest
```

### Usage

#### Lambda Deployment (< 15 minutes)
```python
# Triggered via SQS message from Jira webhook
{
    "github_link": "https://github.com/user/repo",
    "jira_story": "Create API endpoint for user authentication",
    "jira_story_id": "AUTH-123",
    "is_data_analysis_task": false
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

### Key Internal Components

#### Change Manifest System
```python
# Tracks all code modifications with precise line-level changes
change_manifest = get_manifest(project_name=project_name, py_only=True)
# Returns: {"changes": [{"file_path": "...", "change_type": "...", "content": "..."}]}
```

#### MCP Documentation Lookup
```python
# Automatic library documentation retrieval
# 1. resolve-library-id("boto3") → get library_id  
# 2. get-library-docs(library_id, "S3 client usage") → latest API docs
# 3. AWS Documentation search for best practices
```

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

### Key Configuration Files
- **`.env`** - Environment variables and AWS configuration
- **`otel_config.env`** - OpenTelemetry observability settings
- **`cdk.json`** - AWS CDK deployment configuration
- **`requirements.txt`** - Production dependencies
- **`requirements-dev.txt`** - Development dependencies

### Monitoring & Observability
- **AgentCore Observability** - Built-in tracing for agent execution
- **OpenTelemetry Integration** - Distributed tracing across the workflow
- **CloudWatch Logs** - Comprehensive logging for debugging

### Customization Points

#### Adding New Review Agents
```python
# In workflow.py
new_review_agent = Agent(
    name='new_reviewer',
    model=bedrock_nova_pro_model,
    system_prompt=your_custom_prompt,
    tools=[file_read, shell]
)

# Add to review_agents dictionary
review_agents['new_reviewer'] = new_review_agent
```

### Hackathon Requirements

**LLM**: AWS Bedrock (Claude Sonnet 4, Nova Pro)  
**AgentCore**: Code Interpreter for secure code execution  
**Autonomous Capabilities**: Multi-agent workflow with reasoning  
**External Integrations**: MCP Servers (Context7 MCP and AWS Knowledge MCP Server), GitHub, Confluence, Jira  
**Strands SDK Implementation**: Multi-agent workflow pattern using Strands SDK. 

## Contributing

This project is part of the AWS AI Agent Global Hackathon 2025. For questions or collaboration opportunities, please reach out through the hackathon platform.

### Architecture Decisions
- **Multi-Agent Design** - Specialized agents for different aspects of code review
- **MCP Integration** - Real-time documentation access for accurate implementations  
- **Processing** - Lambda for quick tasks, ECS for complex analysis
- **Integration** - Integrationg with Jira, Github, Confluence, external MCP Servers, Observability.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built for AWS AI Hackathon 2025**  
*Nemo AI handles the first draft, so your team can focus on what matters: shipping quality features, solving hard problems, and scaling faster.*