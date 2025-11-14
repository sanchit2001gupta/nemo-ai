import json
import asyncio

from dotenv import load_dotenv

from src.core.run_workflow import run_nemo_agent_workflow

load_dotenv()

def lambda_handler(event, context):

    # Get the JIRA story description from the event body
    if "Records" not in event:
        return {
            "statusCode": 200,
            "body": "No records found in the event payload."
        }
    
    required_fields = ["github_link", "jira_story", "jira_story_id", "is_data_analysis_task"]
    for record in event["Records"]:
        try:
            payload = json.loads(record["body"])
            print("payload", payload)

            if not all(field in payload for field in required_fields):
                missing = [field for field in required_fields if field not in payload]
                print(f"⚠️ Skipping message: missing fields: {missing} {str(record)}")
                continue 
            
            output = asyncio.run(run_nemo_agent_workflow(
                github_link=payload["github_link"],
                jira_story=payload["jira_story"],
                jira_story_id=payload["jira_story_id"],
                is_data_analysis_task=payload['is_data_analysis_task']
            ))
            print(f"✅ Lambda workflow complete: {output}")
            return {"statusCode": 200, "body": "Workflow complete."}

        except Exception as e:
            print(f"❌ Error processing record: {str(e)}")
        
    return {
        "statusCode": 200,
        "body": "Lambda executed. All messages processed."
    }

if __name__ == "__main__":
    payload = {
        'Records': [
            {
                'body': json.dumps({
                    "github_link": "https://github.com/harshitsinghai77/nemo-ai-demo-1",
                    "jira_story": "Create a new route inside the agentRoutes.py which takes two numbers from the query parameter and return the sum of it in JSON format, with keys like num1, num2, total",
                    "jira_story_id": "FIN-1024",
                    "is_data_analysis_task": False
                })
            }
        ]}
    response = lambda_handler(payload, context=None)
    print("=== Lambda Response ===")
    print(response)