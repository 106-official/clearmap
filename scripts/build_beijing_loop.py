# -*- coding: utf-8 -*-
"""循环运行 build_map.py beijing：崩溃后自动重启，利用缓存断点续传。
每次运行缓存若干建筑分块，多次循环后最终完成。
"""
import subprocess, sys, os, time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_SCRIPT = os.path.join(BASE, "scripts", "build_map.py")
CACHE_DIR = os.path.join(BASE, "build_cache")
LOG_FILE = os.path.join(CACHE_DIR, "beijing_loop.log")

MAX_ROUNDS = 40  # 最多循环 40 轮

def count_tiles():
    """统计已缓存的建筑分块数。"""
    d = os.path.join(CACHE_DIR)
    if not os.path.exists(d):
        return 0
    return len([f for f in os.listdir(d) if f.startswith("bld_beijing_") and f.endswith(".json")])

if __name__ == "__main__":
    for rnd in range(1, MAX_ROUNDS + 1):
        tiles = count_tiles()
        ts = time.strftime("%H:%M:%S")
        msg = "[%(ts)s] 第 %(rnd)d 轮 | 已缓存 %(tiles)d/195 块" % {"ts": ts, "rnd": rnd, "tiles": tiles}
        print(msg, flush=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

        # 检查是否已有 beijing_buildings 合并缓存 → 表示已完成
        merged = os.path.join(CACHE_DIR, "beijing_buildings.json")
        if os.path.exists(merged):
            done_msg = "[%(ts)s] 建筑合并缓存已存在，构建完成！" % {"ts": ts}
            print(done_msg, flush=True)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(done_msg + "\n")
            break

        # 运行 build_map.py beijing
        try:
            proc = subprocess.run(
                [sys.executable, "-u", BUILD_SCRIPT, "beijing"],
                cwd=BASE,
                timeout=300,  # 每轮最多 5 分钟，超时自动杀掉重启
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            # 记录输出
            outline = proc.stdout[-2000:] if proc.stdout else ""
            errline = proc.stderr[-1000:] if proc.stderr else ""
            log_chunk = "  exit=%d\n  stdout_tail:\n%s\n  stderr_tail:\n%s\n" % (proc.returncode, outline, errline)
            print(log_chunk, flush=True)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(log_chunk + "\n")
        except subprocess.TimeoutExpired:
            timeout_msg = "  [超时] 5 分钟到期，重启下一轮"
            print(timeout_msg, flush=True)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(timeout_msg + "\n")
        except Exception as ex:
            err_msg = "  [异常] %s" % ex
            print(err_msg, flush=True)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(err_msg + "\n")

        # 轮间停 3 秒避免连续请求
        time.sleep(3)

    # 最终汇报
    tiles = count_tiles()
    ts = time.strftime("%H:%M:%S")
    final = "[%(ts)s] 循环结束 | 最终缓存 %(tiles)d/195 块" % {"ts": ts, "tiles": tiles}
    print(final, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(final + "\n")
