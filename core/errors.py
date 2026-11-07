class LauncherError(Exception):
    """An error that can be displayed safely to a player."""


class ManifestError(LauncherError):
    pass


class ManifestUnavailableError(LauncherError):
    """The release manifest itself could not be retrieved."""
    pass


class DownloadError(LauncherError):
    pass


class ArchiveError(LauncherError):
    pass


class VerificationError(LauncherError):
    pass


class InstallError(LauncherError):
    pass
