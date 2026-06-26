FORENSIC_ORACLE = {
    "FAT32": {
        "recovery_strategy": "Scan for 0xE5 deletion markers in Directory Entries. Trace clusters via FAT mirror backup.",
        "intelligence": "Detected potential fragmentation. C240 recommending bit-stream carving."
    },
    "NTFS": {
        "recovery_strategy": "Parse $MFT (Master File Table). Analyze $LOGFILE for recent transactions. Replay journal to undo accidental deletions.",
        "intelligence": "MFT residency analysis complete. Files < 700 bytes can be recovered from the record itself."
    },
    "EXT4": {
        "recovery_strategy": "Analyze Inode Bitmaps. Search for orphaned inodes in lost+found. Verify extent trees for large file reconstruction.",
        "intelligence": "Journaling re-syncing. Block allocation patterns suggest sequential write before deletion."
    },
    "APFS": {
        "recovery_strategy": "Mount Container Superblock. Search for B-Tree node checkpoints. Snapshot revert simulation active.",
        "intelligence": "Copy-on-write signatures identified. Historical versions available in free space."
    },
    "SQLITE": {
        "recovery_strategy": "Search for 'SQLITE format 3' headers. Analyze WAL (Write Ahead Log) for uncommitted transactions in browser/messaging history.",
        "intelligence": "Detected unvacuumed database. Deleted rows are still present in free list pages."
    },
    "TIME_STOMPING": {
        "detection": "Comparison of $SIA (Standard Information) vs $FNA (File Name) attributes. Mismatch > 1 second indicates anti-forensic activity.",
        "intelligence": "Anomalous timestamp detected. MFT entry sequence number doesn't match creation date."
    }
}

RECOVERY_PATTERNS = [
    {"signature": "49 44 33", "type": "MP3", "recovery": "Frame-header re-sync"},
    {"signature": "FF D8 FF E0", "type": "JPEG", "recovery": "Marker carving"},
    {"signature": "25 50 44 46", "type": "PDF", "recovery": "Trailer-based reconstruction"},
    {"signature": "50 4B 03 04", "type": "ZIP/DOCX", "recovery": "Local file header validation"}
]
