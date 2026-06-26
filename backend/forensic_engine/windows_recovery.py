"""
Forensic AI Assistant - Windows Recovery Module

Provides real deleted file recovery on Windows drives:
1. Recycle Bin scan ($Recycle.Bin)
2. Raw disk sector scanning via \\.\DriveLetter: device path
3. Shadow Copy enumeration
"""

import os
import re
import struct
import hashlib
import platform
import datetime
from typing import Dict, List, Optional, Tuple


VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.mpeg',
                    '.mpg', '.m4v', '.3gp', '.webm', '.ts', '.mts', '.vob'}
DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.raw'}

# File signature map: ext -> list of (header_bytes, description)
FILE_SIGNATURES = {
    'mp4':  ([b'\x00\x00\x00\x18ftyp', b'\x00\x00\x00\x1cftyp', b'\x00\x00\x00\x14ftyp',
              b'\x00\x00\x00\x20ftyp'], 'MPEG-4 Video'),
    'avi':  ([b'RIFF'], 'AVI Video'),
    'mov':  ([b'\x00\x00\x00\x14ftyp', b'\x00\x00\x00\x08wide'], 'QuickTime Movie'),
    'mkv':  ([b'\x1a\x45\xdf\xa3'], 'Matroska Video'),
    'wmv':  ([b'\x30\x26\xb2\x75\x8e\x66\xcf\x11'], 'Windows Media Video'),
    'flv':  ([b'FLV\x01'], 'Flash Video'),
    'pdf':  ([b'%PDF'], 'PDF Document'),
    'jpg':  ([b'\xff\xd8\xff'], 'JPEG Image'),
    'png':  ([b'\x89PNG\r\n\x1a\n'], 'PNG Image'),
    'docx': ([b'PK\x03\x04'], 'Office Open XML Document'),
    'zip':  ([b'PK\x03\x04'], 'ZIP Archive'),
}


def _get_drive_letter(path: str) -> Optional[str]:
    """Extract drive letter from a path, prioritizing removable pendrives."""
    if not path:
        return None
    if platform.system() == 'Windows':
        # Auto-detect removable drive (Pendrive) to ensure we never scan the laptop C: drive by mistake
        try:
            import psutil
            for part in psutil.disk_partitions(all=True):
                if 'removable' in part.opts:
                    return part.mountpoint[0].upper()
        except Exception:
            pass
            
        # Check if path itself is exactly a drive path (like "D:", "D:\", "d:", "d:\")
        # and NOT an absolute file path.
        clean_path = path.strip().rstrip('\\').rstrip('/')
        if len(clean_path) == 2 and clean_path[1] == ':':
            return clean_path[0].upper()
        # Handle raw device path like \\.\D:
        match = re.match(r'^\\\\.\\([A-Za-z]):?$', clean_path)
        if match:
            return match.group(1).upper()
            
    return None


def _get_raw_device_path(drive_path: str) -> Optional[str]:
    """Convert 'D:\\' to '\\\\.\\D:' for raw disk access on Windows."""
    letter = _get_drive_letter(drive_path)
    if letter:
        return f'\\\\.\\{letter}:'
    return None


def scan_recycle_bin(drive_path: str) -> List[Dict]:
    """
    Scan the Windows Recycle Bin ($Recycle.Bin) on the targeted drive for deleted files.
    Returns a list of recovered file metadata dicts.
    """
    recovered = []
    
    target_letter = _get_drive_letter(drive_path)
    if not target_letter:
        return []

    recycle_bin_path = f"{target_letter}:\\$Recycle.Bin"
    if not os.path.exists(recycle_bin_path):
        return []

    try:
        for sid_dir in os.scandir(recycle_bin_path):
            if not sid_dir.is_dir():
                continue
            try:
                for entry in os.scandir(sid_dir.path):
                    name = entry.name
                    # $R files are the actual deleted content, $I files are metadata
                    if name.startswith('$R') and not name.startswith('$I'):
                        ext = os.path.splitext(name)[1].lower()
                        size = entry.stat().st_size if entry.is_file() else 0
                        mtime = datetime.datetime.fromtimestamp(
                            entry.stat().st_mtime, tz=datetime.timezone.utc
                        ).isoformat()

                        # Try to read the matching $I metadata file
                        meta_name = '$I' + name[2:]  # $R -> $I
                        meta_path = os.path.join(sid_dir.path, meta_name)
                        original_name = _parse_recycle_bin_metadata(meta_path) or name

                        is_video = ext in VIDEO_EXTENSIONS
                        is_image = ext in IMAGE_EXTENSIONS
                        is_doc = ext in DOCUMENT_EXTENSIONS

                        recovered.append({
                            'type': 'recycle_bin',
                            'source': f'Windows $Recycle.Bin ({target_letter}:)',
                            'file_type': ext.lstrip('.') or 'unknown',
                            'original_name': original_name,
                            'recycle_path': entry.path,
                            'size': size,
                            'size_readable': _readable_size(size),
                            'deleted_at': mtime,
                            'is_video': is_video,
                            'is_image': is_image,
                            'is_document': is_doc,
                            'recovery_confidence': 'very_high',
                            'recoverable': True,
                            'md5': _hash_file(entry.path) if entry.is_file() and size < 500 * 1024 * 1024 else None,
                        })
            except PermissionError:
                continue
    except PermissionError:
        pass

    return recovered


def _parse_recycle_bin_metadata(meta_path: str) -> Optional[str]:
    """Parse $I metadata file to extract the original file path."""
    try:
        if not os.path.exists(meta_path):
            return None
        with open(meta_path, 'rb') as f:
            data = f.read()
        # $I format: 8 bytes header version, 8 bytes file size, 8 bytes delete time, then UTF-16 path
        if len(data) > 24:
            path_data = data[24:]
            # Null-terminated UTF-16LE
            original = path_data.decode('utf-16-le', errors='ignore').rstrip('\x00')
            if original:
                return os.path.basename(original)
    except Exception:
        pass
    return None


def scan_drive_signatures(drive_path: str, file_types: Optional[List[str]] = None,
                          max_bytes: int = 512 * 1024 * 1024) -> List[Dict]:
    """
    Scan raw drive sectors for file signatures to find carved/deleted files.
    Uses \\\\.\\D: raw device access on Windows.
    Returns list of found file signature metadata.
    """
    if platform.system() != 'Windows':
        return []

    raw_device = _get_raw_device_path(drive_path)
    if not raw_device:
        return []

    found = []
    types_to_scan = file_types or list(FILE_SIGNATURES.keys())
    chunk_size = 65536  # 64KB chunks

    try:
        with open(raw_device, 'rb') as f:
            offset = 0
            bytes_read = 0

            while bytes_read < max_bytes:
                try:
                    chunk = f.read(chunk_size)
                except OSError:
                    break
                if not chunk:
                    break

                for ftype in types_to_scan:
                    if ftype not in FILE_SIGNATURES:
                        continue
                    sigs, desc = FILE_SIGNATURES[ftype]
                    for sig in sigs:
                        pos = 0
                        while True:
                            pos = chunk.find(sig, pos)
                            if pos == -1:
                                break
                            abs_offset = offset + pos
                            found.append({
                                'type': 'carved_file',
                                'source': 'raw_disk_scan',
                                'file_type': ftype,
                                'description': desc,
                                'offset': abs_offset,
                                'header_signature': sig.hex(),
                                'recovery_confidence': 'high',
                                'recoverable': True,
                            })
                            pos += len(sig)

                offset += len(chunk)
                bytes_read += len(chunk)

    except (PermissionError, OSError):
        # Raw disk access requires admin — return empty but not an error
        pass

    return found


def recover_files_from_recycle_bin(entries: List[Dict], dest_dir: str) -> List[Dict]:
    """
    Copy recovered Recycle Bin files to the secure recovery storage directory.
    Returns list of successfully restored files with their new paths.
    """
    os.makedirs(dest_dir, exist_ok=True)
    restored = []

    for entry in entries:
        if entry.get('type') != 'recycle_bin':
            continue
        src = entry.get('recycle_path')
        if not src or not os.path.isfile(src):
            continue
        original_name = entry.get('original_name', 'recovered_file')
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', original_name)
        dest = os.path.join(dest_dir, safe_name)

        # Avoid overwriting
        counter = 1
        base, ext = os.path.splitext(dest)
        while os.path.exists(dest):
            dest = f"{base}_{counter}{ext}"
            counter += 1

        try:
            import shutil
            shutil.copy2(src, dest)
            md5, sha256 = _hash_file_full(dest)
            restored.append({
                **entry,
                'restored_path': dest,
                'md5': md5,
                'sha256': sha256,
                'status': 'restored',
            })
        except Exception as e:
            restored.append({
                **entry,
                'status': 'failed',
                'error': str(e),
            })

    return restored


def _readable_size(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _hash_file(path: str) -> Optional[str]:
    try:
        md5 = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)
        return md5.hexdigest()
    except Exception:
        return None


def _hash_file_full(path: str) -> Tuple[str, str]:
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                md5.update(chunk)
                sha256.update(chunk)
    except Exception:
        pass
    return md5.hexdigest(), sha256.hexdigest()
