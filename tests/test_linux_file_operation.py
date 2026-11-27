# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Safety checks for Linux MergerFS move execution and status reporting."""
import os

from backend.linux import file_operation
from backend.linux.models import ErrorCode


class ExitedProcess:
    def __init__(self, returncode):
        self.returncode = returncode

    def poll(self):
        return self.returncode


def test_zero_exit_without_moving_source_is_not_reported_as_success(tmp_path):
    source = tmp_path / "source.bin"
    destination = tmp_path / "destination.bin"
    source.write_bytes(b"source")
    destination.write_bytes(b"pre-existing destination")
    handle = file_operation.MoveHandle(
        str(source), str(source), str(destination), source.stat().st_size, ExitedProcess(0)
    )

    assert handle.result() is ErrorCode.MOVE_FAILED
    assert source.exists()
    assert destination.read_bytes() == b"pre-existing destination"


def test_success_requires_the_source_to_be_gone_and_destination_to_exist(tmp_path):
    source = tmp_path / "source.bin"
    destination = tmp_path / "destination.bin"
    source.write_bytes(b"moved content")
    total_bytes = source.stat().st_size
    os.replace(source, destination)
    handle = file_operation.MoveHandle(
        str(source), str(source), str(destination), total_bytes, ExitedProcess(0)
    )

    assert handle.result() == str(destination)
    assert not source.exists()
    assert destination.read_bytes() == b"moved content"


def test_move_command_refuses_to_overwrite_a_destination(tmp_path, monkeypatch):
    source = tmp_path / "source.bin"
    source.write_bytes(b"source")
    destination_mount = tmp_path / "target"
    destination_mount.mkdir()
    calls = []

    def fake_popen(args, **kwargs):
        calls.append((args, kwargs))
        return ExitedProcess(None)

    monkeypatch.setattr(file_operation, "resolve_mergerfs_path", lambda _path: (str(source), "source.bin"))
    monkeypatch.setattr(file_operation.subprocess, "Popen", fake_popen)

    handle = file_operation.start_mergerfs_move(str(source), str(destination_mount))

    assert isinstance(handle, file_operation.MoveHandle)
    assert calls[0][0][:3] == ["mv", "--no-clobber", "--"]
    assert calls[0][0][3] == str(source)
    assert calls[0][0][4] == str(destination_mount / "source.bin")


def test_missing_source_fails_before_starting_a_move(tmp_path):
    assert file_operation.start_mergerfs_move(
        str(tmp_path / "missing.bin"), str(tmp_path)
    ) is ErrorCode.FILE_NOT_FOUND


def test_non_directory_destination_fails_before_starting_a_move(tmp_path):
    source = tmp_path / "source.bin"
    source.write_bytes(b"source")
    destination = tmp_path / "destination-file"
    destination.write_bytes(b"not a mount directory")

    assert file_operation.start_mergerfs_move(str(source), str(destination)) is ErrorCode.NOT_A_DIRECTORY
