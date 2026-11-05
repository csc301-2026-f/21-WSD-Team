# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
from time import sleep
import pythoncom
from . import create_backend

if __name__ =="__main__":
    backend = create_backend("debug session")
    backend.start()
    print(backend.get_devices())
    try:
        while True:
            print(backend.get_device_metrics(1))
            print(backend.get_process_metrics(1))
            print(backend.get_file_activity(1))
            print(f"\n\n\n")
            sleep(1)
    finally:
        backend.close()