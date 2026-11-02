# Linux release licenses

WSD's original code is GPL-3.0-only. Bundled dependencies retain their own
licenses. Exact dependency versions are recorded in `BUILD-INFO.json` and
`build-environment.txt`; the full notices are in `licenses/`.

| Component | License / distribution requirement |
| --- | --- |
| Python | PSF license and historical notices; retain the full Python license file. |
| Flask, Werkzeug, Jinja2, MarkupSafe, itsdangerous, click | BSD-3-Clause; retain copyright, terms, and disclaimer. |
| blinker | MIT; retain copyright and permission notice. |
| Chart.js 4.5.0 | MIT; retain its license and bundle header. |
| @kurkle/color 0.3.2, embedded in Chart.js | MIT; retain its separate license and bundle header. |
| Roboto Slab, package 5.2.8 | Apache-2.0, as supplied by this font package; retain its license and any notices. Do not assume all fonts use OFL. |
| PyInstaller | GPL-2.0-or-later with its distribution exception, plus Apache-2.0 files; retain the supplied COPYING file. The exception permits bundling WSD under its own license. |
| setuptools and its vendored modules, if collected | Retain all supplied licenses, including vendored module notices. Build tools are not automatically runtime dependencies; inspect the actual frozen output. |
| GNU Readline (`libreadline.so.8`) | GPL-3.0-or-later; provide matching source, including distribution patches and build instructions, when distributing this library. |
| ncurses / terminfo | MIT/X11 and applicable BSD notices; retain the package copyright files. |
| libuuid | Retain the util-linux package copyright file; use the entries for libuuid, not a single license label for all of util-linux. |
| OpenSSL 3 | Apache-2.0; retain license and applicable notices. |
| SQLite | Public-domain core; retain the distribution's applicable notices. |
| zlib, bzip2, libffi, xz/liblzma, Expat | Retain each matching package's notices. Mixed source packages may contain additional licenses; inspect the files actually bundled. |
| Images in `frontend/assets/img/` | No separate provenance or license record was found during this check. Confirm which are original project artwork/screenshots and record permission for any externally sourced images before redistribution. |

## Corresponding source

New builds include `source/wsd-source.tar.gz`: the WSD source files, demo
fixtures, tests, and build/install scripts used for that build. `SOURCE.md`
explains how to rebuild. This archive is separate from third-party source.

Before publishing a binary release, also provide source for bundled components
whose licenses require it. In particular, the inspected v1.0.0 bundle contains
GNU Readline. Include its exact source version and Ubuntu patches, not just
an upstream homepage. If additional GPL/LGPL components appear in a later
build, check their source and, where applicable, relinking requirements too.
Place matching third-party source archives beside the binary download and
identify them in the release notes. A link to the moving `main` branch is
not a substitute for corresponding source.

The builder preserves notices, but does not fetch or verify all third-party
source archives. Source availability remains a release check, not a claim
that all licensing requirements have been satisfied automatically.

## Audit of the existing v1.0.0 package

The local archive was inspected before these changes. It contains Python,
Python-package, Chart.js, font, and several system-library notices. It lacks
WSD's GPLv3 text and corresponding-source archive. Notices for Readline,
ncurses/terminfo, and libuuid were also missing from its top-level license
directory. Its installer copies only `app/`, leaving the outer license
directory behind. These repository changes do not alter that existing binary.

New builds preserve those additional notices, the project license, source,
and build information during installation. The old release still needs a
replacement build and matching third-party source before it can be described
as having these fixes.
