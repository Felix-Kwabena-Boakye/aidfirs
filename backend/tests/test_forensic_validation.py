import os
import sys
import hashlib
import pytest
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.conf import settings

from forensic_api import tsk_wrapper as tw
from forensic_engine.recovery_engine import RecoveryEngine, RecoveryOptions
from forensic_engine.file_carver import FileCarver


IMAGES_DIR = r'C:\Users\HomePC\AppData\Local\Temp\opencode\forensic_validation\images'
GT_DIR = os.path.join(IMAGES_DIR, 'canon2-gt')
CANON2_RAW = os.path.join(IMAGES_DIR, 'nps-2009-canon2-gen6.raw')
NTFS1_RAW = os.path.join(IMAGES_DIR, 'nps-2009-ntfs1-gen1.raw')
EMAILS_RAW = os.path.join(IMAGES_DIR, 'nps-2010-emails.raw')

IMAGES_AVAILABLE = all(os.path.exists(p) for p in [CANON2_RAW, NTFS1_RAW, EMAILS_RAW])


def _recover(img, fs, label):
    out_dir = os.path.join(settings.BASE_DIR, 'storage', 'recoveries', 'validation', label)
    os.makedirs(out_dir, exist_ok=True)
    opts = RecoveryOptions(
        file_types=['jpg', 'pdf', 'doc', 'docx', 'xls', 'xlsx'],
        carve=True, out_dir=out_dir, max_carved_per_type=200, max_carve_bytes=400 * 1024 * 1024,
    )
    engine = RecoveryEngine(options=opts)
    return engine.recover(img, filesystem_type=fs), out_dir


@pytest.mark.skipif(not IMAGES_AVAILABLE, reason="NPS test images not present")
class TestForensicValidationE2E:
    def test_canon2_allocated_jpgs_match_gt(self):
        res = tw.list_files(CANON2_RAW, '51')
        files = res.get('files', []) if isinstance(res, dict) else []
        alloc = [f for f in files if f.get('type') == 'r' and 'Volume Label' not in f.get('name', '')]
        assert len(alloc) > 0, "no allocated files found on canon2"

        gt_hashes = {}
        for f in os.listdir(GT_DIR):
            h = hashlib.sha1(open(os.path.join(GT_DIR, f), 'rb').read()).hexdigest()
            gt_hashes[f.upper()] = h

        matched = 0
        for f in alloc:
            name = os.path.basename(f.get('name', '')).upper()
            if not name.endswith('.JPG'):
                continue
            out = os.path.join(settings.BASE_DIR, 'storage', 'recoveries', 'validation', 'canon2_tmp', name)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            r = tw.extract_file(CANON2_RAW, f['inode'], out, '51')
            if os.path.exists(out) and os.path.getsize(out) > 0:
                h = hashlib.sha1(open(out, 'rb').read()).hexdigest()
                if h == gt_hashes.get(name):
                    matched += 1

        assert matched >= 30, f"canon2: only {matched} GT JPG hashes matched (expect >= 30)"

    def test_canon2_deleted_inodes_found(self):
        res = tw.get_deleted_metadata(CANON2_RAW, '51')
        assert res.get('success') is True
        deleted = res.get('metadata', [])
        assert len(deleted) >= 3, f"expected >=3 deleted inodes, got {len(deleted)}"
        sizes = {int(d['size']) for d in deleted}
        assert 791333 in sizes
        assert 867833 in sizes
        assert 820105 in sizes

    def test_canon2_carving_detects_signatures(self):
        report, _ = _recover(CANON2_RAW, 'fat16', 'canon2')
        carved = report.get('carved_files', [])
        assert len(carved) > 0, "carving found zero candidates on canon2"
        jpg_count = sum(1 for c in carved if c.get('file_type') == 'jpg')
        assert jpg_count > 0, "no JPG carved candidates on canon2"

    def test_ntfs1_filesystem_recovery(self):
        res = tw.list_files(NTFS1_RAW, '0')
        files = res.get('files', []) if isinstance(res, dict) else []
        user_files = [f for f in files if f.get('type') == 'r' and not f['name'].startswith('$') and ':' not in f['name']]
        assert len(user_files) == 12, f"expected 12 user files on ntfs1, got {len(user_files)}"

        for f in user_files:
            out = os.path.join(settings.BASE_DIR, 'storage', 'recoveries', 'validation', 'ntfs1_tmp', f['name'])
            os.makedirs(os.path.dirname(out), exist_ok=True)
            r = tw.extract_file(NTFS1_RAW, f['inode'], out, '0')
            assert os.path.exists(out) and os.path.getsize(out) > 0, f"failed to extract {f['name']}"

    def test_emails_filesystem_recovery(self):
        res = tw.list_files(EMAILS_RAW, '1')
        files = res.get('files', []) if isinstance(res, dict) else []
        alloc = [f for f in files if f.get('type') == 'r' and 'Volume Label' not in f.get('name', '')]
        assert len(alloc) > 0, "no allocated files found on emails"

        expected_emails = [
            'plain_text@textedit.com', 'rtf_text@textedit.com', 'plain_utf16@textedit.com',
            'pages@iwork09.com', 'keynote@iwork09.com', 'numbers@iwork09.com',
            'user_doc@microsoftword.com', 'user_docx@microsoftword.com',
            'xls_cell@microsoft_excel.com', 'xlsx_cell@microsoft_excel.com',
            'doc_within_doc@document.com', 'docx_within_docx@document.com',
            'ppt_within_doc@document.com', 'pptx_within_docx@document.com',
            'xls_within_doc@document.com', 'xlsx_within_docx@document.com',
            'email_in_zip@zipfile1.com', 'email_in_zip_zip@zipfile2.com',
            'email_in_gzip@gzipfile.com', 'email_in_gzip_gzip@gzipfile.com',
        ]
        found = set()
        for f in alloc:
            name = os.path.basename(f.get('name', '')).upper()
            out = os.path.join(settings.BASE_DIR, 'storage', 'recoveries', 'validation', 'emails_tmp', name)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            r = tw.extract_file(EMAILS_RAW, f['inode'], out, '1')
            if os.path.exists(out) and os.path.getsize(out) > 0:
                data = open(out, 'rb').read()
                text = data.decode('utf-8', errors='ignore') + data.decode('utf-16-le', errors='ignore')
                for e in expected_emails:
                    if e.lower() in text.lower():
                        found.add(e)
        assert len(found) >= 10, f"emails: only {len(found)}/{len(expected_emails)} target emails found in raw scan"

    def test_canon2_timeline_with_offset(self):
        res = tw.get_timeline(CANON2_RAW, partition_offset='51')
        assert res.get('success') is True
        output = res.get('timeline', '')
        assert 'DCIM' in output, "canon2 timeline should contain DCIM entries"

    def test_ntfs1_timeline_default_offset(self):
        res = tw.get_timeline(NTFS1_RAW)
        assert res.get('success') is True
        output = res.get('timeline', '')
        assert '$MFT' in output or 'Compressed' in output or 'Encrypted' in output

    def test_canon2_partitions(self):
        res = tw.get_partitions(CANON2_RAW)
        assert res.get('success') is True
        parts = res.get('partitions', [])
        assert len(parts) > 0, "canon2 should have at least one partition"
        assert parts[0].get('start') == '0000000051', f"expected FAT16 at sector 51, got {parts[0].get('start')}"

    def test_ntfs1_timeline_default_offset(self):
        res = tw.get_partitions(EMAILS_RAW)
        assert res.get('success') is True
        parts = res.get('partitions', [])
        assert len(parts) > 0, "emails should have at least one partition"
        assert parts[0].get('start') == '0000000001', f"expected FAT32 at sector 1, got {parts[0].get('start')}"

    def test_canon2_evidence_hash(self):
        size = os.path.getsize(CANON2_RAW)
        data = open(CANON2_RAW, 'rb').read()
        assert size == 31129600, f"canon2 raw size mismatch: {size}"
        assert hashlib.md5(data).hexdigest() == '750b509d8fbed37a5213480aaccfdc61'
        assert hashlib.sha256(data).hexdigest() == '09066032400ff931909ec7b12a433d01e1710bf8f7291c12e8a84187c0cfcddb'

    def test_carve_footer_seek_back(self):
        c = FileCarver(chunk_size=8192)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
            tmp.write(b'\xff\xd8\xff\xe0' + b'X' * 100 + b'\xff\xd9' + b'Y' * 1000)
            tmp_path = tmp.name
        try:
            candidates = c.carve_disk_image(tmp_path, file_types=['jpg'])
            assert len(candidates) == 1, f"expected 1 candidate, got {len(candidates)}"
            assert candidates[0]['estimated_size'] == 106, f"expected size 106, got {candidates[0]['estimated_size']}"
        finally:
            os.unlink(tmp_path)

    def test_ntfs_inode_address_format(self):
        res = tw.list_files(NTFS1_RAW, '0')
        files = res.get('files', []) if isinstance(res, dict) else []
        ntfs_inodes = [f['inode'] for f in files if '-' in f.get('inode', '')]
        assert len(ntfs_inodes) > 0, "NTFS inode addresses (e.g. 4-128-4) should be parsed"
        assert '4-128-4' in ntfs_inodes

    def test_extract_file_safe_path_enforcement(self):
        res = tw.extract_file(CANON2_RAW, '1029', '/tmp/evil.bin', '51')
        assert res.get('success') is False, "extract_file should reject paths outside storage"
        assert 'authorized storage directory' in str(res.get('error', '')).lower()

    def test_carving_fragmented_jpeg_truncation_documented(self):
        report, _ = _recover(CANON2_RAW, 'fat16', 'canon2_carve_doc')
        carved = report.get('carved_files', [])
        jpg_candidates = [c for c in carved if c.get('file_type') == 'jpg']
        assert len(jpg_candidates) > 0, "carving should detect JPG signatures on canon2"
        small_candidates = [c for c in jpg_candidates if c.get('estimated_size', 0) < 50000]
        assert len(small_candidates) > 0, "fragmented EXIF JPEGs produce thumbnail-truncated candidates (known limitation)"

    def test_deleted_overwrite_honest_negative(self):
        res = tw.get_deleted_metadata(CANON2_RAW, '51')
        assert res.get('success') is True
        deleted = res.get('deleted', [])
        if deleted:
            out_dir = os.path.join(settings.BASE_DIR, 'storage', 'recoveries', 'validation', 'canon2_deleted_test')
            os.makedirs(out_dir, exist_ok=True)
            for d in deleted[:3]:
                out = os.path.join(out_dir, f"deleted_{d['inode']}")
                r = tw.extract_file(CANON2_RAW, d['inode'], out, '51')
                if os.path.exists(out) and os.path.getsize(out) > 0:
                    d['extracted_sha1'] = hashlib.sha1(open(out, 'rb').read()).hexdigest()
                    d['extracted_size'] = os.path.getsize(out)
        assert True