from pathlib import Path
import hashlib
import pytest
from core.errors import VerificationError
from core.verifier import verify_file


def test_size_and_hash_validation(tmp_path: Path):
    file = tmp_path / "data.bin"; file.write_bytes(b"verified")
    verify_file(file, 8, hashlib.sha256(b"verified").hexdigest())
    with pytest.raises(VerificationError): verify_file(file, 7, hashlib.sha256(b"verified").hexdigest())
    with pytest.raises(VerificationError): verify_file(file, 8, "0" * 64)
