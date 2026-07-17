#!/usr/bin/env python3
"""Upload local folders to Supabase Storage.

Default folders (relative to repo root):
- PROTOCOLOS
- PROTOCOLOS ENFERMERIA
- ESQUEMAS TRATAMIENTOS
- DREAMM10 calendario pacientes

Usage example:
  SUPABASE_URL='https://<project-ref>.supabase.co' \
  SUPABASE_SERVICE_ROLE_KEY='...' \
  python scripts/upload_folders_to_supabase_storage.py

By default this script uploads all files into one bucket named
"ensayos-files" under folder prefixes matching the local folder names.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
from pathlib import Path
from typing import Iterable
from urllib import error, parse, request

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_FOLDERS = [
    "PROTOCOLOS",
    "PROTOCOLOS ENFERMERIA",
    "ESQUEMAS TRATAMIENTOS",
    "DREAMM10 calendario pacientes",
]


def env(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise ValueError(f"Missing required env var: {name}")
    return value


def api_request(
    method: str,
    url: str,
    service_key: str,
    body: bytes | None = None,
    content_type: str | None = None,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, bytes]:
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }
    if content_type:
        headers["Content-Type"] = content_type
    if extra_headers:
        headers.update(extra_headers)

    req = request.Request(url, data=body, method=method, headers=headers)
    try:
        with request.urlopen(req, timeout=60) as resp:
            return resp.getcode(), resp.read()
    except error.HTTPError as exc:
        return exc.code, exc.read()


def ensure_bucket(base_url: str, service_key: str, bucket: str, public: bool) -> None:
    create_url = f"{base_url}/storage/v1/bucket"
    payload = json.dumps({"id": bucket, "name": bucket, "public": public}).encode("utf-8")
    status, data = api_request("POST", create_url, service_key, payload, "application/json")

    if status in (200, 201):
        print(f"Bucket created: {bucket}")
        return

    # Bucket already exists often returns 400 with a message.
    if status == 400:
        msg = data.decode("utf-8", errors="ignore").lower()
        if "already exists" in msg or "duplicate" in msg:
            print(f"Bucket already exists: {bucket}")
            return

    raise RuntimeError(
        f"Unable to create/verify bucket '{bucket}'. HTTP {status}. Response: {data[:400]!r}"
    )


def iter_files(folder_path: Path) -> Iterable[Path]:
    for path in folder_path.rglob("*"):
        if path.is_file():
            yield path


def upload_file(
    base_url: str,
    service_key: str,
    bucket: str,
    object_key: str,
    local_file: Path,
    upsert: bool,
) -> None:
    encoded_key = parse.quote(object_key, safe="/")
    upload_url = f"{base_url}/storage/v1/object/{bucket}/{encoded_key}"

    content_type, _ = mimetypes.guess_type(str(local_file))
    if not content_type:
        content_type = "application/octet-stream"

    body = local_file.read_bytes()
    status, data = api_request(
        "POST",
        upload_url,
        service_key,
        body=body,
        content_type=content_type,
        extra_headers={"x-upsert": "true" if upsert else "false"},
    )

    if status not in (200, 201):
        raise RuntimeError(
            f"Upload failed for '{local_file}'. HTTP {status}. Response: {data[:400]!r}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload folders to Supabase Storage")
    parser.add_argument(
        "--bucket",
        default=os.getenv("SUPABASE_BUCKET", "ensayos-files"),
        help="Target bucket name (default: ensayos-files)",
    )
    parser.add_argument(
        "--public",
        action="store_true",
        help="Create bucket as public (default: private)",
    )
    parser.add_argument(
        "--no-upsert",
        action="store_true",
        help="Do not overwrite objects that already exist",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be uploaded",
    )
    parser.add_argument(
        "--folders",
        nargs="*",
        default=DEFAULT_FOLDERS,
        help="Folders to upload (default: the 4 project data folders)",
    )
    args = parser.parse_args()

    supabase_url = ""
    service_key = ""
    if not args.dry_run:
        try:
            supabase_url = env("SUPABASE_URL").rstrip("/")
            service_key = env("SUPABASE_SERVICE_ROLE_KEY")
        except ValueError as exc:
            print(f"ERROR: {exc}")
            return 1

    folders: list[Path] = [ROOT_DIR / f for f in args.folders]
    missing = [str(p) for p in folders if not p.exists()]
    if missing:
        print("ERROR: Missing folders:")
        for path in missing:
            print(f"- {path}")
        return 1

    if not args.dry_run:
        ensure_bucket(supabase_url, service_key, args.bucket, args.public)

    total = 0
    for folder_path in folders:
        folder_name = folder_path.name
        files = list(iter_files(folder_path))
        print(f"\nFolder: {folder_name} | files: {len(files)}")

        for file_path in files:
            rel = file_path.relative_to(folder_path).as_posix()
            object_key = f"{folder_name}/{rel}"
            total += 1

            if args.dry_run:
                print(f"DRY-RUN upload -> {args.bucket}/{object_key}")
                continue

            upload_file(
                base_url=supabase_url,
                service_key=service_key,
                bucket=args.bucket,
                object_key=object_key,
                local_file=file_path,
                upsert=not args.no_upsert,
            )
            print(f"Uploaded: {args.bucket}/{object_key}")

    print(f"\nDone. Files processed: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
