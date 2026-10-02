import hashlib

from app.utils.hashing import sha256_file


def test_sha256_matches_hashlib_reference(tmp_path):
    f = tmp_path / "sample.bin"
    f.write_bytes(b"microspot vision test content" * 1000)

    expected = hashlib.sha256(f.read_bytes()).hexdigest()
    assert sha256_file(f) == expected


def test_sha256_differs_for_different_content(tmp_path):
    f1 = tmp_path / "a.bin"
    f2 = tmp_path / "b.bin"
    f1.write_bytes(b"content A")
    f2.write_bytes(b"content B")

    assert sha256_file(f1) != sha256_file(f2)


def test_sha256_identical_for_identical_content(tmp_path):
    f1 = tmp_path / "a.bin"
    f2 = tmp_path / "b.bin"
    f1.write_bytes(b"same bytes")
    f2.write_bytes(b"same bytes")

    assert sha256_file(f1) == sha256_file(f2)
