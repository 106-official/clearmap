# -*- coding: utf-8 -*-
"""ClearMap 入口：一键启动。用法：  python app.py  [端口]"""

import sys

import server


def main():
    port = None
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    server.serve(port=port)


if __name__ == "__main__":
    main()