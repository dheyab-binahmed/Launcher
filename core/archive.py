from __future__ import annotations

import stat
import zipfile
from pathlib import Path

from .errors import ArchiveError
from .platform_utils import safe_child

MAX_ARCHIVE_MEMBERS = 4096
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024


def extract_zip_safely(archive: Path, destination: Path) -> None:
    """Extract a release archive without accepting traversal, links, or zip bombs."""
    try:
        with zipfile.ZipFile(archive) as bundle:
            members = bundle.infolist()
            if len(members) > MAX_ARCHIVE_MEMBERS:
                raise ArchiveError("The archive contains too many files.")
            if sum(member.file_size for member in members) > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                raise ArchiveError("The archive is too large to install safely.")

            targets: set[str] = set()
            for member in members:
                if not member.filename:
                    raise ArchiveError("The archive contains an invalid path.")
                mode = member.external_attr >> 16
                if mode and stat.S_IFMT(mode) == stat.S_IFLNK:
                    raise ArchiveError("The archive contains a symbolic link.")
                target = safe_child(destination, member.filename)
                key = str(target).casefold()
                if key in targets:
                    raise ArchiveError("The archive contains duplicate paths.")
                targets.add(key)

            for member in members:
                target = safe_child(destination, member.filename)
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(member) as source, target.open("xb") as output:
                    while chunk := source.read(1024 * 1024):
                        output.write(chunk)
    except ArchiveError:
        raise
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise ArchiveError("The archive is invalid.") from error
