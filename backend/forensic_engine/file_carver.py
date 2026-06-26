#!/usr/bin/env python
"""
Forensic AI Assistant - File Carving Module

This module provides advanced file carving capabilities for recovering
deleted files, movies, and metadata from disk images and raw data.
"""

import os
import struct
import re
import hashlib
from typing import Any, Dict, List, Optional, Tuple, Iterable
from datetime import datetime, timezone
import platform


from .signatures import SIGNATURES


class SectorAlignedFile:
    """
    Custom wrapper to safely read raw disks and files.
    Ensures Windows raw disk access (e.g. \\\\.\\D:) aligns seeks and reads to 512-byte sectors,
    which eliminates OSError: [Errno 22] Invalid argument.
    """
    def __init__(self, file_path: str, sector_size: int = 512):
        self.file_path = file_path
        self.sector_size = sector_size
        self.is_raw_disk = False
        
        clean_path = file_path.strip().rstrip('\\').rstrip('/')
        if os.name == 'nt' and (clean_path.startswith('\\\\.\\') or (len(clean_path) == 2 and clean_path[1] == ':')):
            self.is_raw_disk = True
            
        if self.is_raw_disk:
            try:
                # Open using low-level fd for shared access options on Windows raw volumes
                self.fd = os.open(file_path, os.O_RDONLY | os.O_BINARY)
                self.file = os.fdopen(self.fd, 'rb')
            except Exception:
                self.file = open(file_path, 'rb')
        else:
            self.file = open(file_path, 'rb')
            
        self.position = 0

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            self.position = offset
        elif whence == 1:
            self.position += offset
        elif whence == 2:
            try:
                self.file.seek(0, 2)
                end_pos = self.file.tell()
                self.position = end_pos + offset
            except Exception:
                self.file.seek(offset, whence)
                self.position = self.file.tell()
        return self.position

    def tell(self) -> int:
        return self.position

    def read(self, size: int = -1) -> bytes:
        if size == -1 or size is None:
            size = 1024 * 1024
            
        if size <= 0:
            return b""

        if not self.is_raw_disk:
            self.file.seek(self.position)
            data = self.file.read(size)
            self.position += len(data)
            return data

        # Calculate aligned start and end sector bounds
        start_offset = self.position
        end_offset = start_offset + size

        aligned_start = (start_offset // self.sector_size) * self.sector_size
        aligned_end = ((end_offset + self.sector_size - 1) // self.sector_size) * self.sector_size
        aligned_size = aligned_end - aligned_start

        try:
            self.file.seek(aligned_start)
            chunk = self.file.read(aligned_size)
        except OSError as oe:
            if oe.errno == 22:
                try:
                    self.file.seek(aligned_start)
                    chunk = self.file.read(aligned_size)
                except Exception:
                    return b""
            else:
                return b""
        except Exception:
            return b""

        relative_start = start_offset - aligned_start
        requested_data = chunk[relative_start : relative_start + size]
        
        self.position += len(requested_data)
        return requested_data

    def close(self):
        try:
            self.file.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class FileCarver:
    """
    Advanced file carving engine that recovers deleted files by scanning
    for file signatures (headers and footers) in raw disk data.
    """

    def __init__(self, chunk_size: int = 8192, max_file_size: int = 10 * 1024 * 1024 * 1024):
        self.chunk_size = chunk_size
        self.max_file_size = max_file_size
        self.recovered_files: List[Dict] = []

    def carve_disk_image(self, image_path: str, file_types: Optional[List[str]] = None) -> List[Dict]:
        """
        Carve deleted files from a disk image.

        Args:
            image_path: Path to the disk image
            file_types: List of file types to recover (e.g., ['jpg', 'mp4', 'pdf'])
                       If None, all supported types are scanned.

        Returns:
            List of recovered file metadata
        """
        self.recovered_files = []

        is_raw_drive = False
        target_path = image_path
        
        if platform.system() == 'Windows':
            is_drive_target = False
            clean_path = image_path.strip().rstrip('\\').rstrip('/')
            if len(clean_path) == 2 and clean_path[1] == ':':
                is_drive_target = True
            elif re.match(r'^\\\\.\\', clean_path):
                is_drive_target = True
                
            if is_drive_target:
                try:
                    import psutil
                    for part in psutil.disk_partitions(all=False):
                        if 'removable' in part.opts:
                            drive_letter = part.mountpoint[0].upper()
                            target_path = f'\\\\.\\{drive_letter}:'
                            is_raw_drive = True
                            break
                except Exception:
                    pass
                    
                if not is_raw_drive:
                    if len(clean_path) == 2 and clean_path[1] == ':':
                        drive_letter = clean_path[0].upper()
                        target_path = f'\\\\.\\{drive_letter}:'
                        is_raw_drive = True
                    else:
                        match = re.match(r'^\\\\.\\([A-Za-z]):?$', clean_path)
                        if match:
                            drive_letter = match.group(1).upper()
                            target_path = f'\\\\.\\{drive_letter}:'
                            is_raw_drive = True

        if not is_raw_drive and not os.path.exists(target_path):
            raise FileNotFoundError(f"Target path does not exist: {target_path}")

        if not is_raw_drive and os.path.isdir(target_path):
            return []

        types_to_scan = file_types or list(SIGNATURES.keys())

        try:
            with SectorAlignedFile(target_path) as f:
                if is_raw_drive:
                    file_size = 512 * 1024 * 1024 # Scan first 512MB to avoid freezing
                else:
                    file_size = os.path.getsize(target_path)
                offset = 0

                while offset < file_size:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break

                    for file_type in types_to_scan:
                        if file_type not in SIGNATURES:
                            continue

                        sig_info = SIGNATURES[file_type]
                        headers = sig_info['header']
                        footer = sig_info.get('footer')
                        max_size = sig_info.get('max_size', self.max_file_size)

                        for header in headers:
                            pos = 0
                            while True:
                                pos = chunk.find(header, pos)
                                if pos == -1:
                                    break

                                absolute_offset = offset + pos

                                # Try to determine file size
                                file_size_found = self._estimate_file_size(
                                    f, absolute_offset, footer, max_size
                                )

                                recovered = {
                                    'type': 'carved_file',
                                    'file_type': file_type,
                                    'offset': absolute_offset,
                                    'estimated_size': file_size_found,
                                    'header_signature': header.hex(),
                                    'footer_found': footer is not None,
                                    'recovery_confidence': 'high' if footer else 'medium',
                                    'timestamp': datetime.now(timezone.utc).isoformat()
                                }

                                if recovered not in self.recovered_files:
                                    self.recovered_files.append(recovered)

                                pos += len(header)

                    offset += self.chunk_size

        except Exception as e:
            print(f"Error carving disk image: {e}")

        return self.recovered_files

    def _estimate_file_size(self, file_handle, start_offset: int, footer: Optional[bytes], max_size: int) -> int:
        """Estimate file size by looking for footer or using heuristics."""
        if footer is None:
            # No footer known - use chunk-based heuristic
            return self.chunk_size

        try:
            current_pos = file_handle.tell()
            file_handle.seek(start_offset)

            search_size = min(max_size, 100 * 1024 * 1024)  # Search up to 100MB for footer
            data = file_handle.read(search_size)

            footer_pos = data.find(footer, len(footer))
            if footer_pos != -1:
                return footer_pos + len(footer)

            file_handle.seek(current_pos)
            return self.chunk_size  # Fallback
        except Exception:
            return self.chunk_size

    def recover_movies(self, image_path: str) -> List[Dict]:
        """
        Specialized recovery for deleted movie files.
        Supports: MP4, AVI, MOV, MKV, WMV, FLV, MPEG, WEBM
        """
        movie_types = ['mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'mpeg', 'webm']
        return self.carve_disk_image(image_path, file_types=movie_types)

    def recover_documents(self, image_path: str) -> List[Dict]:
        """Recover deleted document files."""
        doc_types = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx']
        return self.carve_disk_image(image_path, file_types=doc_types)

    def recover_images(self, image_path: str) -> List[Dict]:
        """Recover deleted image files."""
        img_types = ['jpg', 'png', 'gif', 'bmp', 'tiff']
        return self.carve_disk_image(image_path, file_types=img_types)

    def recover_game_assets(self, image_path: str) -> List[Dict]:
        """
        Universal Recovery: Recover deleted game assets.
        Supports: Unity (.assets), Unreal (.pak), Godot (.pck)
        """
        game_types = ['unity', 'unreal', 'godot']
        # Placeholder for specialized game asset carving logic
        return self.carve_disk_image(image_path, file_types=game_types)

    def reconstruct_fragmented_files(self, candidates: List[Dict]) -> List[Dict]:
        """
        Empowerment Engine: Reconstruct highly fragmented files using AI.
        Uses Reinforcement Learning concepts to piece together data blocks.
        """
        # Placeholder for future empowerment engine integration
        return candidates

    def extract_carved_bytes(
        self,
        image_path: str,
        carved_candidates: List[Dict[str, Any]],
        out_dir: str,
        max_carved_per_type: int = 200,
        max_total_bytes: int = 2 * 1024 * 1024 * 1024,
        chunk_read_size: int = 1024 * 1024,
    ) -> List[Dict[str, Any]]:
        """Extract carved bytes to output files (for candidates with estimated_size).

        Forensic soundness note: this does not modify the evidence source.
        """
        os.makedirs(out_dir, exist_ok=True)

        total_written = 0
        written_by_type: Dict[str, int] = {}
        outputs: List[Dict[str, Any]] = []

        target_path = image_path
        if platform.system() == 'Windows' and len(image_path) >= 2 and image_path[1] == ':':
            drive_letter = image_path[0].upper()
            target_path = f'\\\\.\\{drive_letter}:'

        for cand in carved_candidates:
            file_type = cand.get("file_type") or "unknown"
            if written_by_type.get(file_type, 0) >= max_carved_per_type:
                continue

            offset = cand.get("offset")
            est_size = cand.get("estimated_size")
            if offset is None or est_size is None:
                continue

            if not isinstance(est_size, int) or est_size <= 0:
                continue

            if total_written + est_size > max_total_bytes:
                break

            out_name = f"carved_{file_type}_off_{offset}_sz_{est_size}.bin"
            out_path = os.path.join(out_dir, out_name)

            try:
                with SectorAlignedFile(target_path) as src, open(out_path, "wb") as dst:
                    src.seek(int(offset))
                    remaining = int(est_size)
                    while remaining > 0:
                        to_read = min(chunk_read_size, remaining)
                        data = src.read(to_read)
                        if not data:
                            break
                        dst.write(data)
                        remaining -= len(data)
                        if len(data) > 0:
                            total_written += len(data)

                # Hash carved output for integrity
                md5, sha256 = self._hash_file(out_path)

                outputs.append(
                    {
                        "file_type": file_type,
                        "offset": offset,
                        "estimated_size": est_size,
                        "output_path": out_path,
                        "md5": md5,
                        "sha256": sha256,
                        "header_signature": cand.get("header_signature"),
                        "footer_found": cand.get("footer_found"),
                        "recovery_confidence": cand.get("recovery_confidence"),
                    }
                )
                written_by_type[file_type] = written_by_type.get(file_type, 0) + 1
            except Exception:
                # keep going on individual failures
                continue

        return outputs

    def _hash_file(self, path: str) -> Tuple[str, str]:
        md5 = hashlib.md5()
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                md5.update(chunk)
                sha256.update(chunk)
        return md5.hexdigest(), sha256.hexdigest()

    def get_recovery_statistics(self) -> Dict:


        """Get statistics about recovered files."""
        if not self.recovered_files:
            return {'total': 0, 'by_type': {}, 'by_confidence': {}}

        by_type = {}
        by_confidence = {}
        total_size = 0

        for f in self.recovered_files:
            ftype = f.get('file_type', 'unknown')
            conf = f.get('recovery_confidence', 'unknown')
            size = f.get('estimated_size', 0)

            by_type[ftype] = by_type.get(ftype, 0) + 1
            by_confidence[conf] = by_confidence.get(conf, 0) + 1
            total_size += size

        return {
            'total': len(self.recovered_files),
            'by_type': by_type,
            'by_confidence': by_confidence,
            'total_estimated_size': total_size,
            'total_estimated_size_mb': round(total_size / (1024 * 1024), 2)
        }




class MetadataExtractor:
    """
    Extract metadata from recovered files and disk images.
    """

    @staticmethod
    def extract_exif(data: bytes, offset: int = 0) -> Dict:
        """Extract EXIF metadata from JPEG data, including GPS coordinates."""
        metadata = {'exif_present': False}
        try:
            # Look for EXIF marker
            exif_marker = b'\xFF\xE1'
            pos = data.find(exif_marker, offset)
            if pos != -1:
                length = struct.unpack('>H', data[pos+2:pos+4])[0]
                exif_data = data[pos+4:pos+4+length]
                metadata['exif_present'] = True
                
                # Check for GPS tags
                if b'GPS ' in exif_data:
                    metadata['has_gps'] = True
                    # Placeholder for actual coordinate parsing (using a custom hex offset search)
                    # Coordinates near "Beijing" or "Conflict Zones" are flagged by higher-level modules
                    metadata['gps_block_found'] = True
                    
                if b'Exif\x00\x00' in exif_data:
                    metadata['exif_standard'] = 'TIFF/EXIF'
        except Exception:
            pass
        return metadata

    @staticmethod
    def extract_mp4_metadata(data: bytes, offset: int = 0) -> Dict:
        """Extract metadata from MP4/MOV files."""
        metadata = {}
        try:
            # Look for moov atom
            moov_pos = data.find(b'moov', offset)
            if moov_pos != -1:
                metadata['moov_atom'] = True

            # Look for mvhd (movie header)
            mvhd_pos = data.find(b'mvhd', offset)
            if mvhd_pos != -1:
                metadata['movie_header'] = True
                # Extract creation time
                version = data[mvhd_pos + 4]
                if version == 0:
                    creation_time = struct.unpack('>I', data[mvhd_pos + 8:mvhd_pos + 12])[0]
                    metadata['creation_time_raw'] = creation_time

            # Look for trak atoms (tracks)
            trak_count = data.count(b'trak', offset, offset + 1024 * 1024)
            if trak_count > 0:
                metadata['track_count'] = trak_count

        except Exception:
            pass
        return metadata

    @staticmethod
    def extract_avi_metadata(data: bytes, offset: int = 0) -> Dict:
        """Extract metadata from AVI files."""
        metadata = {}
        try:
            # AVI uses RIFF structure
            if data[offset:offset+4] == b'RIFF':
                file_size = struct.unpack('<I', data[offset+4:offset+8])[0]
                metadata['riff_size'] = file_size

            # Look for hdrl (header list)
            hdrl_pos = data.find(b'hdrl', offset)
            if hdrl_pos != -1:
                metadata['has_header'] = True

            # Look for movi (movie data)
            movi_pos = data.find(b'movi', offset)
            if movi_pos != -1:
                metadata['has_movie_data'] = True

        except Exception:
            pass
        return metadata

