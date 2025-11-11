# === ONE-CELL: Drive mount + install + remove background for ALL images in your Drive folder ===
# Edit the FOLDER_LINK_OR_ID if you want to change the source folder.
FOLDER_LINK_OR_ID = "https://drive.google.com/drive/folders/1NnSIpOyJzZtM6e2iVqArwwWj3QPBOj3Z"
OUTPUT_SUFFIX = "_no_bg"       # Output folder name = <source_folder_name> + this suffix
MODEL_NAME = "u2net"           # Options: "u2net", "u2netp", "isnet-general-use"

# --- Keep pip/tooling fresh (helps dependency resolution) ---
!pip -q install -U pip setuptools wheel

# --- Install dependencies (no hard pins → let pip resolve compatible versions) ---
!pip -q install --no-cache-dir rembg onnxruntime opencv-python-headless pillow tqdm \
    google-api-python-client google-auth-httplib2 google-auth-oauthlib

# --- Import + mount Drive ---
from pathlib import Path
try:
    from google.colab import drive
    if not Path("/content/drive").exists():
        drive.mount('/content/drive')
except Exception as _e:
    pass

# --- Remove background from ALL images in the Drive folder and write PNGs to <name>_no_bg ---
import io, re
from typing import Optional
from PIL import Image, UnidentifiedImageError
from tqdm import tqdm
from rembg import remove, new_session

def extract_folder_id(link_or_id: str) -> Optional[str]:
    """Accept a raw folder ID or any standard Drive folder URL; return the folder ID."""
    if not link_or_id:
        return None
    m = re.search(r"/folders/([A-Za-z0-9_-]{10,})", link_or_id)
    if m:
        return m.group(1)
    import re as _re
    if _re.fullmatch(r"[A-Za-z0-9_-]{10,}", link_or_id):
        return link_or_id
    return None

def process_drive_folder(folder_id: str, output_suffix: str, model_name: str):
    # Auth for Drive API
    from google.colab import auth
    auth.authenticate_user()
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
    from googleapiclient.errors import HttpError
    import google.auth

    # Init model once
    session = new_session(model_name)

    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/drive"])
    service = build('drive', 'v3', credentials=creds)

    # 1) Get source folder meta
    src = service.files().get(fileId=folder_id, fields="id,name,parents").execute()
    src_name = src.get("name")
    parents = src.get("parents", [])
    parent_for_output = [parents[0]] if parents else []
    out_name = f"{src_name}{output_suffix}"

    # 2) Create/locate sibling output folder
    q = f"name = '{out_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    if parent_for_output:
        q += f" and '{parent_for_output[0]}' in parents"
    res = service.files().list(q=q, spaces='drive', fields="files(id,name)").execute()
    if res.get("files"):
        out_folder_id = res["files"][0]["id"]
    else:
        meta = {"name": out_name, "mimeType": "application/vnd.google-apps.folder"}
        if parent_for_output:
            meta["parents"] = parent_for_output
        out = service.files().create(body=meta, fields="id,name").execute()
        out_folder_id = out["id"]

    # 3) Build set of existing outputs (skip already-processed)
    existing = set()
    pg = None
    while True:
        resp = service.files().list(
            q=f"'{out_folder_id}' in parents and trashed = false",
            spaces='drive', fields="nextPageToken, files(name)", pageToken=pg
        ).execute()
        for f in resp.get("files", []):
            existing.add(f["name"])
        pg = resp.get("nextPageToken")
        if not pg:
            break

    # 4) Collect ALL top-level images in source folder
    def is_image_mime(mt: str) -> bool:
        return mt.startswith("image/") or mt in {"image/bmp", "image/png", "image/jpeg", "image/webp", "image/tiff"}

    files = []
    pg = None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            spaces='drive', fields="nextPageToken, files(id,name,mimeType)", pageToken=pg
        ).execute()
        for f in resp.get("files", []):
            if is_image_mime(f.get("mimeType", "")):
                files.append(f)
        pg = resp.get("nextPageToken")
        if not pg:
            break

    if not files:
        raise FileNotFoundError("No images found in the provided Drive folder.")

    print(f"Input folder : {src_name} ({folder_id})")
    print(f"Output folder: {out_name} ({out_folder_id})")
    print("Processing ALL images in that folder...")

    # 5) Process each image → transparent PNG uploaded to output folder
    done = skipped = errors = 0
    for f in tqdm(files, desc="Removing backgrounds", ncols=100):
        in_id = f["id"]
        stem = f["name"].rpartition(".")[0] or f["name"]
        out_name_png = f"{stem}.png"

        if out_name_png in existing:
            skipped += 1
            continue

        try:
            # Download original bytes
            req = service.files().get_media(fileId=in_id)
            buf = io.BytesIO()
            downloader = MediaIoBaseDownload(buf, req)
            finished = False
            while not finished:
                _status, finished = downloader.next_chunk()
            inp_bytes = buf.getvalue()

            # Remove background (rembg returns PNG bytes with alpha)
            out_bytes = remove(inp_bytes, session=session)

            # Normalize to RGBA PNG and upload
            with Image.open(io.BytesIO(out_bytes)) as im:
                if im.mode != "RGBA":
                    im = im.convert("RGBA")
                out_stream = io.BytesIO()
                im.save(out_stream, format="PNG", optimize=True)
                out_stream.seek(0)

            media = MediaIoBaseUpload(out_stream, mimetype="image/png", resumable=False)
            meta = {"name": out_name_png, "parents": [out_folder_id]}
            _ = service.files().create(body=meta, media_body=media, fields="id").execute()
            existing.add(out_name_png)
            done += 1

        except UnidentifiedImageError:
            errors += 1
            print(f"[WARN] Unreadable image skipped: {f['name']}")
        except HttpError as he:
            errors += 1
            print(f"[ERROR] {f['name']} (HTTP): {he}")
        except Exception as e:
            errors += 1
            print(f"[ERROR] {f['name']}: {e}")

    print("\n----- Summary -----")
    print(f"Processed : {done}")
    print(f"Skipped   : {skipped} (already exists)")
    print(f"Errors    : {errors}")
    print(f"\n✅ Finished. Output folder:\nhttps://drive.google.com/drive/folders/{out_folder_id}")

# --- Run ---
_folder_id = extract_folder_id(FOLDER_LINK_OR_ID)
if not _folder_id:
    raise ValueError("Could not extract a folder ID from FOLDER_LINK_OR_ID. Please double-check the link.")
process_drive_folder(_folder_id, OUTPUT_SUFFIX, MODEL_NAME)