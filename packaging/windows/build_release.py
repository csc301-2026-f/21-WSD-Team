# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Build the Windows launcher with Python, the existing frontend and dependencies."""
import hashlib
import importlib.metadata
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tkinter
import zipfile

ROOT = Path(__file__).resolve().parents[2]
WINDOWS = ROOT / "packaging/windows"


def copy_licenses(destination):
    versions = {}
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata["Name"]
        versions[name] = distribution.version
        for item in distribution.files or []:
            if any(word in str(item).lower() for word in ("license", "copying", "notice")):
                path = Path(distribution.locate_file(item))
                if path.is_file():
                    target = destination / name / str(item)
                    # Distribution records can contain paths outside site-packages.
                    if not target.resolve().is_relative_to(destination.resolve()):
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, target)
    for directory in (Path(sys.base_prefix), Path(sys.base_prefix) / "Lib",
                      Path(tkinter.Tcl().eval("info library")),
                      Path(sys.base_prefix) / "tcl"):
        for path in directory.rglob("license*") if directory.name == "tcl" else directory.glob("LICENSE*"):
            if path.is_file():
                target = destination / "Python-Tcl-Tk" / path.parent.name / path.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
    (destination / "dependency-versions.txt").write_text(
        "\n".join(f"{name}=={version}" for name, version in sorted(versions.items())) + "\n",
        encoding="utf-8",
    )


def copy_source(destination):
    excluded = {"__pycache__", "_future", ".pytest_cache", ".venv"}
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for directory in ("backend", "frontend", "packaging/windows"):
            for path in sorted((ROOT / directory).rglob("*")):
                if path.is_file() and not excluded.intersection(path.parts) and path.suffix not in (".pyc", ".pyo"):
                    archive.write(path, "wsd-source/" + path.relative_to(ROOT).as_posix())
        for name in ("LICENSE", "COPYRIGHT.md", "README.md", "tests/fixtures/d2_demo/algo01_input.json",
                     "packaging/linux/build_release.py"):
            archive.write(ROOT / name, "wsd-source/" + name)


def main():
    if sys.platform != "win32":
        raise SystemExit("Build on Windows using 64-bit Python.")
    import struct
    if struct.calcsize("P") != 8:
        raise SystemExit("Use 64-bit Python for this build.")
    output = ROOT / "dist/windows"
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "WSD-windows-x86_64.zip"
    if destination.exists():
        raise SystemExit(f"Output already exists: {destination}. Move it before rebuilding.")
    with tempfile.TemporaryDirectory(prefix="wsd-windows-build-") as temporary:
        stage = Path(temporary)
        licenses = stage / "licenses"
        licenses.mkdir()
        # Reuse the Linux builder's offline web-asset preparation, without changing
        # Danny's frontend source files or invoking the Linux build.
        spec = importlib.util.spec_from_file_location("linux_assets", ROOT / "packaging/linux/build_release.py")
        assets = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(assets)
        frontend = assets.prepare_frontend(stage, licenses)
        subprocess.run([
            sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
            "--name", "WSD", "--paths", str(ROOT), "--paths", str(WINDOWS),
            "--distpath", str(stage / "frozen"), "--workpath", str(stage / "work"),
            "--specpath", str(stage), "--copy-metadata", "Flask", "--hidden-import", "win32timezone",
            "--add-data", f"{frontend};frontend",
            "--add-data", f"{ROOT / 'backend/db/schema.sql'};backend/db",
            "--add-data", f"{ROOT / 'tests/fixtures/d2_demo/algo01_input.json'};tests/fixtures/d2_demo",
            str(WINDOWS / "entrypoint.py"),
        ], cwd=ROOT, check=True)
        bundle = stage / "frozen/WSD"
        copy_licenses(licenses)
        shutil.copytree(licenses, bundle / "licenses")
        for name in ("LICENSE", "COPYRIGHT.md"):
            shutil.copy2(ROOT / name, bundle / name)
        copy_source(bundle / "wsd-source.zip")
        (bundle / "README.txt").write_text(
            "Wise Storage Director\n\n"
            "Double-click WSD.exe, then choose Start Monitoring or Start Demo.\n"
            "Monitoring requests Administrator access. Demo uses sample data.\n"
            "The dashboard opens in your browser at http://127.0.0.1:5000/.\n"
            "Use Stop and Exit to stop the backend and close WSD.\n\n"
            "Data and logs: %LOCALAPPDATA%\\WSD\n"
            "WSD is licensed under GNU GPL version 3; see LICENSE and COPYRIGHT.md.\n"
            "WSD source and build scripts: wsd-source.zip. Third-party notices: licenses/.\n",
            encoding="utf-8",
        )
        shutil.make_archive(str(destination.with_suffix("")), "zip", bundle.parent, "WSD")
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(".zip.sha256").write_text(f"{digest}  {destination.name}\n", encoding="ascii")
    print(destination)


if __name__ == "__main__":
    main()
