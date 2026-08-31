import re
from datetime import datetime, timezone
from huggingface_hub import HfApi, DiscussionComment, Discussion

from src.config import HF_REPO_ID

api = HfApi()

def get_datasets(revision: str | None = None) -> set[str]:
    """Return dataset names found under data/ for a specific revision."""
    files = api.list_repo_files(HF_REPO_ID, repo_type="dataset", revision=revision)
    return {
        m.group(1) for f in files
        if (m := re.match(r"^data/([^/]+)/.*\.parquet$", f))
    }

def get_unannotated_datasets() -> list[str]:
    """Return paths to dataset folders under data/ that are missing metadata.parquet."""
    all_files = set(
        api.list_repo_files(HF_REPO_ID, repo_type="dataset")
    )

    dataset_folders = get_datasets()

    # fetch open PRs to avoid duplicate annotations
    open_prs = api.get_repo_discussions(HF_REPO_ID, repo_type="dataset")
    pending_datasets = set()
    for pr in open_prs:
        if pr.is_pull_request and pr.status == "open":
            m = re.search(r"\[bot\] ([\w-]+) annotations", pr.title)
            if m:
                pending_datasets.add(m.group(1))

    # return folders that don't have a metadata.parquet yet and aren't pending
    return [
        f"data/{folder}"
        for folder in dataset_folders
        if f"data/{folder}/metadata.parquet" not in all_files
        and folder not in pending_datasets
    ]


def create_pr(local_path: str, remote_path: str, commit_message: str, description: str = ""):
    api.upload_file(
        path_or_fileobj=local_path,
        path_in_repo=remote_path,
        repo_id=HF_REPO_ID,
        repo_type="dataset",
        commit_message=commit_message,
        commit_description=description,
        create_pr=True
    )    

def upload_to_pr(local_path: str, remote_path: str, pr_num: int, commit_message: str):
    api.upload_file(
        path_or_fileobj=local_path,
        path_in_repo=remote_path,
        repo_id=HF_REPO_ID,
        repo_type="dataset",
        commit_message=commit_message,
        revision=f"refs/pr/{pr_num}"
    )

def get_discussions(threshold: datetime | None = None, repo: str = HF_REPO_ID) -> list[Discussion]:
    """Return discussions that were created after the given threshold."""
    discussions = api.get_repo_discussions(
        repo_id=repo,
        repo_type="dataset"
    )
    
    return [d for d in discussions if threshold is None or d.created_at > threshold]

def get_discussion(repo_id: str, discussion_num: int) -> Discussion:
    """Return details for a specific discussion."""
    return api.get_discussion_details(
        repo_id=repo_id,
        repo_type="dataset",
        discussion_num=discussion_num
    )


def add_comment(discussion : Discussion, comment: str) -> DiscussionComment:
    """Add a comment to a discussion."""
    return api.comment_discussion(
        repo_id=discussion.repo_id,
        repo_type="dataset",
        discussion_num=discussion.num,
        comment=comment
    )

def update_comment(discussion : Discussion, comment_id: str, new_content: str) -> DiscussionComment:
    """Edit an existing comment in a discussion."""
    return api.edit_discussion_comment(
        repo_id=discussion.repo_id,
        repo_type="dataset",
        discussion_num=discussion.num,
        comment_id=comment_id,
        new_content=new_content
    )
