import hashlib
from typing import Tuple

def compute_file_hashes(filepath: str) -> Tuple[str, str]:
    """
    Compute SHA-256 and SHA-512 hashes for a file.
    Returns (sha256, sha512) hex strings.
    """
    sha256_hash = hashlib.sha256()
    sha512_hash = hashlib.sha512()

    with open(filepath, 'rb') as f:
        # Read in 1MB chunks
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha256_hash.update(chunk)
            sha512_hash.update(chunk)

    return sha256_hash.hexdigest(), sha512_hash.hexdigest()
