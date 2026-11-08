"""Pengganti After Effects untuk tes di Mac. Dipanggil sebagai subprocess oleh ae.py.

Usage: python -m app.fake_ae <input> <output> <delay_sec>
Menyalin file setelah delay. FAKE_AE_FAIL=1 membuat tahap ini gagal (untuk tes antrian).
"""

import os
import shutil
import sys
import time


def main():
    src, dst, delay = sys.argv[1], sys.argv[2], float(sys.argv[3])
    time.sleep(delay)
    if os.environ.get("FAKE_AE_FAIL") == "1":
        print("FAKE_AE_FAIL=1: dipaksa gagal", file=sys.stderr)
        sys.exit(1)
    shutil.copyfile(src, dst)


if __name__ == "__main__":
    main()
