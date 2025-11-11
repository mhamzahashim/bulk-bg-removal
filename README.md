# Drive Background Remover (Batch)

Removes the background of **all images** in a Google Drive folder and saves transparent PNGs to a new sibling folder `<name>_no_bg`. Originals remain untouched.

[![Open In Colab]([https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/YOURUSER/YOURREPO/blob/main/notebooks/remove_bg_drive.ipynb](https://colab.research.google.com/drive/1K0DN9o51jqOztkeIYiunrlVgMmD5rGW_?usp=sharing))

## Quick start (Colab)
1. Click the Colab badge above.
2. Run the single cell — it will:
   - upgrade pip,
   - install required packages,
   - ask you to **mount Google Drive** and **authenticate** to the Drive API,
   - remove the **background of all images** in the specified folder,
   - and save transparent PNGs to a new sibling folder `<foldername>_no_bg`.
3. To change the source folder, edit `FOLDER_LINK_OR_ID` at the top of the cell.

> This notebook works even if the folder is only **Shared with me**.

## Files
- `notebooks/remove_bg_drive.ipynb` — **Colab notebook** (one-cell, ready to run)
- `src/one_cell_remove_bg.py` — same code as a `.py` script
- `requirements.txt` — libraries if you want to run locally
- `LICENSE` — MIT License

## Requirements (local use)
If you want to run the script locally (not Colab), install:
```
pip install -r requirements.txt
```
> You will still need Google credentials for Drive API if you adapt it for local use.

## Troubleshooting
- If you see dependency conflicts in Colab, use **Runtime → Restart runtime** and run the cell again.
- If the notebook says Drive isn't mounted, make sure you ran the cell and authorized **Drive mount**.
- For optional GPU acceleration, try replacing `onnxruntime` with `onnxruntime-gpu` in the install line (Colab CPU is fine for most cases).

## License
MIT — see `LICENSE`.
