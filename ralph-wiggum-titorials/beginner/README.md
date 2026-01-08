# Ralph Wiggun Janitor - Downloads Folder Organizer

This script uses an AI agent to automatically organize your Downloads folder by:
- Reading each file's contents (using OCR/Vision when needed)
- Extracting dates, entities, and document types
- Renaming files to a consistent format: `[YYYY-MM-DD]_[Entity]_[Type].[ext]`
- Moving files into categorized subfolders

## Usage

```bash
cd ~/Downloads
chmod +x ralph-wiggum-janitor.sh
./ralph-wiggum-janitor.sh
```

## How It Works

1. **Processes files one by one** - The agent opens each file in your Downloads folder
2. **Reads content** - Extracts text from PDFs, uses Vision for images, reads metadata
3. **Uses OCR when needed** - If a PDF has no text layer, it uses Vision/OCR to read it
4. **Renames intelligently** - Creates descriptive names like:
   - `2025-04-15_IRS_TaxReturn.pdf`
   - `2024-12-31_AcmeCorp_Invoice.pdf`
   - `2026-01-20_Delta_Flight_ATL.png`
5. **Categorizes & moves** - Files are moved to appropriate folders:
   - `Financial/` - Tax docs, paystubs, invoices
   - `Legal/` - Contracts, agreements
   - `Travel/` - Flight confirmations, visas
   - `Medical/` - Health documents
   - `Work/` - Professional documents
   - `Images/` - Screenshots, photos
   - `Media/` - Videos, audio
   - `Software/` - Installers (.dmg, .pkg)
   - `Research/` - Academic papers
   - `Receipts/` - Purchase receipts
   - `Miscellaneous/` - Everything else
   - `Quarantine/` - Files that couldn't be processed

## Features

- **Resumable** - If interrupted, run again to continue where you left off
- **Failure tracking** - Files that fail are logged in `ralph_failures.txt`
- **Duplicate handling** - Automatically appends `_v2`, `_v3` if filename exists
- **Safe** - Never deletes files, only moves them
- **Quarantine** - Unreadable files go to `Quarantine/` folder

## Requirements

- `opencode` CLI tool installed and configured
- Model: `opencode/gemini-3-flash` (or modify `MODEL` variable in script)

## Notes

- The script only processes files in the Downloads root (not subdirectories)
- It skips itself and the failure log file
- You can interrupt with Ctrl+C and resume later
- Check `ralph_failures.txt` for any files that couldn't be processed

