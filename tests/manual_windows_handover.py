"""Disposable, real-process verification for the generated Windows updater helper.

Run manually on Windows; it compiles a tiny test launcher in a temporary
directory and removes that directory when finished.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from core.updater import LauncherUpdater


COMPILER = Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe")
SOURCE = """using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
class TestLauncher {
    static int Main() {
        string directory = AppDomain.CurrentDomain.BaseDirectory;
        File.WriteAllText(Path.Combine(directory, \"started.txt\"), Process.GetCurrentProcess().Id.ToString());
        if (File.Exists(Path.Combine(directory, \"exit-now.txt\"))) return 47;
        Thread.Sleep(3000);
        return 0;
    }
}
"""


def wait_for(path: Path, timeout: float = 5) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for {path}")


def run_helper(script: Path) -> subprocess.Popen[str]:
    return subprocess.Popen(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def main() -> None:
    assert COMPILER.is_file(), "The Windows .NET compiler is required for this disposable test."
    with tempfile.TemporaryDirectory(prefix="MeluUpdaterReal-") as temporary:
        root = Path(temporary)
        source, binary = root / "TestLauncher.cs", root / "TestLauncher.exe"
        source.write_text(SOURCE, encoding="ascii")
        subprocess.run([str(COMPILER), "/nologo", f"/out:{binary}", str(source)], check=True)
        external_settings, external_assets = root / "external-settings.json", root / "external-game-assets.bin"
        external_settings.write_text('{"language":"en","keep":true}', encoding="utf-8")
        external_assets.write_bytes(b"unchanged-game-assets")
        expected_settings, expected_assets = external_settings.read_bytes(), external_assets.read_bytes()

        def install(name: str, exits_immediately: bool = False) -> Path:
            location = root / name
            location.mkdir()
            shutil.copy2(binary, location / "MeluLauncher.exe")
            (location / "_internal").mkdir()
            (location / "marker.txt").write_text(name, encoding="utf-8")
            (location / "settings.json").write_text("keep-settings", encoding="utf-8")
            if exits_immediately:
                (location / "exit-now.txt").write_text("x", encoding="utf-8")
            return location

        def helper(old: Path, new: Path, pid: int, label: str) -> Path:
            staging = root / f"{label}-staging"
            staging.mkdir()
            script = staging / "replace-launcher.ps1"
            LauncherUpdater._write_windows_helper(script, old, new, pid)
            return script

        def restored(old: Path, label: str) -> None:
            assert old.is_dir(), f"{label}: old directory was not restored"
            assert (old / "marker.txt").read_text(encoding="utf-8") == old.name
            assert (old / "settings.json").read_text(encoding="utf-8") == "keep-settings"
            assert not list(root.glob(f"{old.name}.previous-*")), f"{label}: recovery backup remained"

        results: list[dict[str, object]] = []
        # Success: prove the helper does not move the installation until the
        # exact, independently running old launcher PID has exited.
        old, new = install("success-old"), install("success-new")
        old_process = subprocess.Popen([str(old / "MeluLauncher.exe")])
        wait_for(old / "started.txt")
        script = helper(old, new, old_process.pid, "success")
        process = run_helper(script)
        time.sleep(0.35)
        assert old.exists() and new.exists(), "Handover began before the old PID exited"
        assert not list(root.glob("success-old.previous-*")), "Backup appeared before old PID exited"
        assert old_process.wait(timeout=5) == 0
        backup = root / f"success-old.previous-{old_process.pid}"
        wait_for(backup)
        assert process.wait(timeout=10) == 0, process.stderr.read()
        assert (old / "marker.txt").read_text(encoding="utf-8") == "success-new"
        wait_for(old / "started.txt")
        new_pid = int((old / "started.txt").read_text(encoding="utf-8"))
        time.sleep(1)
        assert str(new_pid) in subprocess.run(
            ["tasklist", "/FI", f"PID eq {new_pid}"], capture_output=True, text=True, check=True
        ).stdout, "The replacement launcher exited during verification"
        assert not list(root.glob("success-old.previous-*")), "Backup was not cleaned after successful startup"
        assert not script.parent.exists(), "Successful update left its staging directory behind"
        results.append({"scenario": "real_handover", "new_pid": new_pid, "backup_cleaned_after_startup": True})

        # Start failure due to a missing executable, and a separately missing
        # staged directory (replacement failure), must both restore the old app.
        old, new = install("missing-executable-old"), root / "missing-executable-new"
        new.mkdir(); (new / "_internal").mkdir()
        failed = run_helper(helper(old, new, 999999, "missing-executable"))
        assert failed.wait(timeout=10) != 0; restored(old, "missing executable")
        assert not (root / "missing-executable-staging").exists()
        results.append({"scenario": "missing_executable_recovery"})

        old = install("replacement-failure-old")
        failed = run_helper(helper(old, root / "staged-directory-missing", 999999, "replacement-failure"))
        assert failed.wait(timeout=10) != 0; restored(old, "replacement failure")
        assert not (root / "replacement-failure-staging").exists()
        results.append({"scenario": "replacement_failure_recovery"})

        old, new = install("startup-exit-old"), install("startup-exit-new", exits_immediately=True)
        failed = run_helper(helper(old, new, 999999, "startup-exit"))
        assert failed.wait(timeout=10) != 0; restored(old, "startup exit")
        assert not (root / "startup-exit-staging").exists()
        results.append({"scenario": "immediate_exit_recovery"})

        assert external_settings.read_bytes() == expected_settings
        assert external_assets.read_bytes() == expected_assets
        print(json.dumps({"results": results, "external_settings_unchanged": True,
                          "external_assets_unchanged": True, "temporary_root_cleaned": True}))


if __name__ == "__main__":
    main()
