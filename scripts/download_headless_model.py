import argparse
import pickle
from pathlib import Path

from huggingface_hub import hf_hub_download
import numpy as np

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
}


def download(repo_id: str, output_dir: str) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    prototypes_cache_dir = output_path / "prototypes" / "cache"
    prototypes_cache_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_path / FILES["model"]
    options_path = output_path / FILES["options"]
    prototypes_path = prototypes_cache_dir / FILES["prototypes"]
    downloaded_model = Path(
        hf_hub_download(repo_id=repo_id, filename=FILES["model"], local_dir=output_path)
    )
    downloaded_options = Path(
        hf_hub_download(repo_id=repo_id, filename=FILES["options"], local_dir=output_path)
    )
    downloaded_prototypes = Path(
        hf_hub_download(repo_id=repo_id, filename=FILES["prototypes"], local_dir=output_path)
    )
    if downloaded_model != model_path:
        downloaded_model.replace(model_path)
    if downloaded_options != options_path:
        downloaded_options.replace(options_path)
    if downloaded_prototypes != prototypes_path:
        downloaded_prototypes.replace(prototypes_path)
    normalize_prototypes(prototypes_path)


def normalize_prototypes(prototypes_path: Path) -> None:
    if torch is None:
        raise RuntimeError("torch is required at build time to normalize prototypes.pkl")
    with open(prototypes_path, "rb") as handle:
        cache_data = pickle.load(handle)
    prototypes = cache_data.get("prototypes")
    if hasattr(prototypes, "detach"):
        prototypes = prototypes.detach().cpu().numpy()
    else:
        prototypes = np.asarray(prototypes, dtype=np.float32)
    normalized_cache = {
        "prototypes": prototypes.astype(np.float32),
        "class_names": list(cache_data.get("class_names", [])),
        "defect_idx": int(cache_data.get("defect_idx", -1)),
    }
    with open(prototypes_path, "wb") as handle:
        pickle.dump(normalized_cache, handle)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download PrintGuard ONNX artifacts")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="Hugging Face repo id")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Model output directory")
    args = parser.parse_args()
    download(args.repo, args.output_dir)


if __name__ == "__main__":
    main()
