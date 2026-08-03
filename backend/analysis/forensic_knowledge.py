FORENSIC_ORACLE = {
    "FAT32": {
        "recovery_strategy": "Scan for 0xE5 deletion markers in Directory Entries. Trace clusters via FAT mirror backup.",
        "intelligence": "Fragmented files may require bit-stream carving to reassemble their cluster chain."
    },
    "NTFS": {
        "recovery_strategy": "Parse $MFT (Master File Table). Analyze $LOGFILE for recent transactions. Replay journal to undo accidental deletions.",
        "intelligence": "Files smaller than 700 bytes may be resident in the MFT record and recoverable directly from it."
    },
    "EXT4": {
        "recovery_strategy": "Analyze Inode Bitmaps. Search for orphaned inodes in lost+found. Verify extent trees for large file reconstruction.",
        "intelligence": "Extent tree parsing and journal replay are used to rebuild files deleted after sequential writes."
    },
    "APFS": {
        "recovery_strategy": "Mount Container Superblock. Search for B-Tree node checkpoints to locate APFS snapshots.",
        "intelligence": "APFS copy-on-write design keeps historical versions that may survive in free space."
    },
    "SQLITE": {
        "recovery_strategy": "Search for 'SQLITE format 3' headers. Analyze WAL (Write Ahead Log) for uncommitted transactions in browser/messaging history.",
        "intelligence": "If a database was never vacuumed, deleted rows may remain on free list pages."
    },
    "TIME_STOMPING": {
        "detection": "Comparison of $SIA (Standard Information) vs $FNA (File Name) attributes. Mismatch > 1 second indicates anti-forensic activity.",
        "intelligence": "A mismatch between $SIA and $FNA timestamps may indicate anti-forensic timestamp manipulation."
    }
}

RECOVERY_PATTERNS = [
    {"signature": "49 44 33", "type": "MP3", "recovery": "Frame-header re-sync"},
    {"signature": "FF D8 FF E0", "type": "JPEG", "recovery": "Marker carving"},
    {"signature": "25 50 44 46", "type": "PDF", "recovery": "Trailer-based reconstruction"},
    {"signature": "50 4B 03 04", "type": "ZIP/DOCX", "recovery": "Local file header validation"}
]
