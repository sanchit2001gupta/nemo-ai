import boto3
import json
from typing import Literal
from dataclasses import dataclass
from strands import tool
import os

s3_client = boto3.client('s3')

@dataclass
class FunctionEntry:
    """
    dataclass for function entry.
    """

    type: str
    name: str
    file_path: str
    body: str
    start_line: int
    end_line: int
    parent_function: str | None = None
    parent_class: str | None = None


@dataclass
class ClassEntry:
    """
    dataclass for class entry.
    """

    type: str
    name: str
    file_path: str
    body: str
    start_line: int
    end_line: int
    fields: str | None = None
    methods: str | None = None

class MemoryCodeIndex:
    def __init__(self, s3_bucket: str, s3_key: str):
        self.function_entries: list[FunctionEntry] = []
        self.class_entries: list[ClassEntry] = []

        self._load_entries_from_s3(s3_bucket, s3_key)

    def _load_entries_from_s3(self, bucket: str, key: str) -> None:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')
        ast_data  = json.loads(content)

        self.class_entries = [
            ClassEntry(
                type=entry["type"],
                name=entry["name"],
                file_path=entry["file_path"],
                body=entry["body"],
                start_line=entry["start_line"],
                end_line=entry["end_line"],
                fields=entry["fields"],
                methods=entry["methods"],
            )

            for entry in ast_data.get("classes", [])
        ]

        self.function_entries = [
            FunctionEntry(
                type=entry["type"],
                name=entry["name"],
                file_path=entry["file_path"],
                body=entry["body"],
                start_line=entry["start_line"],
                end_line=entry["end_line"],
                parent_function=entry["parent_function"],
                parent_class=entry["parent_class"],
            )

            for entry in ast_data.get("functions", [])
        ]

        # self.class_entries = [ClassEntry(**entry) for entry in ast_data.get("classes", [])]
        # self.function_entries = [FunctionEntry(**entry) for entry in ast_data.get("functions", [])]

    @tool
    def query_function(
        self, identifier: str, entry_type: Literal["function", "async_function", "class_method"] = "function"
    ) -> list[FunctionEntry]:
        """
        Retrieve function entries by exact name match from the code index.

        Use this tool when you know the function name and want to locate its definition(s) in the codebase. 
        Supports top-level functions, async functions, and class methods.

        Args:
            identifier (str): The exact name of the function to search for.
                Example: "authenticate_user"
            entry_type (Literal["function", "async_function", "class_method"], optional): 
                Type of function to query. Defaults to "function".
                - "function": Top-level synchronous function
                - "async_function": Top-level asynchronous function
                - "class_method": Method defined inside a class

        Returns:
            list[FunctionEntry]: Matching function entries, each containing:
                - type (str): Element type ("function", "async_function").
                - name (str): Function name.
                - file_path (str): Path to the file containing the function.
                - start_line (int): Start line of the function definition.
                - end_line (int): End line of the function definition.
                - parent_class (str | None): Parent class name if applicable.
                - parent_function (str | None): Parent function name if applicable.
                - body (str): Full function body as source code.

        Notes:
            - Performs exact match on function name (case-sensitive).
            - For semantic/natural language queries, use `query_vector_store`.
        """
        return [
            func for func in self.function_entries
            if func.name == identifier and (
                (entry_type == "function" and func.type in {"function", "async_function"} and not func.parent_class) or
                (entry_type == "async_function" and func.type == "async_function" and not func.parent_class) or
                (entry_type == "class_method" and func.parent_class)
            )
        ]

    @tool
    def query_class(self, identifier: str) -> list[ClassEntry]:
        """
        Retrieve class entries by exact name match from the code index.

        Use this tool when you know the class name and want to locate its definition(s) in the codebase. 
        Returns structural metadata including fields and methods.

        Args:
            identifier (str): The exact name of the class to search for.
                Example: "AuthService"

        Returns:
            list[ClassEntry]: Matching class entries, each containing:
                - type (str): Element type ("class").
                - name (str): Class name.
                - file_path (str): Path to the file containing the class.
                - start_line (int): Start line of the class definition.
                - end_line (int): End line of the class definition.
                - fields (str | None): Extracted class fields, if available.
                - methods (str | None): Extracted class methods, if available.
                - body (str): Full class body as source code.

        Notes:
            - Performs exact match on class name (case-sensitive).
            - For semantic/natural language discovery (e.g., "where is authentication done?"), use `query_vector_store`.
        """

        return [cls for cls in self.class_entries if cls.name == identifier]

