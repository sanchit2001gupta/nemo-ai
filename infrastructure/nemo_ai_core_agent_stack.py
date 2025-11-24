import os
from dotenv import load_dotenv

from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_sqs as _sqs,
    aws_lambda_event_sources as _event_sources,
    aws_iam as _iam,
    CfnOutput,
)
from constructs import Construct
from aws_cdk.aws_ecr_assets import DockerImageAsset

load_dotenv(dotenv_path='otel_config.env')
open_telemetry_envs = {
    key: value for key, value in os.environ.items() if key.startswith("OTEL_")
}

class NemoCoreAgentStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        aws_account = Stack.of(self).account

        docker_asset = DockerImageAsset(self, 
            "NemoAILambdaDockerImage",
            directory=os.getcwd(),
            display_name='nemo-ai-agentic-lambda-container'
        )

        docker_lambda = _lambda.DockerImageFunction(
            self, "NemoAgentDockerLambda",
            code=_lambda.DockerImageCode.from_ecr(
                repository=docker_asset.repository,
                tag_or_digest=docker_asset.image_tag
            ),
            memory_size=1024,
            timeout=Duration.seconds(900),
            environment={
                "LOG_LEVEL": "INFO",
                "AWS_ACCOUNT_ID": aws_account,
                "AGENT_OBSERVABILITY_ENABLED": "true",
                **open_telemetry_envs
            }
        )
        queue = _sqs.Queue.from_queue_arn(
            self,
            "ImportedQueue",
            f"arn:aws:sqs:us-east-1:{aws_account}:nemo-ai-tasks.fifo"
        )

        docker_lambda.add_event_source(
            _event_sources.SqsEventSource(
                queue,
                batch_size=1,
                enabled=True
            )
        )

        queue.grant_consume_messages(docker_lambda)

        docker_lambda.add_to_role_policy(
            _iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
       
                    "bedrock-agentcore:CreateCodeInterpreter",
                    "bedrock-agentcore:StartCodeInterpreterSession",
                    "bedrock-agentcore:InvokeCodeInterpreter",
                    "bedrock-agentcore:StopCodeInterpreterSession",
                    "bedrock-agentcore:DeleteCodeInterpreter",
                    "bedrock-agentcore:ListCodeInterpreters",
                    "bedrock-agentcore:GetCodeInterpreter",

                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                ],
                resources=["*"],
            )
        )

        docker_lambda.add_to_role_policy(
            _iam.PolicyStatement(
                actions=[
                    "secretsmanager:GetSecretValue"
                ],
                resources=[f"arn:aws:secretsmanager:us-east-1:{aws_account}:secret:github_personal_access_token-mhV2eN"],
            )
        )

        docker_lambda.add_to_role_policy(
            _iam.PolicyStatement(
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                resources=[
                    f"arn:aws:logs:*:{aws_account}:log-group:/aws/bedrock-agentcore/code-interpreter*"
                ],
            )
        )

        CfnOutput(
            self, "LambdaFunctionName",
            value=docker_lambda.function_name,
            description="Docker-based Lambda deployed via CDK"
        )

