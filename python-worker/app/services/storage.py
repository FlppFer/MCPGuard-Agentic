import io
import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import boto3
from botocore.config import Config as BotoConfig

from app.config import settings

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".json", ".yaml", ".yml", ".toml", ".md",
}


def _build_s3_client():
    kwargs: dict = {
        "service_name": "s3",
        "region_name": settings.aws_region,
        "config": BotoConfig(retries={"max_attempts": 3, "mode": "standard"}),
    }
    if settings.aws_access_key_id:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    if settings.s3_endpoint:
        kwargs["endpoint_url"] = settings.s3_endpoint
    return boto3.client(**kwargs)


async def download_and_extract(source_key: str) -> Path:
    """Download the source ZIP and extract it into a temporary directory.

    Returns the Path to the extracted directory.
    """
    extract_dir = Path(tempfile.mkdtemp(prefix="mcpguard_"))

    try:
        if settings.storage_mode == "local":
            zip_path = Path(settings.local_storage_path) / source_key
            logger.info("Reading source archive from local path: %s", zip_path)
            if not zip_path.exists():
                raise FileNotFoundError(f"Local archive not found: {zip_path}")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)
        else:
            logger.info("Downloading source archive from S3: bucket=%s key=%s", settings.s3_bucket, source_key)
            s3 = _build_s3_client()
            response = s3.get_object(Bucket=settings.s3_bucket, Key=source_key)
            zip_bytes = response["Body"].read()
            with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
                zf.extractall(extract_dir)

        logger.info("Extracted source archive to %s", extract_dir)
        return extract_dir

    except Exception:
        shutil.rmtree(extract_dir, ignore_errors=True)
        raise


def collect_source_files(extract_dir: Path) -> dict[str, str]:
    """Walk the extracted directory and return {relative_path: content} for supported files."""
    files: dict[str, str] = {}
    for root, _dirs, filenames in os.walk(extract_dir):
        for fname in filenames:
            fpath = Path(root) / fname
            if fpath.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            rel = fpath.relative_to(extract_dir).as_posix()
            try:
                files[rel] = fpath.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                logger.warning("Skipping unreadable file %s: %s", rel, exc)
    logger.info("Collected %d source files for analysis", len(files))
    return files


def cleanup(extract_dir: Path) -> None:
    """Remove the temporary extraction directory."""
    shutil.rmtree(extract_dir, ignore_errors=True)
    logger.debug("Cleaned up %s", extract_dir)
