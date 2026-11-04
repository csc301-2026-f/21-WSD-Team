"""
chat gpt generated test file, creates a file. 
runs File IO operations, then deletes it
"""

import os
import time
import argparse
from pathlib import Path

def generate_file_io(directory: str, duration: int = 30):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    filepath = directory / "etw_fileio_test.bin"
    chunk_size = 4096
    data = os.urandom(chunk_size)

    print(f"Generating FileIO activity at: {filepath}")
    print(f"Duration: {duration} seconds")
    print("Press Ctrl+C to stop.\n")

    start = time.monotonic()
    operations = 0

    try:
        with open(filepath, "w+b") as f:
            while time.monotonic() - start < duration:
                # Write
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
                operations += 1

                # Read
                f.seek(0)
                f.read(chunk_size)
                operations += 1

                # Move to another offset
                f.seek(0, os.SEEK_END)

                time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nStopped by user.")

    finally:
        try:
            filepath.unlink(missing_ok=True)
        except OSError as e:
            print(f"Could not delete test file: {e}")

    print(f"Completed approximately {operations} file operations.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate Windows FileIO activity for ETW testing."
    )

    parser.add_argument(
        "--directory",
        default=str(Path.home() / "ETWTest"),
        help="Directory in which to generate file activity."
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Duration in seconds."
    )

    args = parser.parse_args()

    generate_file_io(args.directory, args.duration)