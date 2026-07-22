import os
import struct
from datetime import datetime, timezone
from typing import Dict, Optional

# Optional: Pillow for EXIF extraction
try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


class MetadataExtractor:
    """Extract forensic metadata from carved file binaries."""

    @staticmethod
    def extract_file_timestamps(filepath: str) -> Dict:
        """Extract filesystem timestamps from a file."""
        result = {}
        try:
            stat = os.stat(filepath)
            result['created_time'] = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()
            result['modified_time'] = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            result['accessed_time'] = datetime.fromtimestamp(stat.st_atime, tz=timezone.utc).isoformat()
        except Exception as e:
            print(f"[Metadata] Failed to get timestamps for {filepath}: {e}")
        return result

    @staticmethod
    def extract_exif(filepath: str) -> Dict:
        """Extract EXIF metadata from image files. Uses Pillow if available, else raw parsing."""
        metadata = {'exif_present': False}

        if PILLOW_AVAILABLE:
            try:
                with Image.open(filepath) as img:
                    metadata['format'] = img.format
                    metadata['mode'] = img.mode
                    metadata['size'] = f"{img.width}x{img.height}"
                    metadata['width'] = img.width
                    metadata['height'] = img.height

                    exif_data = img._getexif()
                    if exif_data:
                        metadata['exif_present'] = True
                        for tag_id, value in exif_data.items():
                            tag = TAGS.get(tag_id, tag_id)
                            if isinstance(value, bytes):
                                try:
                                    value = value.decode('utf-8', errors='replace')
                                except Exception:
                                    value = str(value)
                            metadata[str(tag)] = str(value)[:500]  # cap length
            except Exception as e:
                pass
        else:
            # Raw EXIF parsing fallback
            try:
                with open(filepath, 'rb') as f:
                    data = f.read(65536)
                exif_marker = b'\xFF\xE1'
                pos = data.find(exif_marker)
                if pos != -1:
                    length = struct.unpack('>H', data[pos+2:pos+4])[0]
                    exif_data = data[pos+4:pos+4+length]
                    metadata['exif_present'] = True
                    metadata['has_gps'] = b'GPS ' in exif_data
                    metadata['exif_standard'] = 'TIFF/EXIF' if b'Exif\x00\x00' in exif_data else 'Unknown'
            except Exception:
                pass

        # Add file timestamps
        metadata.update(MetadataExtractor.extract_file_timestamps(filepath))
        return metadata

    @staticmethod
    def extract_pdf_metadata(filepath: str) -> Dict:
        """Extract metadata from a PDF file."""
        metadata = {}
        try:
            with open(filepath, 'rb') as f:
                data = f.read(65536)
            if data.startswith(b'%PDF'):
                version_end = data.find(b'\n')
                metadata['pdf_version'] = data[1:version_end].decode('latin-1', errors='ignore').strip()
            # Try to find /Author, /Title, /Creator, /Producer, /CreationDate
            for key in [b'/Author', b'/Title', b'/Creator', b'/Producer', b'/CreationDate', b'/Subject']:
                pos = data.find(key)
                if pos != -1:
                    start = data.find(b'(', pos)
                    if start != -1:
                        end = data.find(b')', start)
                        if end != -1:
                            value = data[start+1:end].decode('latin-1', errors='replace')[:200]
                            metadata[key.decode()[1:]] = value
        except Exception:
            pass
        metadata.update(MetadataExtractor.extract_file_timestamps(filepath))
        return metadata

    @staticmethod
    def extract_mp4_metadata(filepath: str) -> Dict:
        """Extract metadata from MP4/MOV video files."""
        metadata = {}
        try:
            with open(filepath, 'rb') as f:
                data = f.read(1048576)
            if b'moov' in data:
                metadata['moov_atom'] = True
            if b'mvhd' in data:
                metadata['movie_header'] = True
                mvhd_pos = data.find(b'mvhd')
                if mvhd_pos != -1:
                    version = data[mvhd_pos + 4]
                    if version == 0:
                        try:
                            creation_raw = struct.unpack('>I', data[mvhd_pos + 8:mvhd_pos + 12])[0]
                            # MP4 epoch: January 1, 1904
                            mp4_epoch_offset = 2082844800
                            if creation_raw > mp4_epoch_offset:
                                creation_ts = datetime.fromtimestamp(creation_raw - mp4_epoch_offset, tz=timezone.utc)
                                metadata['creation_time'] = creation_ts.isoformat()
                        except Exception:
                            pass
            metadata['track_count'] = data.count(b'trak')
        except Exception:
            pass
        metadata.update(MetadataExtractor.extract_file_timestamps(filepath))
        return metadata

    @staticmethod
    def extract_avi_metadata(filepath: str) -> Dict:
        """Extract metadata from AVI video files."""
        metadata = {}
        try:
            with open(filepath, 'rb') as f:
                data = f.read(4096)
            if data[0:4] == b'RIFF':
                metadata['riff_size'] = struct.unpack('<I', data[4:8])[0]
            metadata['has_header'] = b'hdrl' in data
            metadata['has_movie_data'] = b'movi' in data
        except Exception:
            pass
        metadata.update(MetadataExtractor.extract_file_timestamps(filepath))
        return metadata

    @staticmethod
    def extract_zip_metadata(filepath: str) -> Dict:
        """Extract metadata from ZIP/DOCX/XLSX/PPTX archives."""
        metadata = {}
        try:
            import zipfile
            with zipfile.ZipFile(filepath, 'r') as zf:
                metadata['file_count'] = len(zf.namelist())
                metadata['files'] = zf.namelist()[:20]  # first 20 files
                metadata['compressed_size'] = sum(i.compress_size for i in zf.infolist())
                # Check if it's an Office document
                names = zf.namelist()
                if '[Content_Types].xml' in names:
                    metadata['office_format'] = True
                    if 'word/document.xml' in names:
                        metadata['office_type'] = 'DOCX'
                    elif 'xl/workbook.xml' in names:
                        metadata['office_type'] = 'XLSX'
                    elif 'ppt/presentation.xml' in names:
                        metadata['office_type'] = 'PPTX'
        except Exception:
            pass
        metadata.update(MetadataExtractor.extract_file_timestamps(filepath))
        return metadata

    @staticmethod
    def extract_by_extension(filepath: str, extension: str) -> Dict:
        """Route to appropriate extractor based on file extension."""
        ext = extension.lower().lstrip('.')
        try:
            if ext in ('jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff'):
                return MetadataExtractor.extract_exif(filepath)
            elif ext == 'pdf':
                return MetadataExtractor.extract_pdf_metadata(filepath)
            elif ext in ('mp4', 'mov', 'm4v'):
                return MetadataExtractor.extract_mp4_metadata(filepath)
            elif ext == 'avi':
                return MetadataExtractor.extract_avi_metadata(filepath)
            elif ext in ('zip', 'docx', 'xlsx', 'pptx', 'odt', 'ods'):
                return MetadataExtractor.extract_zip_metadata(filepath)
            else:
                return MetadataExtractor.extract_file_timestamps(filepath)
        except Exception as e:
            return {'error': str(e), **MetadataExtractor.extract_file_timestamps(filepath)}
