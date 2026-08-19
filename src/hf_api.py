import re
from huggingface_hub import HfApi

from src.config import HF_REPO_ID

api = HfApi()

def get_unannotated_datasets() -> list[str]:
    """Return paths to dataset folders under data/ that are missing metadata.parquet."""
    all_files = set(
        api.list_repo_files(HF_REPO_ID, repo_type="dataset")
    )

    # collect all data/*/ dataset folders
    dataset_folders = {
        m.group(1) for f in all_files 
        if (m := re.match(r"^data/([^/]+)/.*\.parquet$", f))
    }

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



