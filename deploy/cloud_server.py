# -*- coding: utf-8 -*-
"""阿里云云同步服务端 —— 部署到你的阿里云 ECS / 任意主机。

作用：接收 ClearMap 本机推送的个人信息并存储到云端，也支持按 user_id 拉回。
纯标准库实现，零第三方依赖，直接 `python cloud_server.py` 即可运行。

约定的协议（与本机 cloud.py / config.CLOUD_SYNC_URL 一致）：
  GET  ?token=<KEY>&user_id=<id>         拉取对应用户数据；未命中返回 404
  POST ?token=<KEY>  body={user_id,user}  推送/覆盖该用户数据，返回 {"ok":true}

安全要点：
  * 所有请求必须带 token=<KEY>，KEY 与网络应用（config.CLOUD_SYNC_KEY）一致；
    密钥不符一律 403。
  * 生产建议放到 HTTPS 反向代理（如 Nginx + 阿里云公网证书）后面，
    或使用阿里云 API 网关做鉴权，避免明文传输。
"""

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "cloud_users")   # 云端用户数据目录
ACCESS_KEY = os.environ.get("CLEARMAP_CLOUD_KEY", "CHANGE_ME_STRONG_SECRET")

os.makedirs(DATA_DIR, exist_ok=True)


def _user_path(user_id):
    u = str(user_id or "guest")
    safe = "".join(ch for ch in u if ch.isalnum() or ch in "_-") or "guest"
    return os.path.join(DATA_DIR, safe + ".json")


def _write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError, OSError):
        return None


class SyncHandler(BaseHTTPRequestHandler):
    server_version = "ClearMapCloud/1.0"

    def _send_json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _auth(self, q):
        """校验 token；返回 True/False。"""
        return q.get("token", [""])[0] == ACCESS_KEY and ACCESS_KEY != "CHANGE_ME_STRONG_SECRET"

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length) if length else b""

    def do_GET(self):
        parsed = urlparse(self.path)
        q = parse_qs(parsed.query)
        if not self._auth(q):
            self._send_json(403, {"ok": False, "error": "unauthorized"})
            return
        uid = q.get("user_id", [""])[0]
        if not uid:
            self._send_json(400, {"ok": False, "error": "missing user_id"})
            return
        user = _read_json(_user_path(uid))
        if user is None:
            self._send_json(404, {"ok": False, "error": "not found"})
            return
        self._send_json(200, {"ok": True, "user_id": uid, "user": user})

    def do_POST(self):
        parsed = urlparse(self.path)
        q = parse_qs(parsed.query)
        if not self._auth(q):
            self._send_json(403, {"ok": False, "error": "unauthorized"})
            return
        try:
            body = json.loads(self._read_body().decode("utf-8", "ignore"))
        except ValueError:
            self._send_json(400, {"ok": False, "error": "bad json"})
            return
        uid, user = body.get("user_id"), body.get("user")
        if not uid or not isinstance(user, dict):
            self._send_json(400, {"ok": False, "error": "missing user_id/user"})
            return
        user = dict(user)
        user.setdefault("cloud_synced_at", int(time.time()))
        _write_json(_user_path(uid), user)
        self._send_json(200, {"ok": True, "user_id": uid, "synced": user.get("cloud_synced_at")})

    def log_message(self, *args):  # 精简日志
        print("[sync] %s %s" % (self.command, self.path))


def main():
    port = int(os.environ.get("PORT", 9099))
    httpd = ThreadingHTTPServer(("0.0.0.0", port), SyncHandler)
    print("ClearMap 云同步已启动 → 0.0.0.0:%d（数据目录 %s）" % (port, DATA_DIR))
    print("KEY 校验：%s" % ("OK" if ACCESS_KEY != "CHANGE_ME_STRONG_SECRET" else "请先设置 CLEARMAP_CLOUD_KEY!"))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()