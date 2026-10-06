"""Verify historical byte hashes allowing only Git LF/CRLF checkout changes.

This does not redefine a stored raw hash or normalize JSON whitespace/content.
Current byte hashes must still be recorded as current byte hashes by exporters.
"""
import hashlib


def verify_source_hash(raw, recorded_sha256):
    actual = hashlib.sha256(raw).hexdigest()
    candidates = [('exact_bytes', actual)]
    lf = raw.replace(b'\r\n', b'\n')
    candidates.extend([
        ('lf_checkout_equivalent', hashlib.sha256(lf).hexdigest()),
        ('crlf_checkout_equivalent', hashlib.sha256(lf.replace(b'\n', b'\r\n')).hexdigest()),
    ])
    for mode, candidate in candidates:
        if candidate == recorded_sha256:
            return {'actual_sha256': actual, 'recorded_sha256': recorded_sha256,
                    'verification': mode}
    raise ValueError('來源內容雜湊不符；差異不只是 LF／CRLF 換行')
