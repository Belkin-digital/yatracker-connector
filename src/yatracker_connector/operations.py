"""High-level operations built on top of TrackerClient."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence

from yandex_tracker_client import TrackerClient


def search_issues(
    client: TrackerClient,
    query: Optional[str] = None,
    filter_payload: Optional[Dict] = None,
    limit: int = 50,
) -> List:
    """Search issues via /issues/_search."""
    if not query and not filter_payload:
        raise ValueError("Provide either query or filter_payload")

    # Extract known parameters from filter_payload
    kwargs = {}
    if filter_payload:
        kwargs['queue'] = filter_payload.get('queue')
        kwargs['filter'] = {k: v for k, v in filter_payload.items() if k != 'queue'}
        if not kwargs['filter']:
            kwargs.pop('filter')

    issues = client.issues.find(query=query, per_page=limit, **kwargs)
    return list(issues)


def get_issue(client: TrackerClient, issue_key: str):
    """Fetch a single issue by key."""
    return client.issues[issue_key]


def list_comments(issue) -> List:
    """Return all comments for the issue."""
    return list(issue.comments.get_all())


def add_comment(issue, text: str, attachment_ids: Optional[Sequence[str]] = None):
    """Add a comment to the issue."""
    payload = {"text": text}
    if attachment_ids:
        payload["attachments"] = list(attachment_ids)
    return issue.comments.create(**payload)


def download_attachments(issue, target_dir: str | Path) -> List[Path]:
    """Download all attachments to target_dir."""
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)

    downloaded: List[Path] = []
    for attachment in issue.attachments.get_all():
        content = attachment.download()
        file_path = target / attachment.filename
        file_path.write_bytes(content)
        downloaded.append(file_path)
    return downloaded


def attach_file(issue, file_path: str | Path, filename: Optional[str] = None):
    """Attach a binary file to the issue."""
    path = Path(file_path)
    with path.open("rb") as handle:
        return issue.attachments.create(
            file=handle,
            filename=filename or path.name,
        )


def update_issue_fields(issue, **fields):
    """Patch issue attributes."""
    if not fields:
        raise ValueError("No fields to update")
    return issue.update(**fields)


def list_transitions(issue) -> List:
    """Return available transitions."""
    return list(issue.transitions.get_all())


def execute_transition(issue, transition_id: str):
    """Execute a transition by id."""
    transition = issue.transitions[transition_id]
    return transition.execute()


def list_queues(client: TrackerClient) -> List:
    """Return all available queues."""
    return list(client.queues.get_all())


def get_queue(client: TrackerClient, queue_key: str):
    """Get queue by key."""
    return client.queues[queue_key]


def list_queue_fields(client: TrackerClient, queue_key: str) -> List:
    """Return all fields for a specific queue."""
    queue = client.queues[queue_key]
    fields = queue.fields
    if isinstance(fields, list):
        return fields
    return list(fields.get_all())


def list_all_fields(client: TrackerClient) -> List:
    """Return all available fields in the system."""
    return list(client.fields.get_all())


def list_queue_issue_types(client: TrackerClient, queue_key: str) -> List:
    """Return all issue types for a specific queue."""
    queue = client.queues[queue_key]
    issue_types = queue.issuetypes
    # Check if it's already a list or needs to be converted
    if isinstance(issue_types, list):
        return issue_types
    return list(issue_types.get_all())


def list_all_issue_types(client: TrackerClient) -> List:
    """Return all available issue types in the system."""
    return list(client.issue_types.get_all())


def get_queue_workflows(client: TrackerClient, queue_key: str) -> List[Dict]:
    """Return workflows (business processes) for a specific queue.

    Returns a list of dicts with workflow details, issue types, and statuses.
    """
    queue = client.queues[queue_key]
    workflows_dict = queue.workflows

    if not workflows_dict or not isinstance(workflows_dict, dict):
        return []

    # Convert dict to list of workflow info
    result = []
    for workflow_id, issue_types in workflows_dict.items():
        # Get full workflow object to access steps/statuses
        try:
            workflow = client.workflows[workflow_id]
            workflow_info = {
                "workflow_id": workflow_id,
                "name": getattr(workflow, "name", ""),
                "issue_types": [],
                "steps": []
            }

            # Add issue type info
            if isinstance(issue_types, list):
                for issue_type in issue_types:
                    workflow_info["issue_types"].append({
                        "id": str(issue_type.id),
                        "key": getattr(issue_type, "key", ""),
                        "name": getattr(issue_type, "name", ""),
                    })

            # Add steps/statuses from workflow
            if hasattr(workflow, "steps"):
                steps = workflow.steps
                if isinstance(steps, list):
                    for step in steps:
                        step_info = {}

                        # Add status information
                        if "status" in step:
                            status_ref = step["status"]
                            # Load full status object to get name
                            try:
                                status = client.statuses[str(status_ref.id)]
                                step_info["status"] = {
                                    "id": str(status.id),
                                    "key": status.key,
                                    "name": status.name,
                                }
                            except Exception:
                                step_info["status"] = {
                                    "id": str(getattr(status_ref, "id", "")),
                                    "key": getattr(status_ref, "key", ""),
                                    "name": str(status_ref),
                                }

                        # Add available actions (transitions)
                        if "actions" in step:
                            step_info["actions"] = []
                            for action in step["actions"]:
                                action_info = {
                                    "id": action.get("id", ""),
                                    "name": action.get("name", ""),
                                }
                                # Add target status
                                if "target" in action:
                                    target_ref = action["target"]
                                    try:
                                        target = client.statuses[str(target_ref.id)]
                                        action_info["target_status"] = {
                                            "id": str(target.id),
                                            "key": target.key,
                                            "name": target.name,
                                        }
                                    except Exception:
                                        action_info["target_status"] = {
                                            "id": str(getattr(target_ref, "id", "")),
                                            "key": getattr(target_ref, "key", ""),
                                            "name": str(target_ref),
                                        }
                                step_info["actions"].append(action_info)

                        workflow_info["steps"].append(step_info)

            result.append(workflow_info)
        except Exception:
            # If we can't get the full workflow, just add basic info
            workflow_info = {
                "workflow_id": workflow_id,
                "issue_types": []
            }
            if isinstance(issue_types, list):
                for issue_type in issue_types:
                    workflow_info["issue_types"].append({
                        "id": str(issue_type.id),
                        "key": getattr(issue_type, "key", ""),
                        "name": getattr(issue_type, "name", ""),
                    })
            result.append(workflow_info)

    return result


def download_comment_attachments(comment, target_dir: str | Path) -> List[Path]:
    """Download all attachments from a comment to target_dir."""
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)

    downloaded: List[Path] = []
    if hasattr(comment, 'attachments'):
        for attachment in comment.attachments:
            content = attachment.download()
            file_path = target / attachment.filename
            file_path.write_bytes(content)
            downloaded.append(file_path)
    return downloaded


def add_comment_with_attachment(
    issue,
    text: str,
    file_path: Optional[str | Path] = None,
    filename: Optional[str] = None
):
    """Add a comment with an optional file attachment."""
    # First upload the file if provided
    attachment_ids = []
    if file_path:
        path = Path(file_path)
        with path.open("rb") as handle:
            attachment = issue.attachments.create(
                file=handle,
                filename=filename or path.name,
            )
            attachment_ids.append(attachment.id)

    # Then create the comment with attachment reference
    return add_comment(issue, text, attachment_ids=attachment_ids if attachment_ids else None)


__all__ = [
    "search_issues",
    "get_issue",
    "list_comments",
    "add_comment",
    "download_attachments",
    "attach_file",
    "update_issue_fields",
    "list_transitions",
    "execute_transition",
    "list_queues",
    "get_queue",
    "list_queue_fields",
    "list_all_fields",
    "list_queue_issue_types",
    "list_all_issue_types",
    "get_queue_workflows",
    "download_comment_attachments",
    "add_comment_with_attachment",
]
