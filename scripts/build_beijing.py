# -*- coding: utf-8 -*-
"""独立运行北京建筑抓取（避免加载道路缓存消耗内存）。
抓取完成后自动触发完整构建。"""
import subprocess, sys, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)
os.environ["HTTP_PROXY"] = "http://127.0.0.1:65532"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:65532"

log = os.path.join(BASE, "build_cache", "beijing_build.log")
with open(log, "w", encoding="utf-8") as f:
    f.write("Starting beijing build at %s\n" % sys.version + "\n")
    f.flush()
    proc = subprocess.Popen(
        [sys.executable, "-X", "faulthandler", "scripts/build_map.py", "beijing"],
        stdout=f, stderr=subprocess.STDOUT, cwd=BASE,
        env=os.environ
    )
    proc.wait()
    f.write("\nExit code: %d\n" % proc.returncode)
print("Done. Exit code:", proc.returncode)
