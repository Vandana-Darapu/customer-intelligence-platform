"""Download Amazon Reviews 2023 files listed in config/settings.yaml."""
from pathlib import Path
import requests
import yaml
PROJECT_ROOT = Path(__file__).resolve().parents[1]
def load_config():
    with open(PROJECT_ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)
def download_file(url, destination):
    """Stream a file to disk, skipping it if it already exists."""
    if destination.exists():
        print(f"Skipping (already exists): {destination.name}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = destination.with_suffix(destination.suffix + ".part")
    print(f"Downloading {destination.name} ...")
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        total = int(response.headers.get("Content-Length", 0))
        done = 0
        with open(temp_path, "wb") as out:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                out.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r  {done / 1e6:.0f} / {total / 1e6:.0f} MB", end="")
    temp_path.rename(destination)
    print(f"\n  Saved to {destination}")
def main():
    config = load_config()
    raw_dir = PROJECT_ROOT / config["raw_dir"]
    for category in config["categories"]:
        review_url = f"{config['base_url']}/review_categories/{category}.jsonl.gz"
        meta_url = f"{config['base_url']}/meta_categories/meta_{category}.jsonl.gz"
        download_file(review_url, raw_dir / f"{category}.jsonl.gz")
        download_file(meta_url, raw_dir / f"meta_{category}.jsonl.gz")
if __name__ == "__main__":
    main()
