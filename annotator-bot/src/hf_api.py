import re
from datetime import datetime, timezone
from huggingface_hub import HfApi, DiscussionComment, Discussion, CommitOperationAdd
from src.config import HF_TOKEN

api = HfApi(token=HF_TOKEN or None)

def get_datasets(repo_id: str, revision: str | None = None, hf_token: str = HF_TOKEN) -> set[str]:
    """Return dataset names found under data/ for a specific revision."""
    files = api.list_repo_files(repo_id, repo_type="dataset", revision=revision, token=hf_token or None)
    return {
        m.group(1) for f in files
        if (m := re.match(r"^data/([^/]+)/.*\.parquet$", f))
    }

def get_unannotated_datasets(repo_id: str, hf_token: str = HF_TOKEN) -> list[str]:
    """Return paths to dataset folders under data/ that are missing metadata.parquet."""
    all_files = set(
        api.list_repo_files(repo_id, repo_type="dataset", token=hf_token or None)
    )

    dataset_folders = get_datasets(repo_id, hf_token=hf_token)

    # fetch open PRs to avoid duplicate annotations
    open_prs = api.get_repo_discussions(repo_id, repo_type="dataset", token=hf_token or None)
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


def create_pr(repo_id: str, local_path: str, remote_path: str, commit_message: str, description: str = "", hf_token: str = HF_TOKEN):
    api.upload_file(
        path_or_fileobj=local_path,
        path_in_repo=remote_path,
        repo_id=repo_id,
        repo_type="dataset",
        commit_message=commit_message,
        commit_description=description,
        create_pr=True,
        token=hf_token or None
    )    

def upload_to_pr(repo_id: str, local_path: list[str], pr_num: int, commit_message: str, hf_token: str = HF_TOKEN):
    api.create_commit(
        repo_id=repo_id,
        repo_type="dataset",
        operations=[
            CommitOperationAdd(
                path_or_fileobj=path, 
                path_in_repo=path
            ) 
            for path in local_path
        ],
        commit_message=commit_message,
        revision=f"refs/pr/{pr_num}",
        token=hf_token or None
    )

def get_discussion(repo_id: str, discussion_num: int, hf_token: str = HF_TOKEN) -> Discussion:
    """Return details for a specific discussion."""
    return api.get_discussion_details(
        repo_id=repo_id,
        repo_type="dataset",
        discussion_num=discussion_num,
        token=hf_token or None
    )


def add_comment(discussion : Discussion, comment: str, hf_token: str = HF_TOKEN) -> DiscussionComment:
    """Add a comment to a discussion."""
    return api.comment_discussion(
        repo_id=discussion.repo_id,
        repo_type="dataset",
        discussion_num=discussion.num,
        comment=comment,
        token=hf_token or None
    )

def update_comment(discussion : Discussion, comment_id: str, new_content: str, hf_token: str = HF_TOKEN) -> DiscussionComment:
    """Edit an existing comment in a discussion."""
    return api.edit_discussion_comment(
        repo_id=discussion.repo_id,
        repo_type="dataset",
        discussion_num=discussion.num,
        comment_id=comment_id,
        new_content=new_content,
        token=hf_token or None
    )
