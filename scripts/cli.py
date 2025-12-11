"""Simple CLI to exercise YaTracker Connector helpers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from rich.console import Console
from rich.table import Table

from yatracker_connector import (
    add_comment,
    attach_file,
    build_tracker_client,
    download_attachments,
    execute_transition,
    get_issue,
    list_comments,
    list_transitions,
    search_issues,
    update_issue_fields,
)

console = Console()


def _parse_filter(filter_json: str | None) -> Dict[str, Any]:
    if not filter_json:
        return {}
    return json.loads(filter_json)


def cmd_issues_list(args):
    client = build_tracker_client()
    payload = _parse_filter(args.filter)
    if args.queue:
        payload["queue"] = args.queue
    issues = search_issues(client, query=args.query, filter_payload=payload, limit=args.limit)

    table = Table("Key", "Summary", "Status", show_lines=False)
    for issue in issues:
        status = getattr(issue, "status", None)
        status_display = status.display if status else ""
        table.add_row(issue.key, getattr(issue, "summary", ""), status_display)

    console.print(table)


def cmd_comments_list(args):
    issue = get_issue(build_tracker_client(), args.issue)
    for comment in list_comments(issue):
        console.print(f"[bold]{comment.id}[/bold]: {comment.text}")


def cmd_comments_add(args):
    issue = get_issue(build_tracker_client(), args.issue)
    add_comment(issue, text=args.text)
    console.print("[green]Комментарий добавлен[/green]")


def cmd_attachments_download(args):
    issue = get_issue(build_tracker_client(), args.issue)
    paths = download_attachments(issue, args.target)
    for path in paths:
        console.print(f"Скачано: {path}")


def cmd_attachments_add(args):
    issue = get_issue(build_tracker_client(), args.issue)
    attach_file(issue, args.path)
    console.print("[green]Вложение загружено[/green]")


def cmd_issue_update(args):
    issue = get_issue(build_tracker_client(), args.issue)
    fields = dict(field.split("=", 1) for field in args.field)
    update_issue_fields(issue, **fields)
    console.print("[green]Поля обновлены[/green]")


def cmd_transition_list(args):
    issue = get_issue(build_tracker_client(), args.issue)
    transitions = list_transitions(issue)
    for transition in transitions:
        console.print(f"{transition.id}: {transition.display}")


def cmd_transition_execute(args):
    issue = get_issue(build_tracker_client(), args.issue)
    execute_transition(issue, args.transition_id)
    console.print("[green]Статус обновлён[/green]")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="YaTracker helper CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    issues = subparsers.add_parser("issues", help="Operations with issues")
    issues_sub = issues.add_subparsers(dest="subcommand", required=True)

    issues_list = issues_sub.add_parser("list", help="List issues")
    issues_list.add_argument("--queue")
    issues_list.add_argument("--query")
    issues_list.add_argument("--filter", help="JSON filter payload", default=None)
    issues_list.add_argument("--limit", type=int, default=20)
    issues_list.set_defaults(func=cmd_issues_list)

    issue_update = issues_sub.add_parser("update", help="Update issue fields")
    issue_update.add_argument("issue", help="Issue key, e.g. TEST-1")
    issue_update.add_argument(
        "--field",
        action="append",
        required=True,
        help="Field update in format name=value",
    )
    issue_update.set_defaults(func=cmd_issue_update)

    comments = subparsers.add_parser("comments", help="Work with comments")
    comments_sub = comments.add_subparsers(dest="subcommand", required=True)

    comments_list = comments_sub.add_parser("list")
    comments_list.add_argument("issue")
    comments_list.set_defaults(func=cmd_comments_list)

    comments_add = comments_sub.add_parser("add")
    comments_add.add_argument("issue")
    comments_add.add_argument("text")
    comments_add.set_defaults(func=cmd_comments_add)

    attachments = subparsers.add_parser("attachments", help="Handle attachments")
    attachments_sub = attachments.add_subparsers(dest="subcommand", required=True)

    attachments_download = attachments_sub.add_parser("download")
    attachments_download.add_argument("issue")
    attachments_download.add_argument("--target", default="downloads", type=Path)
    attachments_download.set_defaults(func=cmd_attachments_download)

    attachments_add = attachments_sub.add_parser("add")
    attachments_add.add_argument("issue")
    attachments_add.add_argument("--path", required=True, type=Path)
    attachments_add.set_defaults(func=cmd_attachments_add)

    transitions = subparsers.add_parser("transitions", help="Move issue through workflow")
    transitions_sub = transitions.add_subparsers(dest="subcommand", required=True)

    transitions_list = transitions_sub.add_parser("list")
    transitions_list.add_argument("issue")
    transitions_list.set_defaults(func=cmd_transition_list)

    transitions_exec = transitions_sub.add_parser("execute")
    transitions_exec.add_argument("issue")
    transitions_exec.add_argument("transition_id")
    transitions_exec.set_defaults(func=cmd_transition_execute)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
