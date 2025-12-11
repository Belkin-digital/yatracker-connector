#!/usr/bin/env python3.11
"""MCP Server for YaTracker Connector.

Provides tools for working with Yandex Tracker:
- Search and list issues
- Get issue details
- Add comments
- Update issue fields
- Execute transitions (status changes)
- Manage attachments
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Load environment variables from .env file
from dotenv import load_dotenv

# Get the project root directory
project_root = Path(__file__).parent.parent
dotenv_path = project_root / ".env"

# Load .env file if it exists
if dotenv_path.exists():
    load_dotenv(dotenv_path)

# Add src to path
sys.path.insert(0, str(project_root / "src"))

from yatracker_connector import (
    add_comment,
    add_comment_with_attachment,
    attach_file,
    build_tracker_client,
    download_attachments,
    download_comment_attachments,
    execute_transition,
    get_issue,
    get_queue,
    get_queue_workflows,
    list_all_fields,
    list_all_issue_types,
    list_comments,
    list_queue_fields,
    list_queue_issue_types,
    list_queues,
    list_transitions,
    search_issues,
    update_issue_fields,
)

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("Error: mcp package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)


# Initialize MCP server
app = Server("yatracker-connector")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available YaTracker tools."""
    return [
        Tool(
            name="yatracker_search_issues",
            description="Search and list issues from YaTracker queue. Returns key, summary, and status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "queue": {
                        "type": "string",
                        "description": "Queue key (e.g., CRM, DEV, MGT)",
                    },
                    "query": {
                        "type": "string",
                        "description": "Optional search query string",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of issues to return (default: 50)",
                        "default": 50,
                    },
                },
                "required": ["queue"],
            },
        ),
        Tool(
            name="yatracker_get_issue",
            description="Get detailed information about a specific issue by key.",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Issue key (e.g., CRM-19)",
                    },
                },
                "required": ["issue_key"],
            },
        ),
        Tool(
            name="yatracker_create_issue",
            description="Create a new issue in a queue.",
            inputSchema={
                "type": "object",
                "properties": {
                    "queue": {
                        "type": "string",
                        "description": "Queue key (e.g., CRM, DEV)",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Issue title/summary",
                    },
                    "description": {
                        "type": "string",
                        "description": "Issue description (optional)",
                    },
                },
                "required": ["queue", "summary"],
            },
        ),
        Tool(
            name="yatracker_list_comments",
            description="List all comments for an issue.",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Issue key (e.g., CRM-19)",
                    },
                },
                "required": ["issue_key"],
            },
        ),
        Tool(
            name="yatracker_add_comment",
            description="Add a comment to an issue.",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Issue key (e.g., CRM-19)",
                    },
                    "text": {
                        "type": "string",
                        "description": "Comment text",
                    },
                },
                "required": ["issue_key", "text"],
            },
        ),
        Tool(
            name="yatracker_update_issue",
            description="Update issue fields (e.g., summary, description, etc.).",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Issue key (e.g., CRM-19)",
                    },
                    "fields": {
                        "type": "object",
                        "description": "Fields to update as key-value pairs (e.g., {'summary': 'New title'})",
                    },
                },
                "required": ["issue_key", "fields"],
            },
        ),
        Tool(
            name="yatracker_list_transitions",
            description="List available status transitions for an issue.",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Issue key (e.g., CRM-19)",
                    },
                },
                "required": ["issue_key"],
            },
        ),
        Tool(
            name="yatracker_execute_transition",
            description="Execute a status transition on an issue.",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Issue key (e.g., CRM-19)",
                    },
                    "transition_id": {
                        "type": "string",
                        "description": "Transition ID to execute",
                    },
                },
                "required": ["issue_key", "transition_id"],
            },
        ),
        Tool(
            name="yatracker_download_attachments",
            description="Download all attachments from an issue to a target directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Issue key (e.g., CRM-19)",
                    },
                    "target_dir": {
                        "type": "string",
                        "description": "Target directory path (default: ./downloads)",
                        "default": "./downloads",
                    },
                },
                "required": ["issue_key"],
            },
        ),
        Tool(
            name="yatracker_attach_file",
            description="Attach a file to an issue.",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Issue key (e.g., CRM-19)",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to file to attach",
                    },
                },
                "required": ["issue_key", "file_path"],
            },
        ),
        Tool(
            name="yatracker_list_queues",
            description="List all available queues in the system.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="yatracker_list_queue_fields",
            description="List all fields for a specific queue.",
            inputSchema={
                "type": "object",
                "properties": {
                    "queue": {
                        "type": "string",
                        "description": "Queue key (e.g., CRM, DEV)",
                    },
                },
                "required": ["queue"],
            },
        ),
        Tool(
            name="yatracker_list_all_fields",
            description="List all available fields in the system.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="yatracker_list_queue_issue_types",
            description="List all issue types for a specific queue.",
            inputSchema={
                "type": "object",
                "properties": {
                    "queue": {
                        "type": "string",
                        "description": "Queue key (e.g., CRM, DEV)",
                    },
                },
                "required": ["queue"],
            },
        ),
        Tool(
            name="yatracker_get_queue_workflows",
            description="Get workflows (business processes/status graph) for a specific queue.",
            inputSchema={
                "type": "object",
                "properties": {
                    "queue": {
                        "type": "string",
                        "description": "Queue key (e.g., CRM, DEV)",
                    },
                },
                "required": ["queue"],
            },
        ),
        Tool(
            name="yatracker_add_comment_with_attachment",
            description="Add a comment to an issue with an optional file attachment.",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Issue key (e.g., CRM-19)",
                    },
                    "text": {
                        "type": "string",
                        "description": "Comment text",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Optional path to file to attach",
                    },
                },
                "required": ["issue_key", "text"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    try:
        client = build_tracker_client()

        if name == "yatracker_search_issues":
            queue = arguments["queue"]
            query = arguments.get("query")
            limit = arguments.get("limit", 50)

            filter_payload = {"queue": queue}
            issues = search_issues(client, query=query, filter_payload=filter_payload, limit=limit)

            results = []
            for issue in issues:
                status = getattr(issue, "status", None)
                status_display = status.display if status else ""
                results.append({
                    "key": issue.key,
                    "summary": getattr(issue, "summary", ""),
                    "status": status_display,
                })

            return [TextContent(
                type="text",
                text=json.dumps(results, ensure_ascii=False, indent=2)
            )]

        elif name == "yatracker_get_issue":
            issue_key = arguments["issue_key"]
            issue = get_issue(client, issue_key)

            status = getattr(issue, "status", None)
            result = {
                "key": issue.key,
                "summary": getattr(issue, "summary", ""),
                "description": getattr(issue, "description", ""),
                "status": status.display if status else "",
                "createdAt": str(getattr(issue, "createdAt", "")),
                "updatedAt": str(getattr(issue, "updatedAt", "")),
            }

            return [TextContent(
                type="text",
                text=json.dumps(result, ensure_ascii=False, indent=2)
            )]

        elif name == "yatracker_create_issue":
            queue = arguments["queue"]
            summary = arguments["summary"]
            description = arguments.get("description", "")

            issue = client.issues.create(
                queue=queue,
                summary=summary,
                description=description
            )

            result = {
                "key": issue.key,
                "summary": issue.summary,
                "status": issue.status.display,
            }

            return [TextContent(
                type="text",
                text=f"Создан лид: {issue.key}\n" + json.dumps(result, ensure_ascii=False, indent=2)
            )]

        elif name == "yatracker_list_comments":
            issue_key = arguments["issue_key"]
            issue = get_issue(client, issue_key)
            comments = list_comments(issue)

            results = []
            for comment in comments:
                results.append({
                    "id": str(comment.id),
                    "text": comment.text,
                    "createdAt": str(getattr(comment, "createdAt", "")),
                })

            return [TextContent(
                type="text",
                text=json.dumps(results, ensure_ascii=False, indent=2)
            )]

        elif name == "yatracker_add_comment":
            issue_key = arguments["issue_key"]
            text = arguments["text"]

            issue = get_issue(client, issue_key)
            comment = add_comment(issue, text)

            return [TextContent(
                type="text",
                text=f"Комментарий добавлен к {issue_key}: {comment.id}"
            )]

        elif name == "yatracker_update_issue":
            issue_key = arguments["issue_key"]
            fields = arguments["fields"]

            issue = get_issue(client, issue_key)
            update_issue_fields(issue, **fields)

            return [TextContent(
                type="text",
                text=f"Поля обновлены для {issue_key}"
            )]

        elif name == "yatracker_list_transitions":
            issue_key = arguments["issue_key"]
            issue = get_issue(client, issue_key)
            transitions = list_transitions(issue)

            results = []
            for transition in transitions:
                results.append({
                    "id": transition.id,
                    "display": transition.display,
                })

            return [TextContent(
                type="text",
                text=json.dumps(results, ensure_ascii=False, indent=2)
            )]

        elif name == "yatracker_execute_transition":
            issue_key = arguments["issue_key"]
            transition_id = arguments["transition_id"]

            issue = get_issue(client, issue_key)
            execute_transition(issue, transition_id)

            return [TextContent(
                type="text",
                text=f"Статус обновлён для {issue_key}"
            )]

        elif name == "yatracker_download_attachments":
            issue_key = arguments["issue_key"]
            target_dir = arguments.get("target_dir", "./downloads")

            issue = get_issue(client, issue_key)
            paths = download_attachments(issue, target_dir)

            results = [str(p) for p in paths]
            return [TextContent(
                type="text",
                text=f"Скачано {len(paths)} файлов:\n" + "\n".join(results)
            )]

        elif name == "yatracker_attach_file":
            issue_key = arguments["issue_key"]
            file_path = arguments["file_path"]

            issue = get_issue(client, issue_key)
            attach_file(issue, file_path)

            return [TextContent(
                type="text",
                text=f"Вложение загружено в {issue_key}"
            )]

        elif name == "yatracker_list_queues":
            queues = list_queues(client)

            results = []
            for queue in queues:
                results.append({
                    "key": queue.key,
                    "name": getattr(queue, "name", ""),
                    "lead": str(getattr(queue, "lead", "")),
                })

            return [TextContent(
                type="text",
                text=json.dumps(results, ensure_ascii=False, indent=2)
            )]

        elif name == "yatracker_list_queue_fields":
            queue = arguments["queue"]
            fields = list_queue_fields(client, queue)

            results = []
            for field in fields:
                results.append({
                    "id": field.id,
                    "key": getattr(field, "key", ""),
                    "name": getattr(field, "name", ""),
                    "type": str(getattr(field, "schema", {}).get("type", "")),
                })

            return [TextContent(
                type="text",
                text=json.dumps(results, ensure_ascii=False, indent=2)
            )]

        elif name == "yatracker_list_all_fields":
            fields = list_all_fields(client)

            results = []
            for field in fields:
                results.append({
                    "id": field.id,
                    "key": getattr(field, "key", ""),
                    "name": getattr(field, "name", ""),
                    "type": str(getattr(field, "schema", {}).get("type", "")),
                })

            return [TextContent(
                type="text",
                text=json.dumps(results, ensure_ascii=False, indent=2)
            )]

        elif name == "yatracker_list_queue_issue_types":
            queue = arguments["queue"]
            issue_types = list_queue_issue_types(client, queue)

            results = []
            for issue_type in issue_types:
                results.append({
                    "id": issue_type.id,
                    "key": getattr(issue_type, "key", ""),
                    "name": getattr(issue_type, "name", ""),
                })

            return [TextContent(
                type="text",
                text=json.dumps(results, ensure_ascii=False, indent=2)
            )]

        elif name == "yatracker_get_queue_workflows":
            queue = arguments["queue"]
            workflows = get_queue_workflows(client, queue)

            return [TextContent(
                type="text",
                text=json.dumps(workflows, ensure_ascii=False, indent=2)
            )]

        elif name == "yatracker_add_comment_with_attachment":
            issue_key = arguments["issue_key"]
            text = arguments["text"]
            file_path = arguments.get("file_path")

            issue = get_issue(client, issue_key)
            comment = add_comment_with_attachment(issue, text, file_path=file_path)

            return [TextContent(
                type="text",
                text=f"Комментарий добавлен к {issue_key}: {comment.id}"
            )]

        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
