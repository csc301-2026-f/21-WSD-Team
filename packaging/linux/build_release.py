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
    font = npm_files("roboto-slab")
    (vendor / "roboto-slab-latin.woff2").write_bytes(select(font, ("/roboto-slab-latin-wght-normal.woff2",)))
    (licenses / "Roboto-Slab-LICENSE").write_bytes(select(font, ("/LICENSE", "/OFL.txt")))
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
    packages = ("Flask", "Werkzeug", "Jinja2", "MarkupSafe", "click", "itsdangerous", "blinker", "PyInstaller")
    versions = {}
    for name in packages:
        distribution = importlib.metadata.distribution(name)
        versions[name] = distribution.version
        for item in distribution.files or []:
            if "license" in str(item).lower() or "copying" in str(item).lower():
                source = Path(distribution.locate_file(item))
                if source.is_file():
                    target = directory / name / Path(str(item))
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    for name in ("libc6", "libssl3t64", "libsqlite3-0", "zlib1g", "libffi8", "libbz2-1.0", "liblzma5", "libexpat1"):
        copyright_file = Path("/usr/share/doc") / name / "copyright"
        if copyright_file.is_file():
            shutil.copy2(copyright_file, directory / f"{name}-copyright")
    for candidate in (Path(sys.base_prefix) / "LICENSE", Path(os.__file__).parent / "LICENSE.txt"):
        if candidate.is_file():
            shutil.copy2(candidate, directory / "Python-LICENSE.txt")
            break
    else:
        with urllib.request.urlopen(f"https://raw.githubusercontent.com/python/cpython/v{platform.python_version()}/LICENSE", timeout=60) as response:
            (directory / "Python-LICENSE.txt").write_bytes(response.read())
    return versions


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
        for name in ("install.sh", "README.md"):
            shutil.copy2(ROOT / "packaging/linux" / name, release / name)
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
