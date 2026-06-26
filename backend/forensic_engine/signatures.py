"""
Forensic AI Assistant - Centralized File Signatures
"""

SIGNATURES = {
    # Images
    'jpg': {'header': [b'\xFF\xD8\xFF\xE0', b'\xFF\xD8\xFF\xE1', b'\xFF\xD8\xFF\xDB', b'\xFF\xD8\xFF\xEE'], 'footer': b'\xFF\xD9'},
    'png': {'header': [b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'], 'footer': b'\x49\x45\x4E\x44\xAE\x42\x60\x82'},
    'gif': {'header': [b'\x47\x49\x46\x38\x37\x61', b'\x47\x49\x46\x38\x39\x61'], 'footer': b'\x00\x3B'},
    'bmp': {'header': [b'\x42\x4D'], 'footer': None},
    'tiff': {'header': [b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A'], 'footer': None},

    # Documents
    'pdf': {'header': [b'\x25\x50\x44\x46'], 'footer': b'\x25\x25\x45\x4F\x46'},
    'doc': {'header': [b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'], 'footer': None},
    'docx': {'header': [b'\x50\x4B\x03\x04'], 'footer': b'\x50\x4B\x05\x06'},
    'xls': {'header': [b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'], 'footer': None},
    'xlsx': {'header': [b'\x50\x4B\x03\x04'], 'footer': b'\x50\x4B\x05\x06'},
    'ppt': {'header': [b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'], 'footer': None},
    'pptx': {'header': [b'\x50\x4B\x03\x04'], 'footer': b'\x50\x4B\x05\x06'},

    # Archives
    'zip': {'header': [b'\x50\x4B\x03\x04', b'\x50\x4B\x05\x06', b'\x50\x4B\x07\x08'], 'footer': b'\x50\x4B\x05\x06'},
    'rar': {'header': [b'\x52\x61\x72\x21\x1A\x07\x00', b'\x52\x61\x72\x21\x1A\x07\x01\x00'], 'footer': None},
    '7z': {'header': [b'\x37\x7A\xBC\xAF\x27\x1C'], 'footer': None},
    'gz': {'header': [b'\x1F\x8B\x08'], 'footer': None},

    # Game Assets (Universal Extension)
    'unity': {'header': [b'UnityWeb', b'UnityFS'], 'footer': None},
    'unreal': {'header': [b'\x5B\x35\x05\x5A'], 'footer': None},  # .pak
    'godot': {'header': [b'GDPC'], 'footer': None},  # .pck

    # Movies / Video (High-Priority)
    'mp4': {
        'header': [b'\x00\x00\x00\x18\x66\x74\x79\x70', b'\x00\x00\x00\x1C\x66\x74\x79\x70', b'\x00\x00\x00\x20\x66\x74\x79\x70'],
        'footer': None,
        'max_size': 10 * 1024 * 1024 * 1024
    },
    'avi': {'header': [b'\x52\x49\x46\x46'], 'footer': None, 'max_size': 10 * 1024 * 1024 * 1024},
    'mov': {'header': [b'\x00\x00\x00\x14\x66\x74\x79\x70\x71\x74\x20\x20', b'\x00\x00\x00\x20\x66\x74\x79\x70'], 'footer': None},
    'mkv': {'header': [b'\x1A\x45\xDF\xA3'], 'footer': None},
    'wmv': {'header': [b'\x30\x26\xB2\x75\x8E\x66\xCF\x11\xA6\xD9\x00\xAA\x00\x62\xCE\x6C'], 'footer': None},

    # Executables
    'exe': {'header': [b'\x4D\x5A'], 'footer': None},
    'elf': {'header': [b'\x7F\x45\x4C\x46'], 'footer': None},

    # Audio
    'mp3': {'header': [b'\xFF\xFB', b'\xFF\xF3', b'\xFF\xF2', b'\x49\x44\x33'], 'footer': None},
}
