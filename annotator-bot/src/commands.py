from huggingface_hub import Discussion

from src.annotate import annotate_dataset
from src.db import Webhook 
from src.hf_api import (
    get_discussion, add_comment,
    update_comment, upload_to_pr, get_datasets
)
from src.config import NAME
from src.util import get_dataset_path
from src.repos import run_test, run_update_descriptive_statistics, checkout_pr, repo_dirs

def parse_and_run_commands(webhooks : list[Webhook]):
    for webhook in webhooks:
        if webhook.status == "completed":
            continue
        
        if webhook.payload["event"]["action"] != "create" or webhook.payload["event"]["scope"] != "discussion.comment":
            continue

        comment = webhook.payload["comment"].get("content", "")
        if comment == "":
            continue
        words = comment.split()
        if words and words[0] == "@" + NAME:
            discussion = get_discussion(
                webhook.payload["repo"]["name"],
                webhook.payload["discussion"]["num"]
            )
            run_command(comment, discussion)

def run_command(command: str, discussion: Discussion):
    args = command.lower().split()
    if len(args) < 2:
        return
    cmd_name = args[1]
    cmd_args = args[2:]
    if cmd_name in COMMANDS.keys():
        COMMANDS[cmd_name](discussion, *cmd_args)
    else:
        add_comment(discussion, f"Unknown command: `{cmd_name}`")
        print(f"Unknown command: {cmd_name}")

def add_annotations(discussion : Discussion, *args):
    if not discussion.is_pull_request:
        add_comment(discussion, "Annotation failed. Discussion is not a pull request.")
        return

    if len(args) == 0:
        add_comment(discussion, "Annotation failed. Missing dataset name.")
        return

    if len(args) > 1:
        add_comment(discussion, "Annotation failed. Too many arguments.")
        return

    try:
        dataset_name = args[0]
        
        pr_datasets = get_datasets(discussion.repo_id, f"refs/pr/{discussion.num}")
        if dataset_name not in pr_datasets:
            add_comment(discussion, f"Annotation failed. Dataset '{dataset_name}' not found in this PR.")
            return

        status_comment = add_comment(discussion, f"⏳ Starting annotation for `{dataset_name}`...")
        checkout_pr(discussion.repo_id, discussion.num)
        
        dest = annotate_dataset(
            discussion.repo_id,
            get_dataset_path(dataset_name), 
            repo_dirs[discussion.repo_id] / "data" / dataset_name, 
            revision=f"refs/pr/{discussion.num}"
        )

        run_test(discussion.repo_id)

        upload_to_pr(
            discussion.repo_id,
            local_path=str(dest),
            remote_path=f"data/{dataset_name}/metadata.parquet",
            pr_num=discussion.num,
            commit_message=f"Add annotations for {dataset_name}"
        )
        update_comment(discussion, status_comment.id, f"Finished annotating `{dataset_name}` and created a commit.")
        
    except Exception as err:
        print(f"Annotation failed: {err}")
        if 'status_comment' in locals(): # if status_comment was created before the Exception happened, update it
            update_comment(discussion, status_comment.id, f"Annotation failed: {err}")
    
COMMANDS = {
    "annotate": add_annotations,
}



    