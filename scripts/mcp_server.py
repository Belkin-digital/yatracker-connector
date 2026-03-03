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
import re
import sys
import codecs
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
    create_worklog,
    delete_worklog,
    download_attachments,
    download_comment_attachments,
    execute_transition,
    get_issue,
    get_queue,
    get_queue_workflows,
    get_worklogs_report,
    list_all_fields,
    list_all_issue_types,
    list_comments,
    list_issue_worklogs,
    list_queue_fields,
    list_queue_issue_types,
    list_queues,
    list_transitions,
    search_issues,
    search_worklogs,
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

_REFERENCE_NAME_RE = re.compile(r"\\(b'(?P<name>[^']*)'\\)")


def _decode_python_bytes_escapes_to_utf8(text: str) -> str:
    """
    Convert strings like '\\xd0\\x90\\xd0\\xbb...' (repr of UTF-8 bytes)
    into a proper unicode string.
    """
    try:
        # 1) Interpret \xNN escapes into 0-255 codepoints
        # 2) Convert those codepoints back to bytes via latin-1
        # 3) Decode as UTF-8
        return codecs.decode(text, "unicode_escape").encode("latin-1").decode("utf-8")
    except Exception:
        return text


def _humanize_reference(value: Any) -> str:
    """Best-effort human-readable label for Tracker reference objects."""
    if value is None:
        return ""

    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except Exception:
            return value.decode(errors="replace")

    # Many yandex-tracker-client objects expose .display
    display = getattr(value, "display", None)
    if display:
        return str(display)

    s = str(value)

    # Often looks like: "<Reference to Users/b'8000...' (b'\\xd0...\\xd0...')>"
    m = _REFERENCE_NAME_RE.search(s)
    if m:
        return _decode_python_bytes_escapes_to_utf8(m.group("name"))

    return s


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
            name="yatracker_download_comment_attachments",
            description="Download all attachments from issue comments to a target directory (optionally only one comment).",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Issue key (e.g., CRM-19)",
                    },
                    "comment_id": {
                        "type": "string",
                        "description": "Optional comment id (as string). If omitted, downloads from all comments.",
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
        Tool(
            name="yatracker_list_worklogs",
            description="List all worklog (time tracking) entries for a specific issue.",
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
            name="yatracker_create_worklog",
            description="Create a new worklog (time tracking) entry for an issue.",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Issue key (e.g., ZEL-80)",
                    },
                    "duration": {
                        "type": "string",
                        "description": "Time spent as ISO 8601 duration (e.g., 'PT2H30M' = 2h 30min, 'PT1H' = 1h, 'P1D' = 1 day = 8h)",
                    },
                    "start": {
                        "type": "string",
                        "description": "Work date in YYYY-MM-DD format (default: today)",
                    },
                    "comment": {
                        "type": "string",
                        "description": "Optional comment describing the work done",
                    },
                },
                "required": ["issue_key", "duration"],
            },
        ),
        Tool(
            name="yatracker_delete_worklog",
            description="Delete a worklog (time tracking) entry for an issue. Use for corrections when a wrong record was logged.",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Issue key (e.g., ZEL-80)",
                    },
                    "worklog_id": {
                        "type": "string",
                        "description": "Worklog record ID to delete (e.g., 477)",
                    },
                },
                "required": ["issue_key", "worklog_id"],
            },
        ),
        Tool(
            name="yatracker_get_worklogs_report",
            description="Generate a worklogs report with flexible grouping and aggregation. Returns time spent by users on issues.",
            inputSchema={
                "type": "object",
                "properties": {
                    "from_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                    },
                    "to_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                    },
                    "author": {
                        "type": "string",
                        "description": "User ID or username to filter by (optional, omit for all authors)",
                    },
                    "queues": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of queue keys to filter by (e.g., ['CRM', 'DEV']). Optional, omit for all queues.",
                    },
                    "group_by": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["date", "issue", "queue", "status", "author"],
                        },
                        "description": "Grouping levels in order of nesting. Valid: date, issue, queue, status, author. Optional.",
                    },
                    "details": {
                        "type": "boolean",
                        "description": "If true, include detailed records in the deepest group. Default: false.",
                        "default": False,
                    },
                },
                "required": ["from_date", "to_date"],
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
                attachments = []
                if hasattr(comment, "attachments") and comment.attachments:
                    for a in comment.attachments:
                        attachments.append(
                            {
                                "id": str(getattr(a, "id", "")),
                                "filename": getattr(a, "filename", "") or getattr(a, "name", ""),
                            }
                        )
                results.append({
                    "id": str(comment.id),
                    "text": comment.text,
                    "createdAt": str(getattr(comment, "createdAt", "")),
                    "attachments": attachments,
                })

            return [TextContent(
                type="text",
                text=json.dumps(results, ensure_ascii=False, indent=2)
            )]

        elif name == "yatracker_download_comment_attachments":
            issue_key = arguments["issue_key"]
            comment_id = arguments.get("comment_id")
            target_dir = arguments.get("target_dir", "./downloads")

            issue = get_issue(client, issue_key)
            comments = list_comments(issue)

            downloaded_paths = []
            if comment_id:
                selected = None
                for c in comments:
                    if str(getattr(c, "id", "")) == str(comment_id):
                        selected = c
                        break
                if not selected:
                    return [TextContent(type="text", text=f"Comment {comment_id} not found for {issue_key}")]
                downloaded_paths.extend(download_comment_attachments(selected, Path(target_dir) / issue_key / str(comment_id)))
            else:
                for c in comments:
                    downloaded_paths.extend(download_comment_attachments(c, Path(target_dir) / issue_key / str(getattr(c, 'id', ''))))

            results = [str(p) for p in downloaded_paths]
            return [TextContent(
                type="text",
                text=f"Скачано {len(results)} файлов из комментариев:\n" + ("\n".join(results) if results else "")
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
                    "lead": _humanize_reference(getattr(queue, "lead", None)),
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

        elif name == "yatracker_list_worklogs":
            issue_key = arguments["issue_key"]
            worklogs = list_issue_worklogs(client, issue_key)

            return [TextContent(
                type="text",
                text=json.dumps(worklogs, ensure_ascii=False, indent=2)
            )]

        elif name == "yatracker_create_worklog":
            issue_key = arguments["issue_key"]
            duration = arguments["duration"]
            start = arguments.get("start")
            comment = arguments.get("comment")

            worklog = create_worklog(issue_key, duration=duration, start=start, comment=comment)

            return [TextContent(
                type="text",
                text=f"Worklog создан для {issue_key}:\n" + json.dumps(worklog, ensure_ascii=False, indent=2)
            )]

        elif name == "yatracker_delete_worklog":
            issue_key = arguments["issue_key"]
            worklog_id = arguments["worklog_id"]

            delete_worklog(issue_key, worklog_id)

            return [TextContent(
                type="text",
                text=f"Запись worklog {worklog_id} удалена из задачи {issue_key}"
            )]

        elif name == "yatracker_get_worklogs_report":
            from_date = arguments["from_date"]
            to_date = arguments["to_date"]
            author = arguments.get("author")
            queues = arguments.get("queues")
            group_by = arguments.get("group_by")
            details = arguments.get("details", False)

            report = get_worklogs_report(
                client,
                from_date=from_date,
                to_date=to_date,
                author=author,
                queues=queues,
                group_by=group_by,
                details=details,
            )

            return [TextContent(
                type="text",
                text=json.dumps(report, ensure_ascii=False, indent=2)
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
