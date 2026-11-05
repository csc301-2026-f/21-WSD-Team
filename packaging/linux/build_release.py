# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Build a self-contained Linux bundle without changing the frontend sources."""
import base64
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
VERSION = "1.0.0"
NAME = f"wsd-{VERSION}-linux-x86_64-ubuntu24.04"
ASSETS = {
    "kurkle-color": (
        "https://registry.npmjs.org/@kurkle/color/-/color-0.3.2.tgz",
        "fuscdXJ9G1qb7W8VdHi+IwRqij3lBkosAm4ydQtEmbY58OzHXqQhvlxqEkoz0yssNVn38bcpRWgA9PP+OGoisw==",
    ),
    "chart.js": (
        "https://registry.npmjs.org/chart.js/-/chart.js-4.5.0.tgz",
        "aYeC/jDgSEx8SHWZvANYMioYMZ2KX02W6f6uVfyteuCGcadDLcYVHdfdygsTQkQ4TKn5lghoojAsPj5pu0SnvQ==",
    ),
    "roboto-slab": (
        "https://registry.npmjs.org/@fontsource-variable/roboto-slab/-/roboto-slab-5.2.8.tgz",
        "cdvOSwocP50xS01gXqnGxw7uFcCZQgn1IDlqiAmNuZP4uEVScYAKMDC+aWsbP1grn9QdMJ2frhcuVBNXniBVGA==",
    ),
}


def npm_files(name):
    url, integrity = ASSETS[name]
    with urllib.request.urlopen(url, timeout=60) as response:
        raw = response.read()
    if base64.b64encode(hashlib.sha512(raw).digest()).decode() != integrity:
        raise RuntimeError(f"Integrity check failed: {name}")
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        for item in archive.getmembers():
            if item.isfile():
                files[item.name] = archive.extractfile(item).read()
    return files


def select(files, endings):
    for ending in endings:
        for name, content in files.items():
            if name.endswith(ending):
                return content
    raise RuntimeError(f"Missing expected asset: {endings}")


def prepare_frontend(stage, licenses):
    frontend = stage / "frontend"
    shutil.copytree(ROOT / "frontend", frontend)
    vendor = frontend / "assets/vendor"
    vendor.mkdir(parents=True)
    chart = npm_files("chart.js")
    (vendor / "chart.umd.js").write_bytes(select(chart, ("/dist/chart.umd.js", "/dist/chart.umd.min.js")))
    (licenses / "Chart.js-LICENSE.md").write_bytes(select(chart, ("/LICENSE.md", "/LICENSE")))
    color = npm_files("kurkle-color")
    (licenses / "kurkle-color-LICENSE.md").write_bytes(select(color, ("/LICENSE.md", "/LICENSE")))
    font = npm_files("roboto-slab")
    (vendor / "roboto-slab-latin.woff2").write_bytes(select(font, ("/roboto-slab-latin-wght-normal.woff2",)))
    (licenses / "Roboto-Slab-LICENSE").write_bytes(select(font, ("/LICENSE", "/OFL.txt")))
    for name, content in font.items():
        if Path(name).name.lower().startswith("notice"):
            (licenses / ("Roboto-Slab-" + Path(name).name)).write_bytes(content)
    (vendor / "fonts.css").write_text(
        "@font-face { font-family: 'Roboto Slab'; font-style: normal; "
        "font-weight: 100 900; font-display: swap; "
        "src: url('./roboto-slab-latin.woff2') format('woff2'); }\n", encoding="utf-8")
    for page in frontend.rglob("*.html"):
        lines = []
        for line in page.read_text(encoding="utf-8").splitlines():
            if 'href="https://fonts.googleapis.com/css2?' in line:
                lines.append('<link href="../assets/vendor/fonts.css" rel="stylesheet">')
            elif 'rel="preconnect"' in line and "fonts." in line:
                continue
            else:
                lines.append(line.replace("https://cdn.jsdelivr.net/npm/chart.js", "../assets/vendor/chart.umd.js"))
        page.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return frontend


def copy_licenses(directory):
    packages = ("Flask", "Werkzeug", "Jinja2", "MarkupSafe", "click", "itsdangerous", "blinker", "PyInstaller", "setuptools")
    versions = {}
    for name in packages:
        distribution = importlib.metadata.distribution(name)
        versions[name] = distribution.version
        for item in distribution.files or []:
            if any(term in str(item).lower() for term in ("license", "copying", "notice")):
                source = Path(distribution.locate_file(item))
                if source.is_file():
                    target = directory / name / Path(str(item))
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    for name in ("libc6", "libssl3t64", "libsqlite3-0", "zlib1g", "libffi8", "libbz2-1.0", "liblzma5", "libexpat1",
                 "libreadline8t64", "libncursesw6", "libtinfo6", "libuuid1"):
        copyright_file = Path("/usr/share/doc") / name / "copyright"
        if copyright_file.is_file():
            shutil.copy2(copyright_file, directory / f"{name}-copyright")
        else:
            raise RuntimeError(f"Missing dependency copyright file: {copyright_file}")
    # Debian copyright files may refer to these complete texts by pathname.
    shutil.copytree("/usr/share/common-licenses", directory / "common-licenses")
    for candidate in (Path(sys.base_prefix) / "LICENSE", Path(os.__file__).parent / "LICENSE.txt"):
        if candidate.is_file():
            shutil.copy2(candidate, directory / "Python-LICENSE.txt")
            break
    else:
        with urllib.request.urlopen(f"https://raw.githubusercontent.com/python/cpython/v{platform.python_version()}/LICENSE", timeout=60) as response:
            (directory / "Python-LICENSE.txt").write_bytes(response.read())
    return versions


def copy_release_docs(release):
    source = ROOT / "packaging/linux"
    shutil.copy2(source / "install.sh", release / "install.sh")
    readme = (source / "README.md").read_text(encoding="utf-8")
    readme = readme.replace("../../deliverables/D2/WSD_TA_Frontend_Walkthrough.md",
                            "docs/WSD_TA_Frontend_Walkthrough.md")
    (release / "README.md").write_text(readme, encoding="utf-8")
    if (source / "images").is_dir():
        shutil.copytree(source / "images", release / "images")
    docs = release / "docs"
    docs.mkdir()
    upstream = ROOT / "deliverables/D2"
    shutil.copy2(upstream / "WSD_TA_Frontend_Walkthrough.md", docs)
    shutil.copytree(upstream / "frontend_pictures", docs / "frontend_pictures")


def copy_project_source(release):
    """Include the actual WSD build inputs, rather than a moving branch URL."""
    for name in ("LICENSE", "COPYRIGHT.md"):
        shutil.copy2(ROOT / name, release / name)
    copyright_notice = (release / "COPYRIGHT.md").read_text(encoding="utf-8")
    (release / "COPYRIGHT.md").write_text(copyright_notice.replace(
        "packaging/linux/THIRD_PARTY_NOTICES.md", "THIRD_PARTY_NOTICES.md"), encoding="utf-8")
    shutil.copy2(ROOT / "packaging/linux/THIRD_PARTY_NOTICES.md", release)
    source = release / "source"
    source.mkdir()
    excluded = {"__pycache__", "_future", ".pytest_cache", ".venv"}
    files = []
    for folder in ("backend", "frontend", "packaging/linux", "tests"):
        files.extend(path for path in (ROOT / folder).rglob("*")
                     if path.is_file() and not excluded.intersection(path.parts)
                     and path.suffix not in (".pyc", ".pyo")
                     and path.name not in ("smoke_release.py", "source-snapshot.json"))
    files.extend(ROOT / name for name in ("LICENSE", "COPYRIGHT.md", "README.md", "package.json"))
    walkthrough = ROOT / "deliverables/D2"
    files.append(walkthrough / "WSD_TA_Frontend_Walkthrough.md")
    files.extend(path for path in (walkthrough / "frontend_pictures").rglob("*") if path.is_file())
    with tarfile.open(source / "wsd-source.tar.gz", "w:gz") as archive:
        for path in sorted(set(files)):
            archive.add(path, arcname="wsd-source/" + path.relative_to(ROOT).as_posix())
    (release / "SOURCE.md").write_text(
        "# Corresponding source\n\n"
        "`source/wsd-source.tar.gz` contains WSD's source and build/install scripts "
        "from this build. Extract it, create a Python virtual environment, install "
        "`packaging/linux/requirements-build.txt`, then run "
        "`python packaging/linux/build_release.py` on the documented build target "
        "(Ubuntu 24.04 x86-64, glibc 2.39). Building downloads the pinned browser assets. "
        "Exact Python and dependency versions are in `BUILD-INFO.json` and "
        "`build-environment.txt`; use those versions to reproduce this build.\n\n"
        "The project repository is https://github.com/csc301-2026-f/21-WSD-Team. "
        "Use the included archive for this binary's WSD source, rather than a later branch.\n\n"
        "This WSD archive does not include third-party runtime sources. See "
        "`THIRD_PARTY_NOTICES.md` for the additional source files that must accompany "
        "a binary release, including the matching GNU Readline source and patches.\n",
        encoding="utf-8")


def main():
    if sys.platform != "linux" or platform.machine() != "x86_64":
        raise SystemExit("Build on Ubuntu 24.04 x86-64 Linux.")
    if platform.libc_ver() != ("glibc", "2.39"):
        raise SystemExit("Use a glibc 2.39 build host for this release target.")
    output = ROOT / "dist/linux"
    output.mkdir(parents=True, exist_ok=True)
    destination = output / f"{NAME}.tar.gz"
    if destination.exists():
        raise SystemExit(f"Output already exists: {destination}; preserve or move it before rebuilding.")
    with tempfile.TemporaryDirectory(prefix="wsd-release-build-") as temporary:
        stage = Path(temporary)
        release = stage / NAME
        release.mkdir()
        licenses = release / "licenses"
        licenses.mkdir()
        versions = copy_licenses(licenses)
        frontend = prepare_frontend(stage, licenses)
        subprocess.run([
            sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
            "--name", "wsd", "--paths", str(ROOT),
            "--distpath", str(stage / "frozen"), "--workpath", str(stage / "work"),
            "--specpath", str(stage), "--copy-metadata", "Flask",
            "--add-data", f"{frontend}:frontend",
            "--add-data", f"{ROOT / 'backend/db/schema.sql'}:backend/db",
            "--add-data", f"{ROOT / 'tests/fixtures/d2_demo/algo01_input.json'}:tests/fixtures/d2_demo",
            str(ROOT / "packaging/linux/entrypoint.py"),
        ], check=True, cwd=ROOT)
        shutil.copytree(stage / "frozen/wsd", release / "app")
        copy_release_docs(release)
        copy_project_source(release)
        (release / "install.sh").chmod(0o755)
        snapshot = ROOT / "packaging/linux/source-snapshot.json"
        sources = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                   for folder in ("backend", "frontend", "packaging/linux")
                   for path in sorted((ROOT / folder).rglob("*"))
                   if path.is_file() and "__pycache__" not in path.parts
                   and path != ROOT / "packaging/linux/smoke_release.py"}
        manifest = {
            "version": VERSION, "built_at_utc": datetime.now(timezone.utc).isoformat(),
            "target": "Ubuntu 24.04 x86-64; glibc 2.39+", "python": platform.python_version(),
            "dependencies": versions, "browser_assets": ASSETS,
            "corresponding_source_sha256": hashlib.sha256(
                (release / "source/wsd-source.tar.gz").read_bytes()).hexdigest(),
            "source_snapshot": json.loads(snapshot.read_text()) if snapshot.exists() else {},
            "source_sha256": sources,
        }
        (release / "BUILD-INFO.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        lock = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)
        (release / "build-environment.txt").write_text(lock, encoding="utf-8")
        with tarfile.open(destination, "w:gz") as archive:
            archive.add(release, arcname=NAME)
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        destination.with_suffix(destination.suffix + ".sha256").write_text(f"{digest}  {destination.name}\n", encoding="ascii")
        (output / "BUILD-INFO.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (output / "build-environment.txt").write_text(lock, encoding="utf-8")
        print(json.dumps({"archive": str(destination), "bytes": destination.stat().st_size, "sha256": digest}), flush=True)


if __name__ == "__main__":
    main()
