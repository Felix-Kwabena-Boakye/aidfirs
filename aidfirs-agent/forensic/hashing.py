import hashlib
import os
from typing import Tuple, Dict


def compute_file_hashes(filepath: str) -> Tuple[str, str]:
    """
    Compute SHA256 and SHA512 hashes of a file (backward-compatible signature).
    Returns (sha256, sha512).
    """
    result = compute_all_hashes(filepath)
    return result['sha256'], result['sha512']


def compute_all_hashes(filepath: str) -> Dict[str, str]:
    """
    Compute MD5, SHA1, SHA256, and SHA512 hashes of a file in a single pass.
    Returns dict with keys: md5, sha1, sha256, sha512.
    Returns empty strings on error.
    """
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()

    if not filepath or not os.path.exists(filepath):
        return {'md5': '', 'sha1': '', 'sha256': '', 'sha512': ''}

    try:
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                md5.update(chunk)
                sha1.update(chunk)
                sha256.update(chunk)
                sha512.update(chunk)

        return {
            'md5': md5.hexdigest(),
            'sha1': sha1.hexdigest(),
            'sha256': sha256.hexdigest(),
            'sha512': sha512.hexdigest(),
        }
    except Exception as e:
        print(f"[Hashing] Error computing hashes for {filepath}: {e}")
        return {'md5': '', 'sha1': '', 'sha256': '', 'sha512': ''}


def compute_data_hashes(data: bytes) -> Dict[str, str]:
    """
    Compute all hashes of in-memory bytes.
    Returns dict with keys: md5, sha1, sha256, sha512.
    """
    return {
        'md5': hashlib.md5(data).hexdigest(),
        'sha1': hashlib.sha1(data).hexdigest(),
        'sha256': hashlib.sha256(data).hexdigest(),
        'sha512': hashlib.sha512(data).hexdigest(),
    }
