import os
import hashlib
import platform
from datetime import datetime, timezone
from typing import Dict, Callable, Optional

# Optional: pyewf for E01 support
try:
    import pyewf
    PYEWF_AVAILABLE = True
except ImportError:
    PYEWF_AVAILABLE = False


def _get_device_size_bytes(source: str) -> int:
    """Determine the total byte size of a disk or file."""
    if platform.system() == 'Windows' and source.startswith('\\\\.\\'):
        try:
            import ctypes
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
            if total_bytes_win.value > 0:
                return total_bytes_win.value
        except Exception:
            pass
        # Fallback: use IOCTL_DISK_GET_LENGTH_INFO
        try:
            import ctypes
            GENERIC_READ = 0x80000000
            FILE_SHARE_READ = 0x00000001
            FILE_SHARE_WRITE = 0x00000002
            OPEN_EXISTING = 3
            handle = ctypes.windll.kernel32.CreateFileW(
                source, GENERIC_READ,
                FILE_SHARE_READ | FILE_SHARE_WRITE,
                None, OPEN_EXISTING, 0, None
            )
            if handle != -1:
                size = ctypes.c_longlong(0)
                IOCTL_DISK_GET_LENGTH_INFO = 0x0007405C
                bytes_returned = ctypes.c_ulong(0)
                ctypes.windll.kernel32.DeviceIoControl(
                    handle, IOCTL_DISK_GET_LENGTH_INFO, None, 0,
                    ctypes.byref(size), ctypes.sizeof(size),
                    ctypes.byref(bytes_returned), None
                )
                ctypes.windll.kernel32.CloseHandle(handle)
                if size.value > 0:
                    return size.value
        except Exception:
            pass
    elif os.path.exists(source):
        # Regular file (e.g. forensic image for re-imaging)
        return os.path.getsize(source)
    elif platform.system() != 'Windows' and source.startswith('/dev/'):
        # Linux block device
        try:
            with open(source, 'rb') as f:
                f.seek(0, 2)
                return f.tell()
        except Exception:
            pass

    return 500 * 1024 * 1024  # Default 500MB if cannot determine


def acquire_disk_image(source: str, destination: str,
                       progress_callback: Callable[[float], None] = None,
                       case_id: str = None, examiner: str = None,
                       device_id: str = None) -> Dict:
    """
    Performs bit-by-bit physical disk acquisition (RAW DD).
    Computes MD5, SHA256, and SHA512 hashes on-the-fly.
    Generates a forensic acquisition report.
    Never modifies the source evidence device.

    Args:
        source: Drive letter (e.g. 'E:') or device path (e.g. '\\\\.\\E:' or '/dev/sdb')
        destination: Output file path (.dd, .img, or .raw)
        progress_callback: Called with percentage (0.0-100.0) as imaging progresses
        case_id: Associated case ID for the report
        examiner: Name of the forensic examiner
        device_id: Device ID for chain-of-custody reference

    Returns:
        dict with: status, image_path, report_path, bytes_written, sha256, sha512, md5, start_time, end_time
    """
    start_time = datetime.now(timezone.utc)
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()

    # Sanitize destination extension
    if not destination.endswith(('.dd', '.img', '.raw', '.e01')):
        destination += '.dd'

    report_path = os.path.splitext(destination)[0] + '_acquisition_report.txt'
    chunk_size = 1024 * 1024  # 1MB blocks

    # Resolve source to raw device path on Windows
    raw_source = source
    if platform.system() == 'Windows':
        letter = source.rstrip('\\').rstrip(':').strip().upper()
        if len(letter) == 1:
            raw_source = f'\\\\.\\{letter}:'

    # Determine total size for progress tracking
    total_bytes = _get_device_size_bytes(raw_source)

    bytes_written = 0

    try:
        # Open source (read-only, never modify evidence)
        if platform.system() == 'Windows' and raw_source.startswith('\\\\.\\'):
            fd = os.open(raw_source, os.O_RDONLY | os.O_BINARY)
            src_file = os.fdopen(fd, 'rb')
        elif not raw_source.startswith('\\\\.\\') and not os.path.exists(raw_source):
            raise FileNotFoundError(f"Source not found: {raw_source}")
        else:
            src_file = open(raw_source, 'rb')

        # Write RAW DD image
        with src_file as src, open(destination, 'wb') as dst:
            while True:
                if total_bytes > 0:
                    to_read = min(chunk_size, total_bytes - bytes_written)
                    if to_read <= 0:
                        break
                    chunk = src.read(to_read)
                else:
                    chunk = src.read(chunk_size)

                if not chunk:
                    break

                dst.write(chunk)
                md5.update(chunk)
                sha256.update(chunk)
                sha512.update(chunk)

                bytes_written += len(chunk)

                if progress_callback and total_bytes > 0:
                    pct = min(100.0, (bytes_written / total_bytes) * 100.0)
                    progress_callback(pct)

    except PermissionError:
        raise PermissionError(
            f"Access Denied: Please run the AIDFIRS Forensic Agent as Administrator/Root "
            f"to image {source}. On Windows, right-click → Run as Administrator."
        )
    except Exception as e:
        raise RuntimeError(f"Forensic acquisition failed for {source}: {str(e)}")

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    md5_hash = md5.hexdigest()
    sha256_hash = sha256.hexdigest()
    sha512_hash = sha512.hexdigest()

    # Write forensic acquisition report
    report_content = f"""============================================================
AIDFIRS FORENSIC ACQUISITION REPORT
============================================================
Case ID:                 {case_id or 'N/A'}
Device ID:               {device_id or 'N/A'}
Examiner:                {examiner or 'AIDFIRS Agent'}
Acquisition Source:      {source}
Raw Device Path:         {raw_source}
Target Image:            {destination}
Image Format:            RAW DD
Acquisition Start:       {start_time.isoformat()}
Acquisition Completed:   {end_time.isoformat()}
Duration (seconds):      {duration:.2f}
Total Bytes Acquired:    {bytes_written:,} bytes ({bytes_written / (1024**3):.3f} GB)

Integrity Checksums (Computed On-The-Fly):
  MD5:                   {md5_hash}
  SHA-256:               {sha256_hash}
  SHA-512:               {sha512_hash}

Chain of Custody Notes:
  - Source device was opened READ-ONLY. No writes were made to evidence.
  - Image was acquired bit-for-bit using 1MB block transfers.
  - All hashes computed in a single pass during acquisition.
  - This report must be preserved as part of the case record.

Status: ACQUISITION COMPLETED SUCCESSFULLY
============================================================
"""
    try:
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as rep:
            rep.write(report_content)
    except Exception:
        pass

    return {
        "status": "COMPLETED",
        "image_path": destination,
        "report_path": report_path,
        "image_format": "RAW DD",
        "bytes_written": bytes_written,
        "size_gb": round(bytes_written / (1024 ** 3), 3),
        "md5": md5_hash,
        "sha256": sha256_hash,
        "sha512": sha512_hash,
        "start_time": start_time,
        "end_time": end_time,
        "duration_seconds": duration,
        "case_id": case_id,
        "examiner": examiner,
        "device_id": device_id,
    }


def acquire_e01_image(source: str, destination: str,
                      progress_callback: Callable[[float], None] = None,
                      case_id: str = None, examiner: str = None,
                      device_id: str = None) -> Optional[Dict]:
    """
    Acquire a forensic E01 (Expert Witness Format) image using libewf/pyewf.
    Returns None and falls back to RAW if pyewf is not available.
    """
    if not PYEWF_AVAILABLE:
        return None

    try:
        start_time = datetime.now(timezone.utc)
        sha256 = hashlib.sha256()
        md5 = hashlib.md5()

        if not destination.endswith('.e01'):
            destination += '.e01'

        raw_source = source
        if platform.system() == 'Windows':
            letter = source.rstrip('\\').rstrip(':').strip().upper()
            if len(letter) == 1:
                raw_source = f'\\\\.\\{letter}:'

        total_bytes = _get_device_size_bytes(raw_source)
        bytes_written = 0
        chunk_size = 64 * 1024  # 64KB chunks (EWF standard)

        handle = pyewf.handle()
        filenames = pyewf.glob(destination)
        handle.open_write(filenames if filenames else [destination], pyewf.ACCESS_WRITE)

        if examiner:
            handle.set_examiner_name(examiner.encode('utf-8'))
        if case_id:
            handle.set_case_number(str(case_id).encode('utf-8'))
        handle.set_media_type(pyewf.MEDIA_TYPE_FIXED)
        handle.set_format(pyewf.FORMAT_ENCASE6)

        if platform.system() == 'Windows' and raw_source.startswith('\\\\.\\'):
            fd = os.open(raw_source, os.O_RDONLY | os.O_BINARY)
            src_file = os.fdopen(fd, 'rb')
        else:
            src_file = open(raw_source, 'rb')

        with src_file as src:
            while True:
                chunk = src.read(chunk_size)
                if not chunk:
                    break
                handle.write_buffer(chunk)
                sha256.update(chunk)
                md5.update(chunk)
                bytes_written += len(chunk)
                if progress_callback and total_bytes > 0:
                    progress_callback(min(100.0, (bytes_written / total_bytes) * 100.0))

        handle.close()
        end_time = datetime.now(timezone.utc)

        return {
            "status": "COMPLETED",
            "image_path": destination,
            "image_format": "E01",
            "bytes_written": bytes_written,
            "sha256": sha256.hexdigest(),
            "md5": md5.hexdigest(),
            "sha512": "",
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": (end_time - start_time).total_seconds(),
        }
    except Exception as e:
        print(f"[Imaging] E01 acquisition failed: {e}. Falling back to RAW DD.")
        return None
