"""Line-ending equivalence does not permit other source changes."""
import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch

from pilot.data import BENCH, ROOT
from pilot.provenance import verify_source_hash


class ProvenanceTests(unittest.TestCase):
    def test_only_lf_crlf_equivalence_is_accepted(self):
        raw = b'[\n  ["source\\ntext"]\n]\n'
        crlf = raw.replace(b'\n', b'\r\n')
        for current in (raw, crlf):
            for recorded in (raw, crlf):
                result = verify_source_hash(current, hashlib.sha256(recorded).hexdigest())
                self.assertEqual(result['actual_sha256'], hashlib.sha256(current).hexdigest())
        for changed in (raw.replace(b'source', b'changed'), raw + b'\n', raw.replace(b'  ', b' '),
                        raw.replace(b'\\n', b'\\r\\n')):
            with self.assertRaises(ValueError):
                verify_source_hash(changed, hashlib.sha256(crlf).hexdigest())

    def test_saved_sources_reproduce_with_both_checkout_line_endings(self):
        from test_structure import StructureTests
        from test_social_tradeoffs import SocialTradeoffArtifacts
        read_bytes = Path.read_bytes
        for style in ('lf', 'crlf'):
            def checkout(path):
                raw = read_bytes(path)
                if path.parent in (BENCH, ROOT / 'pilot/structured'):
                    raw = raw.replace(b'\r\n', b'\n')
                    if style == 'crlf':
                        raw = raw.replace(b'\n', b'\r\n')
                return raw
            with self.subTest(checkout=style), patch.object(Path, 'read_bytes', checkout):
                StructureTests('test_full_inventory_and_saved_output').test_full_inventory_and_saved_output()
                SocialTradeoffArtifacts('test_subset_is_exact_and_source_mapped').test_subset_is_exact_and_source_mapped()
