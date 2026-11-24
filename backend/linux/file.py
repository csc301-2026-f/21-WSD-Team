# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
from dataclasses import dataclass
import ctypes
import os
import stat
import threading

from bcc import BPF

from .models import File, ErrorCode, FileCounters
from .constants import *


BPF_PROGRAM_HEADER = r"""
#include <linux/fs.h>
#include <linux/uio.h>

struct file_key {
    u64 dev;
    u64 ino;
    u64 gen;
};

struct file_stats {
    u64 read_attempts;
    u64 read_requested_bytes;
    u64 read_success_ops;
    u64 read_completed_bytes;
    u64 read_gap_sum;
    u64 read_gap_count;
    u64 write_attempts;
    u64 write_requested_bytes;
    u64 write_success_ops;
    u64 write_completed_bytes;
    u64 write_gap_sum;
    u64 write_gap_count;
};

struct stream_state {
    u64 dev;
    u64 ino;
    u64 read_end;
    u64 write_end;
    u64 has_read;
    u64 has_write;
};

BPF_HASH(tracked, struct file_key, u32, MAX_TRACKED);
BPF_PERCPU_ARRAY(stats, struct file_stats, MAX_TRACKED);
BPF_TABLE("lru_hash", u64, struct stream_state, streams, MAX_STREAMS);
BPF_ARRAY(calibration_tid, u32, 1);
BPF_ARRAY(calibration_key, struct file_key, 1);

static __always_inline int get_file_key(struct file *file, struct file_key *key)
{
    struct inode *inode = NULL;
    struct super_block *sb = NULL;
    dev_t dev = 0;
    unsigned long ino = 0;
    u32 gen = 0;

    if (bpf_probe_read_kernel(&inode, sizeof(inode), &file->f_inode) || !inode)
        return -1;
    if (bpf_probe_read_kernel(&ino, sizeof(ino), &inode->i_ino))
        return -1;
    if (bpf_probe_read_kernel(&gen, sizeof(gen), &inode->i_generation))
        return -1;
    if (bpf_probe_read_kernel(&sb, sizeof(sb), &inode->i_sb) || !sb)
        return -1;
    if (bpf_probe_read_kernel(&dev, sizeof(dev), &sb->s_dev))
        return -1;

    key->dev = dev;
    key->ino = ino;
    key->gen = gen;
    return 0;
}

static __always_inline int is_calibration_thread(void)
{
    int zero = 0;
    u32 *tid = calibration_tid.lookup(&zero);

    return tid && *tid != 0 && *tid == (u32)bpf_get_current_pid_tgid();
}

static __always_inline int calibrate(struct file *file)
{
    int zero = 0;
    struct file_key key = {};
    struct file_key *out;

    if (!is_calibration_thread())
        return 0;

    if (get_file_key(file, &key) == 0) {
        out = calibration_key.lookup(&zero);
        if (out) {
            out->dev = key.dev;
            out->ino = key.ino;
            out->gen = key.gen;
        }
    }
    return 1;
}

static __always_inline struct file_stats *lookup_stats(struct file *file, struct file_key *key)
{
    u32 *slot;

    if (get_file_key(file, key))
        return NULL;

    slot = tracked.lookup(key);
    if (!slot)
        return NULL;

    return stats.lookup((int *)slot);
}

static __always_inline void on_entry(struct file *file, u64 requested, int is_write)
{
    struct file_key key = {};
    struct file_stats *s;

    if (calibrate(file))
        return;

    s = lookup_stats(file, &key);
    if (!s)
        return;

    if (is_write) {
        s->write_attempts += 1;
        s->write_requested_bytes += requested;
    } else {
        s->read_attempts += 1;
        s->read_requested_bytes += requested;
    }
}

static __always_inline void on_exit(struct file *file, loff_t *pos, long ret, int is_write)
{
    struct file_key key = {};
    struct file_stats *s;
    struct stream_state zero = {};
    struct stream_state *st;
    loff_t end = 0;
    u64 start;
    u64 previous_end;
    u64 gap;
    u64 stream_key;

    if (ret <= 0)
        return;
    if (is_calibration_thread())
        return;

    s = lookup_stats(file, &key);
    if (!s)
        return;

    if (is_write) {
        s->write_success_ops += 1;
        s->write_completed_bytes += ret;
    } else {
        s->read_success_ops += 1;
        s->read_completed_bytes += ret;
    }

    if (!pos)
        return;
    if (bpf_probe_read_kernel(&end, sizeof(end), pos))
        return;
    if (end < ret)
        return;

    start = (u64)end - (u64)ret;
    stream_key = (u64)file;

    st = streams.lookup_or_try_init(&stream_key, &zero);
    if (!st)
        return;

    if (st->dev != key.dev || st->ino != key.ino) {
        st->dev = key.dev;
        st->ino = key.ino;
        st->has_read = 0;
        st->has_write = 0;
    }

    if (is_write) {
        if (st->has_write) {
            previous_end = st->write_end;
            gap = start > previous_end ? start - previous_end : previous_end - start;
            s->write_gap_sum += gap;
            s->write_gap_count += 1;
        }
        st->write_end = (u64)end;
        st->has_write = 1;
    } else {
        if (st->has_read) {
            previous_end = st->read_end;
            gap = start > previous_end ? start - previous_end : previous_end - start;
            s->read_gap_sum += gap;
            s->read_gap_count += 1;
        }
        st->read_end = (u64)end;
        st->has_read = 1;
    }
}

static __always_inline u64 iovec_total(const struct iovec *vec, unsigned long vlen)
{
    u64 total = 0;
    struct iovec iov = {};

    #pragma unroll
    for (u32 i = 0; i < MAX_IOVEC; i++) {
        if (i >= vlen)
            break;
        if (bpf_probe_read_user(&iov, sizeof(iov), &vec[i]))
            break;
        total += iov.iov_len;
    }
    return total;
}

static __always_inline u64 iter_count(struct iov_iter *iter)
{
    size_t count = 0;

    bpf_probe_read_kernel(&count, sizeof(count), &iter->count);
    return count;
}
"""

BPF_PROBES = {
    "vfs_read": r"""
KFUNC_PROBE(vfs_read, struct file *file, char *buf, size_t count, loff_t *pos)
{
    on_entry(file, count, 0);
    return 0;
}

KRETFUNC_PROBE(vfs_read, struct file *file, char *buf, size_t count, loff_t *pos, ssize_t ret)
{
    on_exit(file, pos, ret, 0);
    return 0;
}
""",
    "vfs_write": r"""
KFUNC_PROBE(vfs_write, struct file *file, const char *buf, size_t count, loff_t *pos)
{
    on_entry(file, count, 1);
    return 0;
}

KRETFUNC_PROBE(vfs_write, struct file *file, const char *buf, size_t count, loff_t *pos, ssize_t ret)
{
    on_exit(file, pos, ret, 1);
    return 0;
}
""",
    "vfs_readv": r"""
KFUNC_PROBE(vfs_readv, struct file *file, const struct iovec *vec, unsigned long vlen, loff_t *pos, rwf_t flags)
{
    on_entry(file, iovec_total(vec, vlen), 0);
    return 0;
}

KRETFUNC_PROBE(vfs_readv, struct file *file, const struct iovec *vec, unsigned long vlen, loff_t *pos, rwf_t flags, ssize_t ret)
{
    on_exit(file, pos, ret, 0);
    return 0;
}
""",
    "vfs_writev": r"""
KFUNC_PROBE(vfs_writev, struct file *file, const struct iovec *vec, unsigned long vlen, loff_t *pos, rwf_t flags)
{
    on_entry(file, iovec_total(vec, vlen), 1);
    return 0;
}

KRETFUNC_PROBE(vfs_writev, struct file *file, const struct iovec *vec, unsigned long vlen, loff_t *pos, rwf_t flags, ssize_t ret)
{
    on_exit(file, pos, ret, 1);
    return 0;
}
""",
    "vfs_iter_read": r"""
KFUNC_PROBE(vfs_iter_read, struct file *file, struct iov_iter *iter, loff_t *pos, rwf_t flags)
{
    on_entry(file, iter_count(iter), 0);
    return 0;
}

KRETFUNC_PROBE(vfs_iter_read, struct file *file, struct iov_iter *iter, loff_t *pos, rwf_t flags, ssize_t ret)
{
    on_exit(file, pos, ret, 0);
    return 0;
}
""",
    "vfs_iter_write": r"""
KFUNC_PROBE(vfs_iter_write, struct file *file, struct iov_iter *iter, loff_t *pos, rwf_t flags)
{
    on_entry(file, iter_count(iter), 1);
    return 0;
}

KRETFUNC_PROBE(vfs_iter_write, struct file *file, struct iov_iter *iter, loff_t *pos, rwf_t flags, ssize_t ret)
{
    on_exit(file, pos, ret, 1);
    return 0;
}
""",
}

REQUIRED_PROBES = ("vfs_read", "vfs_write")




COUNTER_FIELDS = tuple(FileCounters.__dataclass_fields__)


def kernel_dev(st_dev: int) -> int:
    """
    Converts st_dev to the device number used by the kernel.

    :param st_dev: device number from os.stat
    :return: kernel device number
    """
    major = os.major(st_dev)
    minor = os.minor(st_dev)
    return (major << KERNEL_DEV_MINOR_BITS) | minor


def resolve_file(file_path: str) -> File | ErrorCode:
    """
    Gets information about a file from its path.

    :param file_path: absolute path of the file
    :return: a File object, or an ErrorCode if the file cannot be used
    """
    if not os.path.isabs(file_path):
        return ErrorCode.PATH_NOT_ABSOLUTE

    real_path = os.path.realpath(file_path)

    try:
        file_info = os.stat(real_path)
    except FileNotFoundError:
        return ErrorCode.FILE_NOT_FOUND
    except PermissionError:
        return ErrorCode.PERMISSION_DENIED
    except OSError:
        return ErrorCode.FILE_NOT_FOUND

    if not stat.S_ISREG(file_info.st_mode):
        return ErrorCode.NOT_A_REGULAR_FILE

    return File(
        absolute_path=real_path,
        inode=file_info.st_ino,
        device=file_info.st_dev
    )


def list_folder_files(folder_path: str) -> list[str] | ErrorCode:
    """
    Gets all regular files inside a folder, including subfolders.
    Does not follow symlinks.

    :param folder_path: absolute path of the folder
    :return: sorted list of file paths, or an ErrorCode
    """
    if not os.path.isabs(folder_path):
        return ErrorCode.PATH_NOT_ABSOLUTE

    real_path = os.path.realpath(folder_path)

    if not os.path.exists(real_path):
        return ErrorCode.FILE_NOT_FOUND
    if not os.path.isdir(real_path):
        return ErrorCode.NOT_A_DIRECTORY
    if not os.access(real_path, os.R_OK | os.X_OK):
        return ErrorCode.PERMISSION_DENIED

    files = []

    for root, _, names in os.walk(real_path, followlinks=False):
        for name in names:
            path = os.path.join(root, name)

            try:
                file_info = os.lstat(path)
                if stat.S_ISREG(file_info.st_mode):
                    files.append(path)
            except OSError:
                continue

    return sorted(files)


def _traceable_functions() -> set[str]:
    names = set()
    paths = (
        "/sys/kernel/tracing/available_filter_functions",
        "/sys/kernel/debug/tracing/available_filter_functions"
    )

    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    fields = line.split()
                    names.add(fields[0])
            return names
        except OSError:
            continue

    with open("/proc/kallsyms", "r", encoding="utf-8") as f:
        for line in f:
            fields = line.split()
            if len(fields) >= 3:
                names.add(fields[2])

    return names


def build_bpf_program(functions: tuple[str, ...]) -> str:
    programs = [BPF_PROGRAM_HEADER]

    for name in functions:
        programs.append(BPF_PROBES[name])

    return "".join(programs)


class FileIOProbe:
    """
    Loads the BPF program and provides access to its data.
    Requires BCC, kernel BTF, fentry/fexit support and the right permissions.
    """

    def __init__(self):
        available = _traceable_functions()
        functions = []

        for name in BPF_PROBES:
            if name in available:
                functions.append(name)

        self.functions = tuple(functions)

        missing = []
        for name in REQUIRED_PROBES:
            if name not in self.functions:
                missing.append(name)

        if missing:
            raise RuntimeError(f"required kernel functions not traceable: {missing}")

        if not BPF.support_kfunc():
            raise RuntimeError("kernel does not support fentry/fexit programs")

        self._bpf = BPF(
            text=build_bpf_program(self.functions),
            cflags=[
                "-fms-extensions",
                "-Wno-microsoft-anon-tag",
                f"-DMAX_TRACKED={MAX_TRACKED_FILES}",
                f"-DMAX_STREAMS={MAX_TRACKED_FILE_STREAMS}",
                f"-DMAX_IOVEC={MAX_IOVEC_SEGMENTS}"
            ]
        )

        self._tracked = self._bpf["tracked"]
        self._stats = self._bpf["stats"]
        self._calibration_tid = self._bpf["calibration_tid"]
        self._calibration_key = self._bpf["calibration_key"]

    def kernel_key(self, path: str) -> tuple[int, int, int] | None:
        """
        Gets the file key from the kernel using a zero-byte read.
        This also works when the kernel device number is different from stat().
        The calibration read is not counted in the statistics.

        :param path: path of the file
        :return: device, inode and generation, or None
        """
        zero = ctypes.c_int(0)
        self._calibration_key[zero] = self._calibration_key.Leaf()
        self._calibration_tid[zero] = ctypes.c_uint(threading.get_native_id())

        try:
            fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
            try:
                os.pread(fd, 0, 0)
            finally:
                os.close(fd)
        except OSError:
            return None
        finally:
            self._calibration_tid[zero] = ctypes.c_uint(0)

        key = self._calibration_key[zero]

        if key.dev == 0 and key.ino == 0:
            return None

        return (key.dev, key.ino, key.gen)

    def add(self, slot: int, key: tuple[int, int, int]) -> None:
        self._tracked[self._tracked.Key(*key)] = self._tracked.Leaf(slot)

    def remove(self, key: tuple[int, int, int]) -> None:
        try:
            del self._tracked[self._tracked.Key(*key)]
        except KeyError:
            pass

    def reset(self, slot: int) -> None:
        self._stats[ctypes.c_int(slot)] = self._stats.Leaf()

    def read(self, slot: int) -> FileCounters:
        totals = [0] * len(COUNTER_FIELDS)

        for cpu_value in self._stats[ctypes.c_int(slot)]:
            for i, name in enumerate(COUNTER_FIELDS):
                totals[i] += getattr(cpu_value, name)

        return FileCounters(*totals)

    def close(self) -> None:
        self._bpf.cleanup()
