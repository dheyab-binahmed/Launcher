class LauncherError(Exception):
    """An error that can be displayed safely to a player."""


class ManifestError(LauncherError):
    pass


class DownloadError(LauncherError):
    pass


class VerificationError(LauncherError):
    pass


class InstallError(LauncherError):
    pass
