#!/usr/bin/env python
"""
Forensic Engine - Metadata Recovery Module

This module provides functionality for recovering deleted metadata from hard drives
and disk images. It supports various filesystem types and extraction methods.
"""

import os
import struct
import datetime
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from .signatures import SIGNATURES


class MetadataRecovery:
    """
    Handles recovery of deleted metadata from disk images and physical drives.
    """
    
    
    def __init__(self):
        self.recovered_files: List[Dict] = []
        
    def scan_disk_image(self, image_path: str, filesystem_type: str = 'ntfs') -> List[Dict]:
        """
        Scan a disk image for recoverable deleted files and metadata.
        
        Args:
            image_path: Path to the disk image file
            filesystem_type: Type of filesystem (ntfs, fat, ext, etc.)
            
        Returns:
            List of recovered file metadata
        """
        self.recovered_files = []
        
        if not os.path.exists(image_path):
            return []
            
        if os.path.isdir(image_path):
            return self._scan_directory(image_path)
        
        if not os.path.isfile(image_path):
            return []
        
        try:
            with open(image_path, 'rb') as f:
                # Scan for file signatures
                self._scan_for_signatures(f)
                
                # Parse filesystem if supported
                if filesystem_type.lower() == 'ntfs':
                    self._parse_ntfs(f)
                elif filesystem_type.lower() in ['fat16', 'fat32']:
                    self._parse_fat(f)
                    
        except Exception as e:
            print(f"Error scanning disk image: {e}")
            
        return self.recovered_files
    
    def _scan_for_signatures(self, file_handle) -> None:
        """Scan file for known file signatures."""
        file_handle.seek(0)
        
        # Read chunks and search for signatures
        chunk_size = 8192
        offset = 0
        
        while True:
            chunk = file_handle.read(chunk_size)
            if not chunk:
                break
                
            for file_type, sig_info in SIGNATURES.items():
                signatures = sig_info['header']
                for sig in signatures:
                    pos = chunk.find(sig)
                    if pos != -1:
                        # Found a file signature
                        metadata = {
                            'type': 'file_signature',
                            'file_type': file_type,
                            'offset': offset + pos,
                            'signature': sig.hex(),
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                        if metadata not in self.recovered_files:
                            self.recovered_files.append(metadata)
                            
            offset += chunk_size
            
    def _parse_ntfs(self, file_handle) -> None:
        """Parse NTFS filesystem structures."""
        # Read boot sector
        file_handle.seek(0)
        boot_sector = file_handle.read(512)
        
        if len(boot_sector) < 80:
            return
            
        try:
            # Extract bytes per sector (offset 0x0B, 2 bytes)
            bytes_per_sector = struct.unpack('<H', boot_sector[0x0B:0x0D])[0]
            
            # Extract sectors per cluster (offset 0x0D, 1 byte)
            sectors_per_cluster = struct.unpack('B', boot_sector[0x0D:0x0E])[0]
            
            # Extract total sectors (offset 0x28, 8 bytes)
            total_sectors = struct.unpack('<Q', boot_sector[0x28:0x30])[0]
            
            # Extract MFT start (offset 0x30, 8 bytes)
            mft_start = struct.unpack('<Q', boot_sector[0x30:0x38])[0]
            
            cluster_size = bytes_per_sector * sectors_per_cluster
            
            metadata = {
                'type': 'ntfs_boot_sector',
                'bytes_per_sector': bytes_per_sector,
                'sectors_per_cluster': sectors_per_cluster,
                'cluster_size': cluster_size,
                'total_sectors': total_sectors,
                'mft_start_cluster': mft_start,
                'filesystem_size': total_sectors * bytes_per_sector,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            self.recovered_files.append(metadata)
            
            # Parse MFT (Master File Table)
            self._parse_mft(file_handle, mft_start * cluster_size)
            
        except Exception as e:
            print(f"Error parsing NTFS: {e}")
            
    def _parse_mft(self, file_handle, mft_offset: int) -> None:
        """Parse NTFS MFT (Master File Table) entries."""
        try:
            file_handle.seek(mft_offset)
            mft_data = file_handle.read(1024)  # Read first MFT entry
            
            if len(mft_data) >= 48:
                # Extract MFT entry header
                signature = mft_data[0:4]
                
                metadata = {
                    'type': 'ntfs_mft_entry',
                    'signature': signature.hex(),
                    'offset': mft_offset,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                self.recovered_files.append(metadata)
                
        except Exception as e:
            print(f"Error parsing MFT: {e}")
            
    def _parse_fat(self, file_handle) -> None:
        """Parse FAT filesystem."""
        file_handle.seek(0)
        boot_sector = file_handle.read(512)
        
        if len(boot_sector) < 62:
            return
            
        try:
            # Extract FAT parameters
            bytes_per_sector = struct.unpack('<H', boot_sector[0x0B:0x0D])[0]
            sectors_per_cluster = struct.unpack('B', boot_sector[0x0D:0x0E])[0]
            reserved_sectors = struct.unpack('<H', boot_sector[0x0E:0x10])[0]
            fat_copies = struct.unpack('B', boot_sector[0x10:0x11])[0]
            total_sectors = struct.unpack('<H', boot_sector[0x13:0x15])[0]
            
            metadata = {
                'type': 'fat_boot_sector',
                'bytes_per_sector': bytes_per_sector,
                'sectors_per_cluster': sectors_per_cluster,
                'reserved_sectors': reserved_sectors,
                'fat_copies': fat_copies,
                'total_sectors': total_sectors,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            self.recovered_files.append(metadata)
            
        except Exception as e:
            print(f"Error parsing FAT: {e}")
            
    def extract_timestamps(self, file_handle, start_offset: int = 0, count: int = 100) -> List[Dict]:
        """
        Extract potential timestamps from disk image.
        
        Looks for common timestamp patterns in raw data.
        """
        timestamps = []
        
        try:
            file_handle.seek(start_offset)
            data = file_handle.read(count * 1024)  # Read count KB
            
            # Common timestamp patterns
            # Unix timestamps (4 bytes, big-endian and little-endian)
            for i in range(len(data) - 4):
                # Try little-endian
                le_val = struct.unpack('<I', data[i:i+4])[0]
                if 946684800 < le_val < 4102444800:  # 2000-2100 range
                    timestamps.append({
                        'type': 'unix_timestamp_le',
                        'offset': start_offset + i,
                        'value': le_val,
                        'datetime': datetime.fromtimestamp(le_val, tz=timezone.utc).isoformat()
                    })
                    
                # Try big-endian
                be_val = struct.unpack('>I', data[i:i+4])[0]
                if 946684800 < be_val < 4102444800:
                    timestamps.append({
                        'type': 'unix_timestamp_be',
                        'offset': start_offset + i,
                        'value': be_val,
                        'datetime': datetime.fromtimestamp(be_val, tz=timezone.utc).isoformat()
                    })
                    
        except Exception as e:
            print(f"Error extracting timestamps: {e}")
            
        return timestamps
    
    def recover_deleted_entries(self, image_path: str) -> List[Dict]:
        """
        Attempt to recover deleted file entries from filesystem.
        
        Returns:
            List of potentially recoverable file entries
        """
        recovered = []
        
        if not os.path.exists(image_path):
            return []
            
        if os.path.isdir(image_path):
            try:
                from forensic_engine.windows_recovery import scan_recycle_bin
                recycle_entries = scan_recycle_bin(image_path)
                for entry in recycle_entries:
                    recovered.append({
                        'type': 'deleted_file',
                        'filename': entry.get('original_name'),
                        'path': entry.get('recycle_path'),
                        'size': entry.get('size'),
                        'deleted_at': entry.get('deleted_at'),
                        'hash_md5': entry.get('md5'),
                        'status': 'deleted'
                    })
            except Exception as e:
                print(f"Error scanning Recycle Bin: {e}")
            return recovered
            
        if not os.path.isfile(image_path):
            return []
            
        try:
            with open(image_path, 'rb') as f:
                # Look for file name patterns in unused sectors
                # This is a simplified approach
                
                f.seek(0)
                data = f.read(1024 * 1024)  # Read 1MB
                
                # Search for common filename patterns
                import re
                
                # Look for strings that look like filenames
                # Windows filenames
                windows_names = re.findall(b'[A-Za-z]:\\\\[^\\x00-\\x1F]{1,255}', data)
                for name in windows_names[:10]:
                    recovered.append({
                        'type': 'filename',
                        'value': name.decode('utf-8', errors='ignore'),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                    
                # Unix filenames
                unix_names = re.findall(b'/[^/\\x00-\\x1F]{1,255}', data)
                for name in unix_names[:10]:
                    recovered.append({
                        'type': 'unix_path',
                        'value': name.decode('utf-8', errors='ignore'),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                    
        except Exception as e:
            print(f"Error recovering entries: {e}")
            
        return recovered
    
    def compute_file_hashes(self, file_path: str) -> Dict[str, str]:
        """
        Compute multiple hashes for a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with MD5, SHA1, SHA256 hashes
        """
        md5_hash = hashlib.md5()
        sha1_hash = hashlib.sha1()
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    md5_hash.update(chunk)
                    sha1_hash.update(chunk)
                    sha256_hash.update(chunk)
                    
            return {
                'md5': md5_hash.hexdigest(),
                'sha1': sha1_hash.hexdigest(),
                'sha256': sha256_hash.hexdigest()
            }
        except Exception as e:
            return {'error': str(e)}
            
    def _scan_directory(self, dir_path: str) -> List[Dict]:
        """Scan a real directory or drive root to extract actual file metadata. No simulated data is returned."""
        files_metadata = []
        try:
            # Walk directory to find files (limit to 150 files to prevent performance lag)
            file_counter = 0
            for root, dirs, files in os.walk(dir_path):
                if file_counter >= 150:
                    break
                for name in files:
                    if file_counter >= 150:
                        break
                    full_path = os.path.join(root, name)
                    try:
                        st = os.stat(full_path)
                        size = st.st_size
                        created_time = datetime.fromtimestamp(st.st_ctime, tz=timezone.utc).isoformat()
                        modified_time = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
                        accessed_time = datetime.fromtimestamp(st.st_atime, tz=timezone.utc).isoformat()
                        
                        md5_val = ""
                        sha256_val = ""
                        if size < 1 * 1024 * 1024:
                            md5_h = hashlib.md5()
                            sha_h = hashlib.sha256()
                            with open(full_path, 'rb') as f:
                                data = f.read()
                                md5_h.update(data)
                                sha_h.update(data)
                            md5_val = md5_h.hexdigest()
                            sha256_val = sha_h.hexdigest()
                            
                        files_metadata.append({
                            'type': 'file',
                            'filename': name,
                            'path': full_path,
                            'size': size,
                            'created': created_time,
                            'modified': modified_time,
                            'accessed': accessed_time,
                            'hash_md5': md5_val or None,
                            'hash_sha256': sha256_val or None,
                            'status': 'active'
                        })
                        file_counter += 1
                    except Exception:
                        continue
        except Exception as e:
            print(f"Error scanning directory: {e}")
            
        return files_metadata



class DiskImageAnalyzer:
    """
    High-level analyzer for disk images.
    """
    
    def __init__(self):
        self.recovery = MetadataRecovery()
        
    def full_analysis(self, image_path: str, filesystem_type: str = 'ntfs') -> Dict:
        """
        Perform a full forensic analysis of a disk image.
        
        Args:
            image_path: Path to disk image
            filesystem_type: Type of filesystem
            
        Returns:
            Complete analysis results
        """
        results = {
            'image_path': image_path,
            'analysis_time': datetime.now(timezone.utc).isoformat(),
            'filesystem_type': filesystem_type,
            'recovered_files': [],
            'timestamps': [],
            'file_signatures': [],
            'statistics': {}
        }
        
        # Scan for recoverable files
        results['recovered_files'] = self.recovery.scan_disk_image(image_path, filesystem_type)
        
        # Extract timestamps only if it's a real file
        if os.path.isfile(image_path):
            with open(image_path, 'rb') as f:
                results['timestamps'] = self.recovery.extract_timestamps(f)
                
        # Recover deleted entries
        results['deleted_entries'] = self.recovery.recover_deleted_entries(image_path)
        
        # Calculate statistics
        file_types = {}
        for f in results['recovered_files']:
            ftype = f.get('file_type', f.get('type', 'unknown'))
            file_types[ftype] = file_types.get(ftype, 0) + 1
            
        results['statistics'] = {
            'total_recovered': len(results['recovered_files']),
            'total_timestamps': len(results['timestamps']),
            'file_type_breakdown': file_types
        }
        
        return results
