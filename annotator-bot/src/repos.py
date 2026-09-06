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

def run_update_descriptive_statistics(repo_id: str, datasets: list[str]):
    repo_dir = repo_dirs[repo_id]
    try:
        cmd = '. .venv/bin/activate && uv run src/dynaword/update_descriptive_statistics.py' 
        for dataset in datasets:
            subprocess.run(["bash", "-c", f"{cmd} --dataset {dataset} --force"], check=True, cwd=repo_dir)
        subprocess.run(["bash", "-c", f"{cmd} --dataset default --force"], check=True, cwd=repo_dir)
        
        print(f"Descriptive statistics updated for {', '.join(datasets)}")
        return (
            [repo_dir / "descriptive_stats.json"] +
            [f for f in Path(repo_dir / "images").glob("*.*") if f.suffix in [".png", ".svg", ".html"]] +
            [repo_dir / "data" / dataset / "descriptive_stats.json" for dataset in datasets] +
            [repo_dir / "data" / dataset / "descriptive_stats.json" for dataset in datasets] +
            [repo_dir / "data" / dataset / "images/dist_document_length.png" for dataset in datasets]
        )
    except subprocess.CalledProcessError as e:
        print(f"Descriptive statistics update failed with exit code {e.returncode}")
        raise

