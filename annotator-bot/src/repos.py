import subprocess
from pathlib import Path
import shutil

from src.config import HF_REPO_IDS, ROOT

REPO_FOLDER = Path(ROOT / "repos")
REPO_FOLDER.mkdir(exist_ok=True)

repo_dirs: dict[str, Path] = {x:REPO_FOLDER / x.split("/")[-1] for x in HF_REPO_IDS}

def init_repos():
    for repo_id, path in repo_dirs.items():
        if not path.exists():
            path.mkdir()
            try:
                subprocess.run(["git", "clone", f"https://huggingface.co/datasets/{repo_id}", str(path)], check=True)
                subprocess.run(["git", "lfs", "pull"], check=True, cwd=path)
                subprocess.run(["make", "install"], check=True, cwd=path)
            except Exception as e:
                print(f"Failed to init {repo_id}: {e}")
                if path.exists():
                    shutil.rmtree(path) 
                raise e
    
def checkout_pr(repo_id: str, pr_num: int):
    repo_dir = repo_dirs[repo_id]
    subprocess.run(["git", "checkout", "-f", "main"], check=True, cwd=repo_dir) # git throws an error if we fetch from branch we are standing on
    subprocess.run(["git", "fetch", "origin", f"+refs/pr/{pr_num}:pr/{pr_num}"], check=True, cwd=repo_dir)
    subprocess.run(["git", "checkout", "-f", f"pr/{pr_num}"], check=True, cwd=repo_dir)

def run_test(repo_id: str):
    repo_dir = repo_dirs[repo_id]
    cmd = ". .venv/bin/activate && set -o pipefail; uv run pytest src/tests/ | tee test_results.log" # run tests manually with pipefail so we still capture exit errors
    
    try:
        subprocess.run(["bash", "-c", cmd], check=True, cwd=repo_dir)
        print("All tests passed!")
        return repo_dir / "test_results.log"
    except subprocess.CalledProcessError as e:
        print(f"Tests failed with exit code {e.returncode}")
        raise

def run_update_descriptive_statistics(repo_id: str):
    repo_dir = repo_dirs[repo_id]
    try:
        subprocess.run(["bash", "-c", ". .venv/bin/activate && make update-descriptive-statistics"], check=True, cwd=repo_dir)
        print("All descriptive statistics updated!")
        return [repo_dir / "descriptive_stats.json", repo_dir / "images", ]
    except subprocess.CalledProcessError as e:
        print(f"Descriptive statistics update failed with exit code {e.returncode}")
        raise

