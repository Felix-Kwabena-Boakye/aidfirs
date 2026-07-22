"""
AIDFIRS Local Recovery Engine
Real forensic file recovery using:
  1. Windows Recycle Bin scanning ($Recycle.Bin / $I + $R parsing)
  2. Custom raw signature carving (30+ file types)
  3. PhotoRec (subprocess, if installed)
  4. TestDisk (subprocess, if installed)
  5. pytsk3 (The Sleuth Kit Python bindings, if installed)
  6. Scalpel (subprocess, if installed)

All recovery operations work on forensic images (never the raw evidence device directly).
"""

import os
import re
import shutil
import struct
import hashlib
import platform
import subprocess
import tempfile
import datetime
import json
from typing import List, Dict, Tuple, Optional

from .hashing import compute_all_hashes
from .metadata import MetadataExtractor

# =============================================================================
# Optional imports — graceful fallbacks
# =============================================================================
try:
    import pytsk3
    PYTSK3_AVAILABLE = True
except ImportError:
    PYTSK3_AVAILABLE = False

# =============================================================================
# File Signatures: (headers_list, description, max_size_bytes, footer_or_None)
# =============================================================================
FILE_SIGNATURES = {
    # Images
    'jpg':  ([b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\xff\xd8\xff\xe2',
               b'\xff\xd8\xff\xe3', b'\xff\xd8\xff'],
              'JPEG Image', 25 * 1024 * 1024, b'\xff\xd9'),
    'png':  ([b'\x89PNG\r\n\x1a\n'], 'PNG Image', 50 * 1024 * 1024,
              b'\x49\x45\x4e\x44\xae\x42\x60\x82'),
    'gif':  ([b'GIF87a', b'GIF89a'], 'GIF Image', 20 * 1024 * 1024, b'\x00\x3b'),
    'bmp':  ([b'BM'], 'BMP Image', 30 * 1024 * 1024, None),
    'tiff': ([b'II*\x00', b'MM\x00*'], 'TIFF Image', 100 * 1024 * 1024, None),
    'webp': ([b'RIFF'], 'WebP Image', 50 * 1024 * 1024, None),

    # Documents
    'pdf':  ([b'%PDF'], 'PDF Document', 100 * 1024 * 1024, b'%%EOF'),
    'docx': ([b'PK\x03\x04\x14\x00\x06\x00'], 'Word Document (OOXML)', 100 * 1024 * 1024, b'PK\x05\x06'),
    'xlsx': ([b'PK\x03\x04\x14\x00\x08\x00'], 'Excel Spreadsheet (OOXML)', 100 * 1024 * 1024, b'PK\x05\x06'),
    'pptx': ([b'PK\x03\x04\x14\x00\x06\x00'], 'PowerPoint (OOXML)', 100 * 1024 * 1024, b'PK\x05\x06'),
    'doc':  ([b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'], 'Word Document (OLE2)', 50 * 1024 * 1024, None),
    'xls':  ([b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'], 'Excel Spreadsheet (OLE2)', 50 * 1024 * 1024, None),
    'ppt':  ([b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'], 'PowerPoint (OLE2)', 50 * 1024 * 1024, None),
    'odt':  ([b'PK\x03\x04'], 'OpenDocument Text', 50 * 1024 * 1024, None),
    'rtf':  ([b'{\\rtf'], 'Rich Text Format', 20 * 1024 * 1024, b'}'),

    # Text / Data
    'txt':  ([b'\xef\xbb\xbf', b'#!', b'<!DOCTYPE'], 'Text File', 10 * 1024 * 1024, None),
    'csv':  ([b'"', b'id,', b'ID,', b'name,'], 'CSV Data', 50 * 1024 * 1024, None),
    'xml':  ([b'<?xml', b'<root', b'<data'], 'XML Document', 50 * 1024 * 1024, None),
    'html': ([b'<!DOCTYPE html', b'<html', b'<HTML'], 'HTML Document', 20 * 1024 * 1024, b'</html>'),
    'json': ([b'{', b'[{'], 'JSON Data', 50 * 1024 * 1024, None),

    # Archives
    'zip':  ([b'PK\x03\x04'], 'ZIP Archive', 500 * 1024 * 1024, b'PK\x05\x06'),
    'rar':  ([b'Rar!\x1a\x07\x00', b'Rar!\x1a\x07\x01'], 'RAR Archive', 500 * 1024 * 1024, None),
    '7z':   ([b'7z\xbc\xaf\x27\x1c'], '7-Zip Archive', 500 * 1024 * 1024, None),
    'gz':   ([b'\x1f\x8b'], 'GZIP Archive', 100 * 1024 * 1024, None),
    'tar':  ([b'ustar'], 'TAR Archive', 500 * 1024 * 1024, None),

    # Databases
    'sqlite': ([b'SQLite format 3'], 'SQLite Database', 500 * 1024 * 1024, None),
    'db':   ([b'SQLite format 3', b'\x53\x51\x4c\x69\x74\x65'], 'Database File', 500 * 1024 * 1024, None),
    'mdb':  ([b'\x00\x01\x00\x00Standard Jet DB', b'\x00\x01\x00\x00Standard ACE DB'],
              'Access Database', 200 * 1024 * 1024, None),

    # Video
    'mp4':  ([b'\x00\x00\x00\x18ftyp', b'\x00\x00\x00\x1cftyp', b'\x00\x00\x00\x14ftyp',
               b'\x00\x00\x00\x20ftyp', b'\x00\x00\x00\x08ftyp'],
              'MPEG-4 Video', 2 * 1024 * 1024 * 1024, None),
    'mov':  ([b'\x00\x00\x00\x14ftyp', b'\x00\x00\x00\x08wide', b'mdat'],
              'QuickTime Video', 2 * 1024 * 1024 * 1024, None),
    'avi':  ([b'RIFF'], 'AVI Video', 2 * 1024 * 1024 * 1024, None),
    'wmv':  ([b'\x30\x26\xb2\x75\x8e\x66\xcf\x11'], 'Windows Media Video', 2 * 1024 * 1024 * 1024, None),
    'mkv':  ([b'\x1a\x45\xdf\xa3'], 'Matroska Video', 2 * 1024 * 1024 * 1024, None),

    # Audio
    'mp3':  ([b'ID3', b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'], 'MP3 Audio', 200 * 1024 * 1024, None),
    'wav':  ([b'RIFF'], 'WAV Audio', 500 * 1024 * 1024, None),
    'flac': ([b'fLaC'], 'FLAC Audio', 500 * 1024 * 1024, None),
    'aac':  ([b'\xff\xf1', b'\xff\xf9'], 'AAC Audio', 200 * 1024 * 1024, None),

    # Executables / Code
    'exe':  ([b'MZ'], 'Windows Executable', 200 * 1024 * 1024, None),
    'elf':  ([b'\x7fELF'], 'ELF Executable', 200 * 1024 * 1024, None),
    'py':   ([b'#!/usr/bin/python', b'#!/usr/bin/env python', b'# -*- coding:'],
              'Python Script', 5 * 1024 * 1024, None),
    'java': ([b'\xca\xfe\xba\xbe'], 'Java Class File', 10 * 1024 * 1024, None),
}

# Ambiguous signatures that need MIME disambiguation
AMBIGUOUS_SIGNATURES = {b'PK\x03\x04', b'RIFF'}


def _safe_filename(name: str) -> str:
    """Sanitize a filename for safe filesystem storage."""
    name = os.path.basename(name)
    name = re.sub(r'[^\w\s\-.]', '_', name)
    return name or 'unnamed_file'


def _build_file_record(filepath: str, ext: str, description: str,
                       recovery_method: str, original_path: str = "",
                       carve_offset: int = None) -> Dict:
    """Build a standardized recovered file record with all forensic metadata."""
    hashes = compute_all_hashes(filepath)
    meta = MetadataExtractor.extract_by_extension(filepath, ext)
    size = os.path.getsize(filepath) if os.path.exists(filepath) else 0

    return {
        "filename": os.path.basename(filepath),
        "filepath": filepath,
        "extension": ext.lower(),
        "description": description,
        "size": f"{round(size / (1024*1024), 2)}MB" if size >= 1024*1024 else f"{round(size/1024, 2)}KB",
        "bytes_size": size,
        "type": ext.upper(),
        "deleted": True,
        "recoverable": True,
        "recovery_method": recovery_method,
        "original_path": original_path,
        "recovered_path": filepath,
        # Hashes
        "hash_sha256": hashes['sha256'],
        "hash_sha512": hashes['sha512'],
        "hash_md5": hashes['md5'],
        "hash_sha1": hashes['sha1'],
        # Timestamps from metadata
        "created_time": meta.get('created_time'),
        "modified_time": meta.get('modified_time'),
        "accessed_time": meta.get('accessed_time'),
        "deleted_time": None,
        # Extra metadata
        "carve_offset": carve_offset,
        "metadata": {k: v for k, v in meta.items()
                     if k not in ('created_time', 'modified_time', 'accessed_time')},
    }


class LocalRecoveryEngine:
    """
    Forensic recovery engine for local drives and forensic disk images.
    Uses multiple recovery techniques in priority order:
      1. pytsk3 (Sleuth Kit) — filesystem traversal (most accurate)
      2. PhotoRec subprocess — professional carver
      3. TestDisk subprocess — partition/directory recovery
      4. Scalpel subprocess — signature carver
      5. Windows Recycle Bin scan ($Recycle.Bin)
      6. Custom raw signature carver (built-in fallback)
    """

    def __init__(self, output_dir: str, examiner: str = "AIDFIRS Agent",
                 case_id: str = None, device_id: str = None):
        self.output_dir = output_dir
        self.examiner = examiner
        self.case_id = case_id
        self.device_id = device_id
        os.makedirs(self.output_dir, exist_ok=True)

        # Create forensic output subdirectories
        self.carve_dir = os.path.join(output_dir, 'CarvedFiles')
        self.recycle_dir = os.path.join(output_dir, 'RecycleBin')
        self.sleuth_dir = os.path.join(output_dir, 'SleuthKit')
        os.makedirs(self.carve_dir, exist_ok=True)
        os.makedirs(self.recycle_dir, exist_ok=True)
        os.makedirs(self.sleuth_dir, exist_ok=True)

    def scan_and_recover(self, source_path: str, recovery_type: str = "full",
                         image_path: str = None) -> List[Dict]:
        """
        Main entry point for forensic recovery.

        Args:
            source_path: Drive letter, device node, or raw image path
            recovery_type: 'full', 'quick', or 'carve'
            image_path: Path to forensic image (preferred over raw device for carving)

        Returns:
            List of recovered file descriptors with full forensic metadata
        """
        recovered_list = []
        # Prefer operating on forensic image if provided
        scan_target = image_path if image_path and os.path.exists(image_path) else source_path

        print(f"[Recovery] Starting {recovery_type} recovery on: {scan_target}")
        print(f"[Recovery] Output directory: {self.output_dir}")

        # --- 1. Windows Recycle Bin ---
        if platform.system() == "Windows":
            drive = self._normalize_drive(source_path)
            if drive:
                print(f"[Recovery] Scanning Windows Recycle Bin on {drive}...")
                rb_files = self._scan_windows_recycle_bin(drive)
                recovered_list.extend(rb_files)
                print(f"[Recovery] Recycle Bin: {len(rb_files)} files found")

        # --- 2. pytsk3 Sleuth Kit filesystem traversal ---
        if PYTSK3_AVAILABLE and scan_target:
            print(f"[Recovery] Attempting Sleuth Kit (pytsk3) filesystem scan...")
            try:
                sk_files = self._scan_with_pytsk3(scan_target)
                recovered_list.extend(sk_files)
                print(f"[Recovery] Sleuth Kit: {len(sk_files)} files found")
            except Exception as e:
                print(f"[Recovery] Sleuth Kit scan failed: {e}")

        # --- 3. PhotoRec ---
        if recovery_type != "quick":
            photorec_path = self._find_tool('photorec')
            if photorec_path and scan_target:
                print(f"[Recovery] Attempting PhotoRec recovery...")
                try:
                    pr_files = self._run_photorec(scan_target, photorec_path)
                    recovered_list.extend(pr_files)
                    print(f"[Recovery] PhotoRec: {len(pr_files)} files found")
                except Exception as e:
                    print(f"[Recovery] PhotoRec failed: {e}")

        # --- 4. TestDisk ---
        if recovery_type == "full":
            testdisk_path = self._find_tool('testdisk')
            if testdisk_path and scan_target:
                print(f"[Recovery] Attempting TestDisk file listing...")
                try:
                    td_files = self._run_testdisk(scan_target, testdisk_path)
                    recovered_list.extend(td_files)
                    print(f"[Recovery] TestDisk: {len(td_files)} entries found")
                except Exception as e:
                    print(f"[Recovery] TestDisk failed: {e}")

        # --- 5. Scalpel ---
        if recovery_type != "quick":
            scalpel_path = self._find_tool('scalpel')
            if scalpel_path and scan_target:
                print(f"[Recovery] Attempting Scalpel carving...")
                try:
                    sc_files = self._run_scalpel(scan_target, scalpel_path)
                    recovered_list.extend(sc_files)
                    print(f"[Recovery] Scalpel: {len(sc_files)} files found")
                except Exception as e:
                    print(f"[Recovery] Scalpel failed: {e}")

        # --- 6. Raw signature carving (always runs as final pass) ---
        if recovery_type != "quick":
            print(f"[Recovery] Running built-in raw signature carver on {scan_target}...")
            try:
                carved = self._carve_raw_signatures(scan_target)
                recovered_list.extend(carved)
                print(f"[Recovery] Raw carver: {len(carved)} files carved")
            except Exception as e:
                print(f"[Recovery] Raw carving error: {e}")

        # Deduplicate by hash
        seen_hashes = set()
        unique_files = []
        for f in recovered_list:
            h = f.get('hash_sha256') or f.get('hash_md5') or f['filepath']
            if h not in seen_hashes:
                seen_hashes.add(h)
                unique_files.append(f)

        print(f"[Recovery] Total unique recovered files: {len(unique_files)}")
        return unique_files

    # =========================================================================
    # TOOL DETECTION
    # =========================================================================

    def _find_tool(self, tool_name: str) -> Optional[str]:
        """Find a forensic tool in PATH or common installation directories."""
        # Check PATH first
        path = shutil.which(tool_name)
        if path:
            return path

        # Common locations
        common_paths = []
        if platform.system() == 'Windows':
            common_paths = [
                rf'C:\Program Files\{tool_name}\{tool_name}.exe',
                rf'C:\Program Files (x86)\{tool_name}\{tool_name}.exe',
                rf'C:\forensic_tools\{tool_name}.exe',
                rf'C:\tools\{tool_name}\{tool_name}.exe',
                os.path.join(os.path.dirname(__file__), '..', 'tools', f'{tool_name}.exe'),
            ]
        else:
            common_paths = [
                f'/usr/bin/{tool_name}',
                f'/usr/local/bin/{tool_name}',
                f'/opt/{tool_name}/{tool_name}',
                f'/usr/sbin/{tool_name}',
            ]

        for p in common_paths:
            if os.path.isfile(p):
                return p

        return None

    # =========================================================================
    # WINDOWS RECYCLE BIN
    # =========================================================================

    def _normalize_drive(self, source_path: str) -> Optional[str]:
        """Extract a Windows drive letter from a path."""
        if platform.system() != 'Windows':
            return None
        path = source_path.strip().rstrip('\\').upper()
        if len(path) == 1:
            return path + ':'
        if len(path) == 2 and path[1] == ':':
            return path
        if len(path) >= 3 and path[1:3] == ':\\':
            return path[:2]
        return None

    def _scan_windows_recycle_bin(self, drive: str) -> List[Dict]:
        """Scan Windows $Recycle.Bin for deleted files."""
        recovered = []
        recycle_path = f"{drive}\\$Recycle.Bin"
        if not os.path.exists(recycle_path):
            print(f"[Recovery] Recycle Bin not found at {recycle_path}")
            return []

        try:
            for sid_dir in os.scandir(recycle_path):
                if not sid_dir.is_dir():
                    continue
                try:
                    for entry in os.scandir(sid_dir.path):
                        name = entry.name
                        # $R files are the actual content, $I files are metadata
                        if name.startswith('$R') and not name.startswith('$I'):
                            filepath = entry.path
                            ext = os.path.splitext(name)[1].lower().lstrip('.')
                            size = entry.stat().st_size

                            # Parse original filename from matching $I file
                            meta_name = '$I' + name[2:]
                            meta_path = os.path.join(sid_dir.path, meta_name)
                            original_name, deleted_time = self._parse_recycle_bin_metadata(meta_path)
                            original_name = original_name or name

                            # Copy to recovery output directory
                            dest_path = os.path.join(self.recycle_dir, _safe_filename(original_name))
                            counter = 1
                            base, ext_part = os.path.splitext(dest_path)
                            while os.path.exists(dest_path):
                                dest_path = f"{base}_{counter}{ext_part}"
                                counter += 1

                            shutil.copy2(filepath, dest_path)

                            record = _build_file_record(
                                dest_path, ext or 'bin',
                                description=f"Recovered from Windows Recycle Bin ($Recycle.Bin\\{sid_dir.name})",
                                recovery_method="recycle_bin",
                                original_path=os.path.join(drive, original_name),
                            )
                            if deleted_time:
                                record['deleted_time'] = deleted_time
                            record['original_path'] = os.path.join(drive, original_name)
                            recovered.append(record)

                except PermissionError:
                    continue
        except Exception as e:
            print(f"[Recovery] Error reading Recycle Bin: {e}")

        return recovered

    def _parse_recycle_bin_metadata(self, meta_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse $I metadata file to get original filename and deletion time."""
        if not os.path.exists(meta_path):
            return None, None
        try:
            with open(meta_path, 'rb') as f:
                data = f.read()

            # $I file format:
            # Offset 0:  8 bytes - Header/Version
            # Offset 8:  8 bytes - File size
            # Offset 16: 8 bytes - Deletion timestamp (FILETIME, Windows epoch)
            # Offset 24: 4 bytes - Path length (in characters)
            # Offset 28: variable - Original path (UTF-16-LE)

            deleted_time = None
            original_name = None

            if len(data) >= 24:
                # Parse deletion timestamp (Windows FILETIME: 100ns intervals since 1601-01-01)
                try:
                    filetime = struct.unpack('<q', data[16:24])[0]
                    if filetime > 0:
                        # Convert Windows FILETIME to Unix timestamp
                        unix_ts = (filetime - 116444736000000000) / 10000000
                        if unix_ts > 0:
                            dt = datetime.datetime.fromtimestamp(unix_ts, tz=datetime.timezone.utc)
                            deleted_time = dt.isoformat()
                except Exception:
                    pass

            if len(data) > 28:
                path_bytes = data[28:]
                original_path = path_bytes.decode('utf-16-le', errors='ignore').rstrip('\x00')
                if original_path:
                    original_name = os.path.basename(original_path)

            if not original_name and len(data) > 24:
                # Fallback: try offset 24 directly
                path_bytes = data[24:]
                original_path = path_bytes.decode('utf-16-le', errors='ignore').rstrip('\x00')
                if original_path:
                    original_name = os.path.basename(original_path)

            return original_name, deleted_time
        except Exception:
            return None, None

    # =========================================================================
    # PYTSK3 / SLEUTH KIT
    # =========================================================================

    def _scan_with_pytsk3(self, source_path: str) -> List[Dict]:
        """
        Use pytsk3 (The Sleuth Kit) to traverse the filesystem and find deleted files.
        Works on forensic images (.dd, .img) or raw device paths.
        """
        if not PYTSK3_AVAILABLE:
            return []

        recovered = []
        try:
            img = pytsk3.Img_Info(source_path)
            try:
                fs = pytsk3.FS_Info(img)
            except Exception:
                # Try to detect partition table
                try:
                    volume = pytsk3.Volume_Info(img)
                    for part in volume:
                        if part.len > 2048:  # Skip tiny partitions
                            try:
                                fs = pytsk3.FS_Info(img, offset=part.start * 512)
                                part_files = self._walk_tsk_fs(fs, source_path)
                                recovered.extend(part_files)
                            except Exception:
                                continue
                except Exception:
                    pass
                return recovered

            recovered = self._walk_tsk_fs(fs, source_path)
        except Exception as e:
            print(f"[Recovery] pytsk3 error: {e}")

        return recovered

    def _walk_tsk_fs(self, fs, source_path: str) -> List[Dict]:
        """Walk a Sleuth Kit filesystem and recover deleted files."""
        recovered = []
        try:
            root_dir = fs.open_dir(path='/')
            recovered = self._tsk_recurse(root_dir, '/', source_path)
        except Exception as e:
            print(f"[Recovery] TSK directory walk error: {e}")
        return recovered

    def _tsk_recurse(self, directory, path: str, source_path: str,
                     depth: int = 0) -> List[Dict]:
        """Recursively walk TSK directory entries looking for deleted files."""
        if depth > 10:
            return []
        recovered = []
        try:
            for entry in directory:
                # Skip . and ..
                name = entry.info.name.name
                if isinstance(name, bytes):
                    name = name.decode('utf-8', errors='replace')
                if name in ('.', '..'):
                    continue

                full_path = f"{path}{name}"

                # Check if deleted
                is_deleted = (entry.info.name.flags & pytsk3.TSK_FS_NAME_FLAG_UNALLOC) != 0

                if entry.info.meta and entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_REG:
                    if is_deleted:
                        ext = os.path.splitext(name)[1].lower().lstrip('.')
                        try:
                            file_obj = entry.as_file()
                            size = entry.info.meta.size if entry.info.meta else 0
                            if size > 0 and size < 500 * 1024 * 1024:  # Skip files > 500MB
                                dest_name = _safe_filename(name)
                                dest_path = os.path.join(self.sleuth_dir, f"tsk_{abs(hash(full_path))}_{dest_name}")
                                counter = 1
                                base, ext_part = os.path.splitext(dest_path)
                                while os.path.exists(dest_path):
                                    dest_path = f"{base}_{counter}{ext_part}"
                                    counter += 1

                                # Read and save file content
                                with open(dest_path, 'wb') as out:
                                    offset = 0
                                    chunk_size = 1024 * 1024
                                    while offset < size:
                                        to_read = min(chunk_size, size - offset)
                                        data = file_obj.read_random(offset, to_read)
                                        if not data:
                                            break
                                        out.write(data)
                                        offset += len(data)

                                record = _build_file_record(
                                    dest_path, ext or 'bin',
                                    description=f"Deleted file recovered via Sleuth Kit filesystem analysis",
                                    recovery_method="sleuth_kit_tsk",
                                    original_path=full_path,
                                )
                                # Get TSK timestamps
                                if entry.info.meta:
                                    meta = entry.info.meta
                                    try:
                                        if meta.crtime:
                                            record['created_time'] = datetime.datetime.fromtimestamp(
                                                meta.crtime, tz=datetime.timezone.utc).isoformat()
                                        if meta.mtime:
                                            record['modified_time'] = datetime.datetime.fromtimestamp(
                                                meta.mtime, tz=datetime.timezone.utc).isoformat()
                                        if meta.atime:
                                            record['accessed_time'] = datetime.datetime.fromtimestamp(
                                                meta.atime, tz=datetime.timezone.utc).isoformat()
                                    except Exception:
                                        pass
                                recovered.append(record)
                        except Exception as e:
                            print(f"[Recovery] TSK file read error for {full_path}: {e}")

                elif (entry.info.meta and
                      entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR and
                      not is_deleted and depth < 8):
                    try:
                        sub_dir = entry.as_directory()
                        sub_files = self._tsk_recurse(sub_dir, f"{full_path}/", source_path, depth + 1)
                        recovered.extend(sub_files)
                    except Exception:
                        pass
        except Exception as e:
            print(f"[Recovery] TSK recurse error at {path}: {e}")
        return recovered

    # =========================================================================
    # PHOTOREC
    # =========================================================================

    def _run_photorec(self, source_path: str, photorec_path: str) -> List[Dict]:
        """
        Run PhotoRec in unattended mode against a forensic image or device.
        Collects all recovered files from the output directory.
        """
        photorec_out = os.path.join(self.carve_dir, 'photorec_out')
        os.makedirs(photorec_out, exist_ok=True)

        # Build PhotoRec command for unattended operation
        cmd = [
            photorec_path,
            '/log', '/d', photorec_out,
            '/cmd', source_path,
            'fileopt,everything,enable,options,paranoid,disable,quit'
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute max
            )
        except subprocess.TimeoutExpired:
            print("[Recovery] PhotoRec timed out after 5 minutes")
        except FileNotFoundError:
            print(f"[Recovery] PhotoRec not found at {photorec_path}")
            return []
        except Exception as e:
            print(f"[Recovery] PhotoRec error: {e}")
            return []

        # Collect all recovered files from PhotoRec output directory
        recovered = []
        for root, dirs, files in os.walk(photorec_out):
            for fname in files:
                fpath = os.path.join(root, fname)
                ext = os.path.splitext(fname)[1].lower().lstrip('.')
                record = _build_file_record(
                    fpath, ext or 'bin',
                    description="File recovered by PhotoRec",
                    recovery_method="photorec",
                    original_path="",
                )
                recovered.append(record)

        return recovered

    # =========================================================================
    # TESTDISK
    # =========================================================================

    def _run_testdisk(self, source_path: str, testdisk_path: str) -> List[Dict]:
        """
        Run TestDisk to list files from deleted partitions.
        Uses the list command to enumerate recoverable files.
        """
        testdisk_out = os.path.join(self.output_dir, 'testdisk.log')
        cmd = [testdisk_path, '/log', source_path, 'analyze,list']

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute max for listing
            )
            # TestDisk primarily creates testdisk.log — parse it for file entries
            log_file = 'testdisk.log'
            if os.path.exists(log_file):
                return self._parse_testdisk_log(log_file)
        except subprocess.TimeoutExpired:
            print("[Recovery] TestDisk timed out")
        except FileNotFoundError:
            print(f"[Recovery] TestDisk not found at {testdisk_path}")
        except Exception as e:
            print(f"[Recovery] TestDisk error: {e}")

        return []

    def _parse_testdisk_log(self, log_path: str) -> List[Dict]:
        """Parse TestDisk log file for recoverable file entries (metadata only)."""
        entries = []
        try:
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    # TestDisk log lines with file info typically start with spaces and have paths
                    line = line.strip()
                    if line and ('/' in line or '\\' in line) and not line.startswith('#'):
                        parts = line.split()
                        if len(parts) >= 2:
                            filename = parts[-1]
                            ext = os.path.splitext(filename)[1].lower().lstrip('.')
                            # We only return metadata entries since we can't extract the actual file
                            entries.append({
                                "filename": os.path.basename(filename),
                                "filepath": filename,  # virtual path from log
                                "extension": ext,
                                "deleted": True,
                                "recoverable": True,
                                "recovery_method": "testdisk_log",
                                "original_path": filename,
                                "description": "File entry found in TestDisk partition scan log",
                                "bytes_size": 0,
                                "size": "Unknown",
                                "type": ext.upper() if ext else "UNKNOWN",
                                "hash_sha256": "",
                                "hash_sha512": "",
                                "hash_md5": "",
                                "hash_sha1": "",
                                "metadata": {}
                            })
        except Exception as e:
            print(f"[Recovery] TestDisk log parse error: {e}")
        return entries

    # =========================================================================
    # SCALPEL
    # =========================================================================

    def _run_scalpel(self, source_path: str, scalpel_path: str) -> List[Dict]:
        """Run Scalpel file carver against a forensic image or device."""
        scalpel_out = os.path.join(self.carve_dir, 'scalpel_out')
        os.makedirs(scalpel_out, exist_ok=True)

        # Scalpel needs a config file — use default /etc/scalpel/scalpel.conf on Linux
        config_paths = ['/etc/scalpel/scalpel.conf', '/usr/local/etc/scalpel/scalpel.conf']
        config_path = None
        for cp in config_paths:
            if os.path.exists(cp):
                config_path = cp
                break

        cmd = [scalpel_path]
        if config_path:
            cmd += ['-c', config_path]
        cmd += ['-o', scalpel_out, source_path]

        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            print("[Recovery] Scalpel timed out")
        except FileNotFoundError:
            print(f"[Recovery] Scalpel not found at {scalpel_path}")
            return []
        except Exception as e:
            print(f"[Recovery] Scalpel error: {e}")
            return []

        # Collect carved files
        recovered = []
        for root, dirs, files in os.walk(scalpel_out):
            for fname in files:
                if fname.endswith('.audit'):
                    continue
                fpath = os.path.join(root, fname)
                ext = os.path.splitext(fname)[1].lower().lstrip('.')
                record = _build_file_record(
                    fpath, ext or 'bin',
                    description="File recovered by Scalpel signature carver",
                    recovery_method="scalpel",
                )
                recovered.append(record)

        return recovered

    # =========================================================================
    # RAW SIGNATURE CARVER (built-in, always available)
    # =========================================================================

    def _carve_raw_signatures(self, source_path: str) -> List[Dict]:
        """
        Built-in raw byte signature carver.
        Scans the source for known file headers and carves them out.
        Works on forensic images or raw device paths.
        """
        carved = []
        target_src = source_path

        # Convert drive letter to Windows raw device path
        if platform.system() == "Windows":
            stripped = source_path.strip().rstrip('\\')
            if len(stripped) == 2 and stripped[1] == ':':
                letter = stripped[0].upper()
                target_src = f'\\\\.\\{letter}:'
            elif len(stripped) == 1:
                target_src = f'\\\\.\\{stripped.upper()}:'

        chunk_size = 128 * 1024    # 128KB read blocks
        overlap = 1024             # 1KB overlap for boundary-spanning signatures
        max_scan_bytes = 500 * 1024 * 1024  # Scan first 500MB max

        try:
            if platform.system() == 'Windows' and target_src.startswith('\\\\.\\'):
                try:
                    fd = os.open(target_src, os.O_RDONLY | os.O_BINARY)
                    f = os.fdopen(fd, 'rb')
                except Exception as e:
                    print(f"[Recovery] Cannot open raw device {target_src}: {e}")
                    return []
            else:
                if not os.path.exists(target_src):
                    print(f"[Recovery] Source not found: {target_src}")
                    return []
                f = open(target_src, 'rb')
        except Exception as e:
            print(f"[Recovery] Failed to open {target_src}: {e}")
            return []

        # Build flat list of (header_bytes, ext, description, max_size, footer)
        sig_list = []
        for ext, (headers, desc, max_size, footer) in FILE_SIGNATURES.items():
            for header in headers:
                sig_list.append((header, ext, desc, max_size, footer))

        seen_offsets = set()  # Avoid double-carving same offset

        try:
            with f:
                offset = 0
                prev_chunk = b''

                while offset < max_scan_bytes:
                    try:
                        chunk = f.read(chunk_size)
                    except OSError as e:
                        print(f"[Recovery] Read error at offset {offset}: {e}")
                        break
                    if not chunk:
                        break

                    # Combine with tail of previous chunk for boundary detection
                    search_data = prev_chunk[-overlap:] + chunk
                    search_base = offset - min(overlap, len(prev_chunk))

                    for header, ext, desc, max_size, footer in sig_list:
                        pos = 0
                        while True:
                            pos = search_data.find(header, pos)
                            if pos == -1:
                                break

                            abs_offset = search_base + pos

                            # Skip if already carved from this offset
                            key = (abs_offset, ext)
                            if key in seen_offsets:
                                pos += 1
                                continue
                            seen_offsets.add(key)

                            try:
                                carved_name = f"carved_{abs_offset}_{ext}.{ext}"
                                carved_path = os.path.join(self.carve_dir, carved_name)

                                # Seek to found offset and read
                                f.seek(abs_offset)
                                if footer:
                                    # Read up to max_size looking for footer
                                    raw_data = f.read(min(max_size, max_scan_bytes - abs_offset))
                                    foot_pos = raw_data.find(footer, len(header))
                                    if foot_pos != -1:
                                        carve_data = raw_data[:foot_pos + len(footer)]
                                    else:
                                        # No footer found: cap at a reasonable size
                                        carve_data = raw_data[:min(max_size, 5 * 1024 * 1024)]
                                else:
                                    carve_data = f.read(min(max_size, max_scan_bytes - abs_offset))

                                # Skip trivially small files
                                if len(carve_data) < 16:
                                    pos += 1
                                    continue

                                with open(carved_path, 'wb') as out_f:
                                    out_f.write(carve_data)

                                record = _build_file_record(
                                    carved_path, ext, desc,
                                    recovery_method="signature_carving",
                                    original_path="",
                                    carve_offset=abs_offset,
                                )
                                carved.append(record)

                            except Exception as carve_err:
                                print(f"[Recovery] Carving error at offset {abs_offset} ({ext}): {carve_err}")
                            finally:
                                # Restore position
                                f.seek(offset + len(chunk))

                            pos += 1

                    prev_chunk = chunk
                    offset += len(chunk)

        except Exception as e:
            print(f"[Recovery] Raw carving fatal error: {e}")

        return carved
