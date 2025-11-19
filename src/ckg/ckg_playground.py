import os
import ast
import boto3
import json
import requests
import uuid
from dataclasses import dataclass, asdict
from typing import Optional, List
import boto3
from dotenv import load_dotenv
from ckg_vector_store_qdrant import QdrantVectorStore

load_dotenv()

# aws s3vectors delete-index --vector-bucket-name "nemo-ai-vector-bucket" --index-name "nemo-ai-vector-index" --region us-east-1 --profile personal-dev
# aws s3vectors create-index --vector-bucket-name "nemo-ai-vector-bucket" --index-name "nemo-ai-vector-index" --dimension 1024 --data-type "float32" --distance-metric cosine --profile personal-dev

session_bedrock = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name="us-east-1"
)
# session = boto3.Session(profile_name="personal-dev")
session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID_PERSONAL_DEV"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY_PERSONAL_DEV"),
    region_name="us-east-1"
)

bedrock_client = session_bedrock.client("bedrock-runtime")
model_id = "amazon.titan-embed-text-v2:0"

VECTOR_BUCKET = "nemo-ai-vector-bucket"
VECTOR_INDEX = "nemo-ai-vector-index"
AST_BUCKET = "nemo-ai-ast-bucket"

s3 = session.client("s3")
# s3vectors = session.client("s3vectors")
store = QdrantVectorStore(collection_name=VECTOR_INDEX, dim=1024)

@dataclass
class CodeEntry:
    """Code entry metadata extracted from AST."""
    name: str
    type: str   # "function", "async_function", "class", "variable"
    file_path: str
    body: str
    start_line: int
    end_line: int
    docstring: Optional[str] = 'None'
    decorators: Optional[str] = 'None'
    llm_summary: Optional[str] = 'Random LLM Summary'
    parent_function: Optional[str] = 'None'
    parent_class: Optional[str] = 'None'
    fields: Optional[str] = 'None'
    methods: Optional[str] = 'None'
    value: Optional[str] = 'None'

def extract_docstring(node):
    return ast.get_docstring(node)

def extract_decorators(node: ast.AST) -> str:
    if hasattr(node, 'decorator_list'):
        return "\n".join([ast.unparse(d) for d in node.decorator_list]) if node.decorator_list else ''
    return ''

def parse_python_ast(file_path: str):
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    tree = ast.parse(code)
    lines = code.splitlines()
    entries: List[CodeEntry] = []

    def get_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        args = [arg.arg for arg in node.args.args]
        sig = f"{node.name}({', '.join(args)})"
        if node.returns:
            try:
                return_type = ast.unparse(node.returns)
                sig += f" -> {return_type}"
            except Exception:
                pass
        return sig

    def visit(node, parent_class=None, parent_func=None):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_type = "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function"
            body = "\n".join(lines[node.lineno - 1: node.end_lineno])
            entry = CodeEntry(
                name=node.name,
                type=func_type,
                file_path=file_path,
                body=body,
                start_line=node.lineno,
                end_line=node.end_lineno,
                docstring=extract_docstring(node) or '',
                decorators=extract_decorators(node),
                parent_function=parent_func.name if parent_func else '',
                parent_class=parent_class.name if parent_class else ''
            )
            entries.append(entry)
            parent_func = entry

        elif isinstance(node, ast.ClassDef):
            body = "\n".join(lines[node.lineno - 1: node.end_lineno])
            methods = []

            # Capture base classes
            try:
                base_classes = [ast.unparse(base) for base in node.bases]
            except Exception:
                base_classes = []
                
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(get_signature(child))
                    
            class_entry = CodeEntry(
                name=node.name,
                type="class",
                file_path=file_path,
                body=body,
                start_line=node.lineno,
                end_line=node.end_lineno,
                docstring=extract_docstring(node) or '',
                decorators=extract_decorators(node),
                methods="\n".join(methods) if methods else '',
                fields=', '.join(base_classes) if base_classes else '',
            )
            entries.append(class_entry)
            parent_class = class_entry

        # elif isinstance(node, ast.Assign):
        #     if isinstance(node.targets[0], ast.Name):
        #         name = node.targets[0].id
        #         try:
        #             value = ast.unparse(node.value)
        #         except Exception:
        #             value = ""
        #         body = lines[node.lineno - 1]
        #         entry = CodeEntry(
        #             name=name,
        #             type="variable",
        #             file_path=file_path,
        #             body=body,
        #             start_line=node.lineno,
        #             end_line=node.end_lineno,
        #             value=value
        #         )
        #         entries.append(entry)
        
        # elif isinstance(node, ast.AnnAssign):  # for annotated variables
        #     if isinstance(node.target, ast.Name):
        #         name = node.target.id
        #         try:
        #             value = ast.unparse(node.value) if node.value else ''
        #         except Exception:
        #             value = ""
        #         body = lines[node.lineno - 1]
        #         entry = CodeEntry(
        #             name=name,
        #             type="variable",
        #             file_path=file_path,
        #             body=body,
        #             start_line=node.lineno,
        #             end_line=node.end_lineno,
        #             value=value
        #         )
        #         entries.append(entry)

        for child in ast.iter_child_nodes(node):
            visit(child, parent_class, parent_func)

    visit(tree)

    if entries:
        # 🔁 Call LLM summarizer here to enrich entries with structured summaries
        summaries = get_code_summary_from_llm(code)
        for entry in entries:
            if entry.name in summaries:
                # 🔁 You can replace docstring or add another field if preferred
                entry.llm_summary = summaries[entry.name]
    return entries

def generate_structured_text(entry: CodeEntry) -> str:
    return f"""
        {entry.type}: {entry.name}
        File: {entry.file_path}
        Docstring: {entry.docstring.strip()}
        Summary: {entry.llm_summary.strip()}
        Code: {entry.body.strip()}
    """

def get_code_summary_from_llm(code: str) -> str:
    system_prompt = "You generate short, structured summaries for Python code."

    user_prompt = f"""
        Summarize the following functions or classes into a JSON object.

        Each key must be the function/class name, and value a short summary of what it does and what the function/class does.
        You MUST respond with only valid JSON. No markdown, no extra text.

        Example format:
        {{
            "get_user_payload": "Verifies and decodes an OAuth2 token.",
            "UserSettings": "Defines user settings and preferences."
        }}

        {code}
    """

    response = bedrock_client.invoke_model(
        modelId='amazon.nova-pro-v1:0',
        body=json.dumps({
            "system": [{"text": system_prompt}],
            "messages": [
                {"role": "user", "content": [{"text": user_prompt}]},
                {"role": "assistant", "content": [{"text": "```json\n"}]},  # Prefill response
            ]
        }),
        contentType="application/json",
        accept="application/json"
    )

    model_response  = json.loads(response["body"].read())
    response_text: str = model_response["output"]["message"]["content"][0]["text"]
    trimmed = response_text.strip().removeprefix("```json").removesuffix("```").strip()
    return json.loads(trimmed)
    
def get_embeddings(entries: list[CodeEntry], project_name: str):

    texts = [generate_structured_text(entry) for entry in entries]
    embeddings = []
    for text in texts:
        # print(f"==>> text: {text}")
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps({"inputText": text})
        )
        embeddings.append(json.loads(response["body"].read())["embedding"])

        # make a request to the embedding API
        # response = requests.post("http://localhost:8000/embed", json={"text": text})
        # embeddings.append(response.json()["embedding"])

    vector_records = []
   
    for entry, vec in zip(entries, embeddings):
        key = str(uuid.uuid4())

        metadata = {
            "file_path": entry.file_path,
            "name": entry.name,
            "type": entry.type,
            "start_line": entry.start_line,
            "end_line": entry.end_line,
            "parent_class": entry.parent_class,
            "parent_function": entry.parent_function,
            "llm_summary": entry.llm_summary,
            "docstring": entry.docstring,
            "decorators": entry.decorators,
            "project_name": project_name,
        }
        vector_records.append({
            "key": key,
            "data": {"float32": vec},
            "metadata": metadata
        })
    return vector_records


def upload_vectors_to_s3(vector_records: list[dict]):
    s3vectors.put_vectors(
        vectorBucketName=VECTOR_BUCKET,
        indexName=VECTOR_INDEX,
        vectors=vector_records
    )

def upload_ast_json(repo_name: str, entries: list[CodeEntry]):
    
    classes = [asdict(entry) for entry in entries if entry.type == "class"]
    functions = [asdict(entry) for entry in entries if entry.type in {"function", "async_function"}]

    
    ast_data = {
        "classes": classes,
        "functions": functions,
    }
    ast_key = f"asts/{repo_name}.json"
    s3.put_object(
        Bucket=AST_BUCKET,
        Key=ast_key,
        Body=json.dumps(ast_data, indent=2),
        ContentType="application/json"
    )

def walk_directory_and_process(root_dir: str):
    all_vector_records = []
    all_ast_records = []

    project_name = root_dir.removeprefix("tmp/")
    print(f"==>> project_name: {project_name}")

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".py"):
                # print(f"==>> filename: {filename}")
                full_path = os.path.join(dirpath, filename)
                try:
                    entries = parse_python_ast(full_path)
                    if entries:
                        vector_records = get_embeddings(entries, project_name)
                        all_vector_records.extend(vector_records)
                        all_ast_records.extend(entries)
                    else:
                        print(f"⚠️ No classes or functions found in {full_path}")
                    print(f"✅ Processed {full_path}")
                except Exception as e:
                    # print(f"❌ Error in {full_path}: {e}")
                    raise e
    
    # upload_vectors_to_s3(all_vector_records)
    store.add(all_vector_records)
    upload_ast_json(project_name, all_ast_records)

# Example usage
if __name__ == "__main__":
    walk_directory_and_process("tmp/finance_service_agent")  # or any code directory
