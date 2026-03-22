import argparse
import pickle
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from huggingface_hub import hf_hub_download

try:
    import torch
except ImportError:  # pragma: no cover - only used in build container
    torch = None


DEFAULT_REPO = "oliverbravery/printguard"
DEFAULT_OUTPUT_DIR = "/opt/printguard/model"
FILES = {
    "model": "model.onnx",
    "options": "opt.json",
    "prototypes": "prototypes.pkl",
    "normalized_prototypes": "prototypes.npz",
}


def _download_with_retries(repo_id: str, filename: str, local_dir: Path) -> Path:
    attempts = 3
    for attempt in range(1, attempts + 1):
        try:
            return Path(
                hf_hub_download(repo_id=repo_id, filename=filename, local_dir=local_dir)
            )
        except Exception:
            if attempt == attempts:
                raise
            time.sleep(attempt)
    raise RuntimeError(f"Failed to download required artifact: {filename}")


def download(repo_id: str, output_dir: str) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output_path) as staging_dir_name:
        staging_dir = Path(staging_dir_name)
        model_path = output_path / FILES["model"]
        options_path = output_path / FILES["options"]
        prototypes_path = output_path / FILES["normalized_prototypes"]
        downloaded_model = _download_with_retries(
            repo_id,
            FILES["model"],
            staging_dir,
        )
        downloaded_options = _download_with_retries(
            repo_id,
            FILES["options"],
            staging_dir,
        )
        downloaded_prototypes = _download_with_retries(
            repo_id,
            FILES["prototypes"],
            staging_dir,
        )
        normalized_prototypes = staging_dir / FILES["normalized_prototypes"]
        normalize_prototypes(downloaded_prototypes, normalized_prototypes)
        downloaded_model.replace(model_path)
        downloaded_options.replace(options_path)
        normalized_prototypes.replace(prototypes_path)


def normalize_prototypes(raw_prototypes_path: Path, output_path: Path) -> None:
    if torch is None:
        raise RuntimeError(
            "torch is required at build time to normalize prototypes artifacts"
        )
    with open(raw_prototypes_path, "rb") as handle:
        cache_data = pickle.load(handle)
    prototypes = cache_data.get("prototypes")
    if hasattr(prototypes, "detach"):
        prototypes = prototypes.detach().cpu().numpy()
    else:
        prototypes = np.asarray(prototypes, dtype=np.float32)
    class_names = np.asarray(list(cache_data.get("class_names", [])), dtype=np.str_)
    np.savez_compressed(
        output_path,
        prototypes=prototypes.astype(np.float32),
        class_names=class_names,
        defect_idx=np.asarray(int(cache_data.get("defect_idx", -1)), dtype=np.int64),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Download PrintGuard ONNX artifacts")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="Hugging Face repo id")
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Model output directory",
    )
    args = parser.parse_args()
    download(args.repo, args.output_dir)


if __name__ == "__main__":
    main()
