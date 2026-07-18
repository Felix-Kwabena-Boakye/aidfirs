import os
import re
import struct
import hashlib
import platform
import datetime
from typing import List, Dict, Tuple, Optional

from .hashing import compute_file_hashes
from .metadata import MetadataExtractor

# File signatures mapping: extension -> (headers, description, max_size, footer)
FILE_SIGNATURES = {
    'jpg': ([b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\xff\xd8\xff\xe2', b'\xff\xd8\xff'], 'JPEG Image', 10 * 1024 * 1024, b'\xff\xd9'),
    'png': ([b'\x89PNG\r\n\x1a\n'], 'PNG Image', 15 * 1024 * 1024, b'\x49\x45\x4e\x44\xae\x42\x60\x82'),
    'pdf': ([b'%PDF'], 'PDF Document', 50 * 1024 * 1024, b'%%EOF'),
    'mp4': ([b'\x00\x00\x00\x18ftyp', b'\x00\x00\x00\x1cftyp', b'\x00\x00\x00\x14ftyp', b'\x00\x00\x00\x20ftyp'], 'MPEG-4 Video', 500 * 1024 * 1024, None),
    'zip': ([b'PK\x03\x04'], 'ZIP Archive', 100 * 1024 * 1024, b'\x50\x4b\x05\x06'),
    'docx': ([b'PK\x03\x04\x14\x00\x06\x00'], 'Office Open XML Document', 50 * 1024 * 1024, b'\x50\x4b\x05\x06'),
    'xlsx': ([b'PK\x03\x04\x14\x00\x06\x00'], 'Office Open XML Spreadsheet', 50 * 1024 * 1024, b'\x50\x4b\x05\x06'),
}

class LocalRecoveryEngine:
    """Forensic recovery engine for local drives and partition images."""
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def scan_and_recover(self, source_path: str, recovery_type: str = "full") -> List[Dict]:
        """
        Scan a drive letter, device node, or raw image file.
        Recovers files and returns list of recovered file descriptors.
        """
        recovered_list = []

        # 1. If Windows and source is drive letter (e.g. D:), try Recycle Bin scan first
        if platform.system() == "Windows" and len(source_path) <= 3:
            drive = source_path[0].upper() + ":"
            print(f"[Recovery] Scanning Recycle Bin on Windows drive {drive}...")
            recovered_list.extend(self._scan_windows_recycle_bin(drive))

        # 2. Raw signature carving (works on raw files and raw disk streams)
        print(f"[Recovery] Scanning raw bytes for signatures on: {source_path}...")
        recovered_list.extend(self._carve_raw_signatures(source_path))

        return recovered_list

    def _scan_windows_recycle_bin(self, drive: str) -> List[Dict]:
        recovered = []
        recycle_path = f"{drive}\\$Recycle.Bin"
        if not os.path.exists(recycle_path):
            return []

        try:
            for sid_dir in os.scandir(recycle_path):
                if not sid_dir.is_dir():
                    continue
                try:
                    for entry in os.scandir(sid_dir.path):
                        name = entry.name
                        # Recycle Bin format: $Rxxxxxx is the file, $Ixxxxxx is the metadata
                        if name.startswith('$R') and not name.startswith('$I'):
                            filepath = entry.path
                            ext = os.path.splitext(filepath)[1].lower().lstrip('.')
                            size = entry.stat().st_size
                            
                            # Parse original filename from matching $I file
                            meta_name = '$I' + name[2:]
                            meta_path = os.path.join(sid_dir.path, meta_name)
                            original_name = self._parse_recycle_bin_metadata(meta_path) or name

                            # Copy to recovered output directory
                            dest_path = os.path.join(self.output_dir, original_name)
                            counter = 1
                            base, extension = os.path.splitext(dest_path)
                            while os.path.exists(dest_path):
                                dest_path = f"{base}_{counter}{extension}"
                                counter += 1
                            
                            import shutil
                            shutil.copy2(filepath, dest_path)
                            sha256, sha512 = compute_file_hashes(dest_path)

                            recovered.append({
                                "filename": os.path.basename(dest_path),
                                "filepath": dest_path,
                                "deleted": True,
                                "recoverable": True,
                                "size": f"{round(size / (1024*1024), 2)}MB" if size >= 1024*1024 else f"{round(size/1024, 2)}KB",
                                "bytes_size": size,
                                "type": ext.upper() or "BIN",
                                "hash_sha256": sha256,
                                "hash_sha512": sha512,
                                "metadata": MetadataExtractor.extract_exif(dest_path) if ext in ('jpg', 'jpeg') else {}
                            })
                except PermissionError:
                    continue
        except Exception as e:
            print(f"[Recovery] Error reading Recycle Bin: {e}")

        return recovered

    def _parse_recycle_bin_metadata(self, meta_path: str) -> Optional[str]:
        if not os.path.exists(meta_path):
            return None
        try:
            with open(meta_path, 'rb') as f:
                data = f.read()
            if len(data) > 24:
                path_bytes = data[24:]
                original = path_bytes.decode('utf-16-le', errors='ignore').rstrip('\x00')
                if original:
                    return os.path.basename(original)
        except Exception:
            pass
        return None

    def _carve_raw_signatures(self, source_path: str) -> List[Dict]:
        carved = []
        target_src = source_path
        
        # Convert "D:" to Windows raw handle if drive letter
        if platform.system() == "Windows" and len(source_path.strip().rstrip('\\')) <= 2:
            letter = source_path[0].upper()
            target_src = f"\\\\.\\{letter}:"

        chunk_size = 65536  # 64KB blocks
        max_scan_bytes = 200 * 1024 * 1024  # Limit scan to first 200MB to avoid locking
        
        try:
            if target_src.startswith('\\\\.\\'):
                # Elevated raw disk handle access on Windows
                fd = os.open(target_src, os.O_RDONLY | os.O_BINARY)
                f = os.fdopen(fd, 'rb')
            else:
                if not os.path.exists(target_src):
                    return []
                f = open(target_src, 'rb')
        except Exception as e:
            print(f"[Recovery] Failed to open raw source {target_src}: {e}")
            return []

        try:
            with f:
                offset = 0
                bytes_read = 0
                
                while bytes_read < max_scan_bytes:
                    try:
                        chunk = f.read(chunk_size)
                    except OSError:
                        break
                    if not chunk:
                        break
                    
                    for ext, (headers, desc, max_size, footer) in FILE_SIGNATURES.items():
                        for header in headers:
                            pos = 0
                            while True:
                                pos = chunk.find(header, pos)
                                if pos == -1:
                                    break
                                
                                # Found signature at absolute file offset
                                abs_offset = offset + pos
                                
                                # Fast carve: read the block and write candidate
                                carved_file_name = f"carved_file_{abs_offset}.{ext}"
                                carved_path = os.path.join(self.output_dir, carved_file_name)
                                
                                try:
                                    # Determine carved size
                                    carve_size = max_size
                                    if footer:
                                        # Look for footer within search boundary
                                        orig_pos = f.tell()
                                        f.seek(abs_offset)
                                        search_data = f.read(max_size)
                                        f.seek(orig_pos)
                                        
                                        foot_pos = search_data.find(footer, len(header))
                                        if foot_pos != -1:
                                            carve_size = foot_pos + len(footer)
                                            
                                    # Extract bytes
                                    orig_pos = f.tell()
                                    f.seek(abs_offset)
                                    carved_bytes = f.read(carve_size)
                                    f.seek(orig_pos)
                                    
                                    with open(carved_path, 'wb') as out_f:
                                        out_f.write(carved_bytes)
                                        
                                    sha256, sha512 = compute_file_hashes(carved_path)
                                    
                                    carved.append({
                                        "filename": carved_file_name,
                                        "filepath": carved_path,
                                        "deleted": True,
                                        "recoverable": True,
                                        "size": f"{round(carve_size / (1024*1024), 2)}MB" if carve_size >= 1024*1024 else f"{round(carve_size/1024, 2)}KB",
                                        "bytes_size": carve_size,
                                        "type": ext.upper(),
                                        "hash_sha256": sha256,
                                        "hash_sha512": sha512,
                                        "metadata": {"carve_offset": abs_offset, "description": desc}
                                    })
                                    
                                except Exception as carve_err:
                                    print(f"[Recovery] Carving error at offset {abs_offset}: {carve_err}")
                                
                                pos += len(header)
                    
                    offset += len(chunk)
                    bytes_read += len(chunk)
                    
        except Exception as e:
            print(f"[Recovery] Error scanning raw bytes: {e}")
            
        return carved
