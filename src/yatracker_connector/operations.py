"""High-level operations built on top of TrackerClient."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import requests
from yandex_tracker_client import TrackerClient

from .config import get_settings


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
        # yandex-tracker-client determines filename from the file object; older versions
        # do not accept a separate "filename" kwarg.
        return issue.attachments.create(file=handle)


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
            # See attach_file(): older yandex-tracker-client versions don't accept "filename".
            attachment = issue.attachments.create(file=handle)
            attachment_ids.append(attachment.id)

    # Then create the comment with attachment reference
    return add_comment(issue, text, attachment_ids=attachment_ids if attachment_ids else None)


# =============================================================================
# Worklog (Time Tracking) Functions
# =============================================================================

def parse_iso_duration(duration: str) -> float:
    """Parse ISO 8601 duration string to hours.
    
    Supports formats like:
    - P3W (3 weeks)
    - P1D (1 day)
    - PT2H (2 hours)
    - PT30M (30 minutes)
    - PT2H30M (2 hours 30 minutes)
    - P1DT4H30M (1 day 4 hours 30 minutes)
    - P1W2DT3H4M5S (1 week 2 days 3 hours 4 minutes 5 seconds)
    """
    if not duration:
        return 0.0
    
    # ISO 8601 duration pattern
    pattern = r'^P(?:(\d+)W)?(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$'
    match = re.match(pattern, duration.upper())
    
    if not match:
        return 0.0
    
    weeks = int(match.group(1) or 0)
    years = int(match.group(2) or 0)
    months = int(match.group(3) or 0)
    days = int(match.group(4) or 0)
    hours = int(match.group(5) or 0)
    minutes = int(match.group(6) or 0)
    seconds = float(match.group(7) or 0)
    
    # Convert everything to hours
    # Assumptions: 1 week = 40 work hours, 1 day = 8 work hours
    # 1 year = 52 weeks, 1 month = 4 weeks (approximation)
    total_hours = (
        years * 52 * 40 +
        months * 4 * 40 +
        weeks * 40 +
        days * 8 +
        hours +
        minutes / 60 +
        seconds / 3600
    )
    
    return round(total_hours, 2)


def _get_api_headers() -> Dict[str, str]:
    """Get headers for direct API requests."""
    settings = get_settings()
    headers = {
        "Authorization": f"OAuth {settings.token}",
        "Content-Type": "application/json",
    }
    if settings.org_id:
        headers["X-Org-ID"] = settings.org_id
    if settings.cloud_org_id:
        headers["X-Cloud-Org-ID"] = settings.cloud_org_id
    return headers


def _get_api_base_url() -> str:
    """Get base API URL."""
    settings = get_settings()
    return settings.api_url


def search_worklogs(
    client: TrackerClient,
    author: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    per_page: int = 100,
    max_pages: int = 100,
) -> List[Dict[str, Any]]:
    """Search worklogs by author and/or date range.
    
    Filters by worklog START date (actual work date), not by record creation date.
    
    Args:
        client: TrackerClient instance (used for consistency, actual request is direct)
        author: User ID or username (optional)
        from_date: Start date in YYYY-MM-DD format - filters by work date (optional)
        to_date: End date in YYYY-MM-DD format - filters by work date (optional)
        per_page: Number of records per page (default: 100, max: 100)
        max_pages: Maximum pages to fetch (default: 100, for safety)
    
    Returns:
        List of worklog records with parsed data, filtered by work date (start field)
    """
    base_url = _get_api_base_url()
    headers = _get_api_headers()
    
    # Build request body
    # Note: API only supports filtering by createdAt, not by start (work date)
    # We expand createdAt range and filter by start on client side
    body: Dict[str, Any] = {}
    
    if author:
        body["createdBy"] = author
    
    # Expand createdAt range to catch records created later than work date
    # People often log work days/weeks after the actual work
    if from_date or to_date:
        body["createdAt"] = {}
        if from_date:
            # Use from_date as-is for createdAt (records can't be created before work)
            body["createdAt"]["from"] = f"{from_date}T00:00:00.000+0000"
        if to_date:
            # Expand to_date by 90 days to catch late entries
            from datetime import timedelta
            to_dt = datetime.strptime(to_date, "%Y-%m-%d")
            expanded_to = to_dt + timedelta(days=90)
            body["createdAt"]["to"] = f"{expanded_to.strftime('%Y-%m-%d')}T23:59:59.999+0000"
    
    # Fetch all pages
    all_worklogs = []
    page = 1
    
    while page <= max_pages:
        # Make POST request to /v3/worklog/_search with pagination
        url = f"{base_url}/worklog/_search?perPage={per_page}&page={page}"
        response = requests.post(url, json=body, headers=headers)
        response.raise_for_status()
        
        worklogs = response.json()
        
        if not worklogs:
            break
        
        all_worklogs.extend(worklogs)
        
        # If we got fewer than per_page, we've reached the end
        if len(worklogs) < per_page:
            break
        
        page += 1
    
    worklogs = all_worklogs
    
    # Parse and normalize worklog data
    results = []
    for wl in worklogs:
        issue_data = wl.get("issue", {})
        created_by = wl.get("createdBy", {})
        
        # Parse start date
        start_str = wl.get("start", "")
        worklog_date = ""
        if start_str:
            try:
                dt = datetime.fromisoformat(start_str.replace("+0000", "+00:00"))
                worklog_date = dt.strftime("%Y-%m-%d")
            except (ValueError, AttributeError):
                worklog_date = start_str[:10] if len(start_str) >= 10 else start_str
        
        results.append({
            "id": wl.get("id"),
            "issue_key": issue_data.get("key", ""),
            "issue_summary": issue_data.get("display", ""),
            "author_id": created_by.get("id", ""),
            "author_display": created_by.get("display", ""),
            "worklog_date": worklog_date,
            "duration_raw": wl.get("duration", ""),
            "hours": parse_iso_duration(wl.get("duration", "")),
            "comment": wl.get("comment", ""),
            "created_at": wl.get("createdAt", ""),
        })
    
    # Filter by work date (start field) on client side
    if from_date:
        results = [r for r in results if r["worklog_date"] >= from_date]
    if to_date:
        results = [r for r in results if r["worklog_date"] <= to_date]
    
    return results


def list_issue_worklogs(
    client: TrackerClient,
    issue_key: str,
) -> List[Dict[str, Any]]:
    """Get all worklogs for a specific issue.
    
    Args:
        client: TrackerClient instance
        issue_key: Issue key (e.g., CRM-24)
    
    Returns:
        List of worklog records
    """
    base_url = _get_api_base_url()
    headers = _get_api_headers()
    
    url = f"{base_url}/issues/{issue_key}/worklog"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    worklogs = response.json()
    
    results = []
    for wl in worklogs:
        issue_data = wl.get("issue", {})
        created_by = wl.get("createdBy", {})
        
        start_str = wl.get("start", "")
        worklog_date = ""
        if start_str:
            try:
                dt = datetime.fromisoformat(start_str.replace("+0000", "+00:00"))
                worklog_date = dt.strftime("%Y-%m-%d")
            except (ValueError, AttributeError):
                worklog_date = start_str[:10] if len(start_str) >= 10 else start_str
        
        results.append({
            "id": wl.get("id"),
            "issue_key": issue_data.get("key", issue_key),
            "issue_summary": issue_data.get("display", ""),
            "author_id": created_by.get("id", ""),
            "author_display": created_by.get("display", ""),
            "worklog_date": worklog_date,
            "duration_raw": wl.get("duration", ""),
            "hours": parse_iso_duration(wl.get("duration", "")),
            "comment": wl.get("comment", ""),
            "created_at": wl.get("createdAt", ""),
        })
    
    return results


def create_worklog(
    issue_key: str,
    duration: str,
    start: Optional[str] = None,
    comment: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new worklog entry for an issue.

    Args:
        issue_key: Issue key (e.g., ZEL-80)
        duration: Time spent as ISO 8601 duration string (e.g., "PT2H30M", "PT1H", "P1D")
        start: Work date in YYYY-MM-DD format (default: today)
        comment: Optional comment for the worklog entry

    Returns:
        Created worklog record dict with id, hours, worklog_date, etc.
    """
    base_url = _get_api_base_url()
    headers = _get_api_headers()

    if start is None:
        start = datetime.now().strftime("%Y-%m-%d")

    body: Dict[str, Any] = {
        "start": f"{start}T00:00:00.000+0000",
        "duration": duration,
    }
    if comment:
        body["comment"] = comment

    url = f"{base_url}/issues/{issue_key}/worklog"
    response = requests.post(url, json=body, headers=headers)
    response.raise_for_status()

    wl = response.json()
    created_by = wl.get("createdBy", {})
    start_str = wl.get("start", "")
    worklog_date = ""
    if start_str:
        try:
            dt = datetime.fromisoformat(start_str.replace("+0000", "+00:00"))
            worklog_date = dt.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            worklog_date = start_str[:10] if len(start_str) >= 10 else start_str

    return {
        "id": wl.get("id"),
        "issue_key": wl.get("issue", {}).get("key", issue_key),
        "author_id": created_by.get("id", ""),
        "author_display": created_by.get("display", ""),
        "worklog_date": worklog_date,
        "duration_raw": wl.get("duration", ""),
        "hours": parse_iso_duration(wl.get("duration", "")),
        "comment": wl.get("comment", ""),
        "created_at": wl.get("createdAt", ""),
    }


def delete_worklog(issue_key: str, worklog_id: Union[int, str]) -> None:
    """Delete a worklog entry by issue key and worklog ID.

    Args:
        issue_key: Issue key (e.g., ZEL-80)
        worklog_id: Worklog record ID (numeric)
    """
    base_url = _get_api_base_url()
    headers = _get_api_headers()

    url = f"{base_url}/issues/{issue_key}/worklog/{worklog_id}"
    response = requests.delete(url, headers=headers)
    response.raise_for_status()


def _get_issue_status(client: TrackerClient, issue_key: str) -> str:
    """Get current status of an issue."""
    try:
        issue = get_issue(client, issue_key)
        status = getattr(issue, "status", None)
        return status.display if status else ""
    except Exception:
        return ""


def _extract_queue(issue_key: str) -> str:
    """Extract queue key from issue key (e.g., CRM-24 -> CRM)."""
    if "-" in issue_key:
        return issue_key.split("-")[0]
    return issue_key


def get_worklogs_report(
    client: TrackerClient,
    from_date: str,
    to_date: str,
    author: Optional[str] = None,
    queues: Optional[List[str]] = None,
    group_by: Optional[List[str]] = None,
    details: bool = False,
) -> Dict[str, Any]:
    """Generate worklogs report with flexible grouping.
    
    Args:
        client: TrackerClient instance
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        author: User ID/username to filter by (optional, None = all authors)
        queues: List of queue keys to filter by (optional, None = all queues)
        group_by: List of grouping levels in order of nesting.
                  Valid values: 'date', 'issue', 'queue', 'status', 'author'
        details: If True, include detailed records in the deepest group level
    
    Returns:
        Report dictionary with groups or records and totals
    """
    # Fetch worklogs
    worklogs = search_worklogs(client, author=author, from_date=from_date, to_date=to_date)
    
    # Filter by queues if specified
    if queues:
        queues_upper = [q.upper() for q in queues]
        worklogs = [
            wl for wl in worklogs 
            if _extract_queue(wl["issue_key"]).upper() in queues_upper
        ]
    
    # Add queue and status to each worklog
    issue_statuses: Dict[str, str] = {}  # Cache for issue statuses
    for wl in worklogs:
        wl["queue"] = _extract_queue(wl["issue_key"])
        
        # Get status (with caching)
        issue_key = wl["issue_key"]
        if issue_key not in issue_statuses:
            issue_statuses[issue_key] = _get_issue_status(client, issue_key)
        wl["status"] = issue_statuses[issue_key]
    
    # Calculate total hours
    total_hours = round(sum(wl["hours"] for wl in worklogs), 2)
    
    # Build filter info
    filter_info = {
        "period": {"from": from_date, "to": to_date},
        "author": author,
        "queues": queues,
    }
    
    # If no grouping, return flat list
    if not group_by:
        return {
            "records": worklogs,
            "total_hours": total_hours,
            "filter": filter_info,
        }
    
    # Validate group_by values
    valid_groups = {"date", "issue", "queue", "status", "author"}
    for g in group_by:
        if g not in valid_groups:
            raise ValueError(f"Invalid group_by value: {g}. Valid: {valid_groups}")
    
    # Build grouped result
    def get_group_key(wl: Dict, group_type: str) -> str:
        if group_type == "date":
            return wl["worklog_date"]
        elif group_type == "issue":
            return wl["issue_key"]
        elif group_type == "queue":
            return wl["queue"]
        elif group_type == "status":
            return wl["status"]
        elif group_type == "author":
            return wl["author_id"]
        return ""
    
    def get_group_display(wl: Dict, group_type: str) -> Dict[str, str]:
        """Get display fields for a group."""
        if group_type == "date":
            return {"date": wl["worklog_date"]}
        elif group_type == "issue":
            return {"issue_key": wl["issue_key"], "issue_summary": wl["issue_summary"]}
        elif group_type == "queue":
            return {"queue": wl["queue"]}
        elif group_type == "status":
            return {"status": wl["status"]}
        elif group_type == "author":
            return {"author_id": wl["author_id"], "author_display": wl["author_display"]}
        return {}
    
    def build_groups(
        records: List[Dict],
        group_levels: List[str],
        current_level: int = 0,
        used_groups: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Recursively build nested group structure."""
        if used_groups is None:
            used_groups = []
        
        if current_level >= len(group_levels):
            # Deepest level - return records if details=True, otherwise nothing
            if details:
                # Filter out fields that are redundant due to grouping
                filtered_records = []
                for rec in records:
                    filtered_rec = {"hours": rec["hours"]}
                    
                    # Only include fields not covered by grouping
                    if "date" not in used_groups:
                        filtered_rec["worklog_date"] = rec["worklog_date"]
                    if "issue" not in used_groups:
                        filtered_rec["issue_key"] = rec["issue_key"]
                        filtered_rec["issue_summary"] = rec["issue_summary"]
                    if "queue" not in used_groups:
                        filtered_rec["queue"] = rec["queue"]
                    if "status" not in used_groups:
                        filtered_rec["status"] = rec["status"]
                    if "author" not in used_groups:
                        filtered_rec["author_id"] = rec["author_id"]
                        filtered_rec["author_display"] = rec["author_display"]
                    
                    # Comment is always unique per record
                    filtered_rec["comment"] = rec["comment"]
                    filtered_records.append(filtered_rec)
                
                return filtered_records
            return []
        
        group_type = group_levels[current_level]
        
        # Group records
        grouped: Dict[str, List[Dict]] = defaultdict(list)
        group_displays: Dict[str, Dict] = {}
        
        for rec in records:
            key = get_group_key(rec, group_type)
            grouped[key].append(rec)
            if key not in group_displays:
                group_displays[key] = get_group_display(rec, group_type)
        
        # Build result groups
        result = []
        for key in sorted(grouped.keys()):
            group_records = grouped[key]
            group_hours = round(sum(r["hours"] for r in group_records), 2)
            
            group_entry = {
                **group_displays[key],
                "hours": group_hours,
            }
            
            # Check if there are more levels
            next_used = used_groups + [group_type]
            if current_level + 1 < len(group_levels):
                # More grouping levels
                group_entry["groups"] = build_groups(
                    group_records, 
                    group_levels, 
                    current_level + 1,
                    next_used
                )
            elif details:
                # Deepest level with details
                group_entry["records"] = build_groups(
                    group_records,
                    group_levels,
                    current_level + 1,
                    next_used
                )
            
            result.append(group_entry)
        
        return result
    
    groups = build_groups(worklogs, group_by)
    
    return {
        "groups": groups,
        "total_hours": total_hours,
        "filter": filter_info,
        "group_by": group_by,
    }


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
    # Worklog functions
    "parse_iso_duration",
    "search_worklogs",
    "list_issue_worklogs",
    "get_worklogs_report",
    "create_worklog",
    "delete_worklog",
]
