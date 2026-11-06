"""Pengganti Topaz untuk tes tanpa GPU. Dipanggil sebagai subprocess oleh topaz.py.

Usage: python -m app.fake_topaz <input> <output> <delay_sec>
Hanya menyalin file setelah menunggu delay.
"""

import shutil
import sys
import time


def main():
    src, dst, delay = sys.argv[1], sys.argv[2], float(sys.argv[3])
    time.sleep(delay)
    shutil.copyfile(src, dst)


if __name__ == "__main__":
    main()
