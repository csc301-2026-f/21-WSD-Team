# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
from time import sleep

from . import create_backend

if __name__ =="__main__":
    backend = create_backend("debug session")
    backend.start()
    print(backend.get_devices())
    try:
        while True:
            print(backend.get_device_metrics(1))
            sleep(1)
    finally:
        backend.close()
    