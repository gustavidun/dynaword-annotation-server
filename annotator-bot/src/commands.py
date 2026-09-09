from huggingface_hub import Discussion

from src.annotate import annotate_dataset
from src.db import Webhook 
from src.hf_api import (
    get_discussion, add_comment,
    update_comment, upload_to_pr, get_datasets
)
from src.config import NAME
from src.util import get_dataset_path
from src.repos import run_test, checkout_pr, repo_dirs, run_update_descriptive_statistics

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

def ping(discussion : Discussion, *args):
    add_comment(discussion, f"The bot is live and responsive.")

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

        status_comment_msg = f"**INFO**: Starting annotation for `{dataset_name}`..."
        status_comment = add_comment(discussion, status_comment_msg)

        try:
            checkout_pr(discussion.repo_id, discussion.num)
        except Exception as e:
            status_comment_msg += f"\n \n **ERROR**: Failed to checkout PR. Error message: `{e}`."
            update_comment(discussion, status_comment.id, status_comment_msg)
            return
        
        try:
            dest = annotate_dataset(
                discussion.repo_id,
                get_dataset_path(dataset_name), 
                repo_dirs[discussion.repo_id] / "data" / dataset_name, 
                revision=f"refs/pr/{discussion.num}",
                dataset_name=dataset_name
            )
            status_comment_msg += "\n \n **INFO**: Annotation completed." 
            update_comment(discussion,status_comment.id,status_comment_msg)
        except Exception as e:
            status_comment_msg += "\n \n **ERROR**: Annotation failed." 
            update_comment(discussion,status_comment.id,status_comment_msg)
            return

        try:
            run_test(discussion.repo_id)
            status_comment_msg += "\n \n **INFO**: Tests passed."
            update_comment(discussion,status_comment.id,status_comment_msg)
        except Exception as e:
            status_comment_msg += "\n \n **ERROR**: Tests failed. See test_results.log for more information. You may need to fix the issue manually." 
            update_comment(discussion,status_comment.id,status_comment_msg)

        try:
            stats_files = run_update_descriptive_statistics(discussion.repo_id, [dataset_name])
            status_comment_msg += "\n \n **INFO**: Descriptive statistics updated."
            update_comment(discussion,status_comment.id,status_comment_msg)
            upload_to_pr(
                discussion.repo_id,
                local_path=[str(f) for f in stats_files],
                pr_num=discussion.num,
                commit_message=f"Add descriptive statistics for {dataset_name}"
            )
        except Exception as e:
            status_comment_msg += f"\n \n **ERROR**: Failed to update descriptive statistics. You may need to update them manually. Error: {e}"
            update_comment(discussion,status_comment.id,status_comment_msg)

        try:
            upload_to_pr(
                discussion.repo_id,
                local_path=[str(dest)],
                pr_num=discussion.num,
                commit_message=f"Add annotations for {dataset_name}"
            )
            upload_to_pr(
                discussion.repo_id,
                local_path=[str(repo_dirs[discussion.repo_id] / "test_results.log")],
                pr_num=discussion.num,
                commit_message=f"Add test results for {dataset_name}"
            )
            status_comment_msg += f"\n \n **SUCCESS**: Uploaded annotations and test results for `{dataset_name}`."
            update_comment(discussion, status_comment.id, status_comment_msg)
        except Exception as e:
            status_comment_msg += f"\n \n **ERROR**: Failed to upload annotations / test results. Error message: `{e}`."
            update_comment(discussion, status_comment.id, status_comment_msg)
            return
   
    except Exception as err:
        print(f"Annotation failed: {err}")
        if 'status_comment' in locals(): # if status_comment was created before the Exception happened, update it
            update_comment(discussion, status_comment.id, f"\n \n **ERROR**: Annotation failed. Error message: `{err}`")
    
COMMANDS = {
    "annotate": add_annotations,
    "ping": ping
}



    