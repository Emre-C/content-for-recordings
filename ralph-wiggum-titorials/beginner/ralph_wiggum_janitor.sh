#!/bin/bash
set -euo pipefail

# --- CONFIGURATION ---
SOURCE_DIR="."  # Current directory (Downloads)
MODEL="opencode/gemini-3-flash"
FAILED_LOG="ralph_failures.txt"  # Tracks files that stumped the agent
QUARANTINE_DIR="Quarantine"  # For files that can't be processed

# --- TAXONOMY & INSTRUCTIONS ---
readonly TAXONOMY="# ROLE
You are a Digital Janitor Agent. Your job is to organize a chaotic Downloads folder.

# TARGET CATEGORIES (Create subfolders as needed)
- Financial/ (tax documents, paystubs, invoices, receipts, W2s, 1099s, bank statements)
- Legal/ (contracts, agreements, disclosures, executed documents)
- Travel/ (flight confirmations, visas, travel documents, hotel bookings)
- Medical/ (medical records, insurance documents, health forms)
- Work/ (work documents, presentations, spreadsheets, professional files)
- Personal/ (personal photos, personal documents, family items)
- Media/ (videos, audio files, music)
- Images/ (screenshots, memes, downloaded images, graphics)
- Software/ (installers: .dmg, .pkg, .exe, setup files)
- Research/ (academic papers, research PDFs, articles)
- Receipts/ (purchase receipts, order confirmations, transaction records)
- Miscellaneous/ (anything that doesn't fit above categories)

# INSTRUCTIONS
1. **OPEN & READ**: 
   - Open the file. Read its contents.
   - For PDFs: Extract text. If text layer is empty, use Vision/OCR to read the image.
   - For images: Use Vision to understand what the image contains.
   - For spreadsheets: Read the content and understand the data.
   - For videos/audio: If possible, extract metadata or use vision on thumbnails.

2. **EXTRACT INFORMATION**:
   - Find dates (prefer dates from content over filename)
   - Identify entities (company names, people, organizations)
   - Determine document type (tax return, receipt, contract, etc.)

3. **RENAME**:
   - Format: [YYYY-MM-DD]_[Entity]_[Type].[ext]
   - Examples:
     * 2025-04-15_IRS_TaxReturn.pdf
     * 2024-12-31_AcmeCorp_Invoice.pdf
     * 2026-01-20_Delta_Flight_ATL.png
     * 2024-11-15_HomeDepot_Receipt.pdf
   - If no date found, use \"0000-00-00\" or omit date prefix
   - If entity unclear, use a descriptive type name
   - Preserve original extension

4. **HANDLE DUPLICATES**:
   - If target filename exists, append \"_v2\", \"_v3\", etc.
   - Check if it's actually a duplicate or different file

5. **CATEGORIZE & MOVE**:
   - Pick the best category folder
   - Create the folder if it doesn't exist
   - MOVE (not copy) the file to that folder with the new name
   - This is CRITICAL - the file must leave the Downloads root

6. **ERROR HANDLING**:
   - If you cannot read the file (corrupted, encrypted, unsupported):
     * Move it to Quarantine/ folder with original name
     * Log why it failed
   - If OCR fails after retry, quarantine it
   - Never delete files - always move them

7. **SILENCE**: No chat. Just do the work. Process the file and move it.

# CRITICAL RULES
- ALWAYS move files out of the root Downloads folder
- NEVER leave files in the root after processing
- If unsure about category, use Miscellaneous/
- Preserve file extensions
- Handle duplicates gracefully
- Use Vision/OCR when text extraction fails"

# --- FUNCTIONS ---

log_failure() {
    local filename="$1"
    local reason="$2"
    echo "${filename} | ${reason}" >> "$FAILED_LOG"
}

ensure_quarantine() {
    if [ ! -d "$QUARANTINE_DIR" ]; then
        mkdir -p "$QUARANTINE_DIR"
        echo "📁 Created quarantine directory: $QUARANTINE_DIR"
    fi
}

organize_files() {
    # 1. Load failures to avoid retrying "poison" files
    local failed_filenames=()
    if [ -f "$FAILED_LOG" ]; then
        while IFS= read -r line; do
            if [ -n "$line" ]; then
                local filename="${line%% | *}"
                failed_filenames+=("$filename")
            fi
        done < "$FAILED_LOG"
    fi
    
    # 2. Ensure quarantine directory exists
    ensure_quarantine
    
    # 3. Find and Sort files (only root-level files, skip subdirectories)
    # Exclude common system files and the script itself
    local temp_file
    temp_file=$(mktemp)
    find "$SOURCE_DIR" -maxdepth 1 -type f \
        ! -name "digital_janitor.sh" \
        ! -name "digital_janitor_failures.txt" \
        ! -name ".DS_Store" \
        ! -name ".*" | sort > "$temp_file"
    
    local files_to_process=()
    while IFS= read -r file; do
        if [ -n "$file" ]; then
            files_to_process+=("$file")
        fi
    done < "$temp_file"
    rm -f "$temp_file"
    
    local total_files=${#files_to_process[@]}
    echo "🔎 Found ${total_files} files remaining in queue."
    
    if [ $total_files -eq 0 ]; then
        echo "✨ No files to process! Downloads folder is clean."
        return 0
    fi
    
    local i=0
    for filepath in "${files_to_process[@]}"; do
        i=$((i + 1))
        local filename
        filename=$(basename "$filepath")
        
        # Skip if we already failed on this file
        local skip=false
        if [ ${#failed_filenames[@]} -gt 0 ]; then
            for failed_name in "${failed_filenames[@]}"; do
                if [ "$filename" = "$failed_name" ]; then
                    skip=true
                    break
                fi
            done
        fi
        
        if [ "$skip" = true ]; then
            echo "⏩ Skipping known failure: ${filename}"
            continue
        fi
        
        echo ""
        echo "[${i}/${total_files}] 🤖 Digital Janitor processing: ${filename}"
        
        # Construct multi-line prompt and pass via stdin (heredoc)
        # This is more reliable for multi-line prompts than passing as argument
        if opencode run --model "$MODEL" <<PROMPT_EOF; then
${TAXONOMY}
---
TARGET FILE: "${filepath}"
Action: Open this file, read its contents (use OCR/Vision if needed), rename it to [Date]_[Entity]_[Type] format, categorize it, and MOVE it to the appropriate subfolder. If you cannot process it, move it to Quarantine/.
PROMPT_EOF
            # --- VERIFICATION STEP ---
            # If the file is still in the source folder root, the agent failed to move it.
            # Check if file still exists at original path
            if [ -f "$filepath" ]; then
                echo "⚠️  Agent finished but file was NOT moved: ${filename}"
                log_failure "$filename" "Agent failed to move file - still in Downloads root"
            else
                echo "✅ Successfully organized: ${filename}"
            fi
        else
            local exit_code=$?
            echo "❌ Process error on file ${filename}: exit code ${exit_code}"
            log_failure "$filename" "Process Error: exit code ${exit_code}"
        fi
        
        # Optional: Sleep briefly to prevent rate limits and allow clean Ctrl+C
        sleep 1
    done
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✨ Digital Janitor finished processing!"
    echo ""
    
    # Count remaining files
    local remaining
    remaining=$(find "$SOURCE_DIR" -maxdepth 1 -type f \
        ! -name "digital_janitor.sh" \
        ! -name "digital_janitor_failures.txt" \
        ! -name ".DS_Store" \
        ! -name ".*" | wc -l | tr -d ' ')
    
    if [ "$remaining" -gt 0 ]; then
        echo "📊 Remaining files in Downloads: ${remaining}"
        echo "   (Some may be in Quarantine/ or failed - check ${FAILED_LOG})"
    else
        echo "🎉 Downloads folder is completely organized!"
    fi
}

# --- MAIN EXECUTION ---

# Set up trap for graceful interruption
cleanup() {
    echo ""
    echo "🛑 Paused by user. Resume anytime by running the script again."
    echo "   Failed files are logged in: ${FAILED_LOG}"
    exit 0
}

trap cleanup SIGINT

echo "🧹 Digital Janitor - Downloads Folder Organizer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

organize_files

