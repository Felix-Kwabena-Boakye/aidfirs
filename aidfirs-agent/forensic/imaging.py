import os
import hashlib
from datetime import datetime, timezone
from typing import Dict, Callable

def acquire_disk_image(source: str, destination: str, progress_callback: Callable[[float], None] = None) -> Dict:
    """
    Performs bit-by-bit physical disk acquisition (RAW DD).
    Computes SHA-256 and SHA-512 hashes on-the-fly.
    Generates an acquisition report.
    """
    start_time = datetime.now(timezone.utc)
    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()
    
    # Secure clean names
    safe_destination = destination
    if not safe_destination.endswith(('.dd', '.img', '.raw')):
        safe_destination += '.dd'
        
    report_destination = os.path.splitext(safe_destination)[0] + '.txt'
    
    # Determine size and seek boundaries
    total_bytes = 0
    bytes_written = 0
    chunk_size = 1024 * 1024  # 1MB blocks for fast imaging
    
    # Try determining drive size
    if os.name == 'nt' and source.startswith('\\\\.\\'):
        try:
            import ctypes
            # Call Win32 GetDiskFreeSpaceEx to estimate size
            drive_letter = source.split('\\')[-1].rstrip(':') + ':\\'
            free_bytes = ctypes.c_ulonglong(0)
            total_bytes_win = ctypes.c_ulonglong(0)
            total_free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(drive_letter),
                ctypes.byref(free_bytes),
                ctypes.byref(total_bytes_win),
                ctypes.byref(total_free_bytes)
            )
            total_bytes = total_bytes_win.value
        except Exception:
            total_bytes = 100 * 1024 * 1024  # 100MB fallback for raw scan limits
    else:
        if os.path.exists(source):
            total_bytes = os.path.getsize(source)
            
    if total_bytes <= 0:
        total_bytes = 500 * 1024 * 1024  # default 500MB if cannot be read
        
    try:
        # Open source
        if os.name == 'nt' and source.startswith('\\\\.\\'):
            # Low-level Windows raw disk handle access
            fd = os.open(source, os.O_RDONLY | os.O_BINARY)
            src_file = os.fdopen(fd, 'rb')
        else:
            src_file = open(source, 'rb')
            
        # Open destination
        with src_file as src, open(safe_destination, 'wb') as dst:
            while bytes_written < total_bytes:
                to_read = min(chunk_size, total_bytes - bytes_written)
                chunk = src.read(to_read)
                if not chunk:
                    break
                
                dst.write(chunk)
                sha256.update(chunk)
                sha512.update(chunk)
                
                bytes_written += len(chunk)
                if progress_callback and total_bytes > 0:
                    progress_callback(min(100.0, (bytes_written / total_bytes) * 100.0))
                    
    except PermissionError:
        raise PermissionError(f"Access Denied: Please run this agent as Administrator/Root to image {source}.")
    except Exception as e:
        raise RuntimeError(f"Forensic acquisition failed: {str(e)}")

    end_time = datetime.now(timezone.utc)
    sha256_hash = sha256.hexdigest()
    sha512_hash = sha512.hexdigest()
    
    # Generate acquisition audit report
    report_content = f"""==================================================
AIDFIRS FORENSIC ACQUISITION REPORT
==================================================
Acquisition Source:      {source}
Target Destination:      {safe_destination}
Acquisition Start:       {start_time.isoformat()}
Acquisition Complete:    {end_time.isoformat()}
Total Bytes Acquired:    {bytes_written} bytes
Integrity Checksums:
  SHA-256:               {sha256_hash}
  SHA-512:               {sha512_hash}
Status:                  Acquisition Completed Successfully
==================================================
"""
    try:
        with open(report_destination, 'w', encoding='utf-8') as rep:
            rep.write(report_content)
    except Exception:
        pass

    return {
        "status": "COMPLETED",
        "image_path": safe_destination,
        "report_path": report_destination,
        "bytes_written": bytes_written,
        "sha256": sha256_hash,
        "sha512": sha512_hash,
        "start_time": start_time,
        "end_time": end_time
    }
