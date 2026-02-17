import os
import tempfile
import uuid
from pathlib import Path

import yt_dlp

from app.config import settings
from app.services.yt_utils import yt_dlp_cookie_opts
from app.database import storage_upload

BUCKET_NAME = "viral-videos"


def download_and_upload_video(video_url: str) -> str:
    """
    Download video with yt-dlp, upload to Supabase Storage, delete local file.
    Returns public URL of the uploaded file.
    """
    tmp_dir = tempfile.mkdtemp()
    output_template = os.path.join(tmp_dir, "%(id)s.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        "format": "best[ext=mp4]/best",
        "quiet": False,
    }
    ydl_opts.update(yt_dlp_cookie_opts())

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        if not info:
            raise ValueError(f"Could not download {video_url}")

        ext = info.get("ext", "mp4")
        video_id = info.get("id", "unknown")
        local_path = Path(tmp_dir) / f"{video_id}.{ext}"

        if not local_path.exists():
            files = list(Path(tmp_dir).glob("*"))
            if not files:
                raise FileNotFoundError(f"No file downloaded in {tmp_dir}")
            local_path = files[0]

        storage_path = f"viral/{uuid.uuid4().hex}.{ext}"
        with open(local_path, "rb") as f:
            data = f.read()

        result = storage_upload(
            BUCKET_NAME, storage_path, data, content_type=f"video/{ext}"
        )

        try:
            local_path.unlink(missing_ok=True)
        finally:
            os.rmdir(tmp_dir)

        return result
