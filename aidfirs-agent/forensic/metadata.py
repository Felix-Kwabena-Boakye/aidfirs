import struct
from typing import Dict

class MetadataExtractor:
    """Extract metadata from carved file binaries (JPEG, MP4, AVI)."""
    @staticmethod
    def extract_exif(filepath: str) -> Dict:
        metadata = {'exif_present': False}
        try:
            with open(filepath, 'rb') as f:
                data = f.read(65536) # Read first 64KB
            
            exif_marker = b'\xFF\xE1'
            pos = data.find(exif_marker)
            if pos != -1:
                length = struct.unpack('>H', data[pos+2:pos+4])[0]
                exif_data = data[pos+4:pos+4+length]
                metadata['exif_present'] = True
                
                if b'GPS ' in exif_data:
                    metadata['has_gps'] = True
                if b'Exif\x00\x00' in exif_data:
                    metadata['exif_standard'] = 'TIFF/EXIF'
        except Exception:
            pass
        return metadata

    @staticmethod
    def extract_mp4_metadata(filepath: str) -> Dict:
        metadata = {}
        try:
            with open(filepath, 'rb') as f:
                data = f.read(1048576) # Read first 1MB

            moov_pos = data.find(b'moov')
            if moov_pos != -1:
                metadata['moov_atom'] = True

            mvhd_pos = data.find(b'mvhd')
            if mvhd_pos != -1:
                metadata['movie_header'] = True
                version = data[mvhd_pos + 4]
                if version == 0:
                    creation_time = struct.unpack('>I', data[mvhd_pos + 8:mvhd_pos + 12])[0]
                    metadata['creation_time_raw'] = creation_time

            trak_count = data.count(b'trak')
            if trak_count > 0:
                metadata['track_count'] = trak_count
        except Exception:
            pass
        return metadata

    @staticmethod
    def extract_avi_metadata(filepath: str) -> Dict:
        metadata = {}
        try:
            with open(filepath, 'rb') as f:
                data = f.read(4096)

            if data[0:4] == b'RIFF':
                file_size = struct.unpack('<I', data[4:8])[0]
                metadata['riff_size'] = file_size

            hdrl_pos = data.find(b'hdrl')
            if hdrl_pos != -1:
                metadata['has_header'] = True

            movi_pos = data.find(b'movi')
            if movi_pos != -1:
                metadata['has_movie_data'] = True
        except Exception:
            pass
        return metadata
