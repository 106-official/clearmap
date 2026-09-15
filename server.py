# -*- coding: utf-8 -*-
"""HTTP 服务层：路由分发 + 静态资源服务。

使用标准库 http.server，零第三方依赖。
API 请求转发给 api.route；静态文件从 static/ 目录读取。
"""

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import config
import api


def content_type(path):
    ct, _ = mimetypes.guess_type(path)
    return ct or "application/octet-stream"


class ClearMapHandler(BaseHTTPRequestHandler):
    server_version = "ClearMap/1.0"

    # ---- 输出工具 ----
    def _cors(self):
        # 允许 WebView/浏览器跨域调用 API（打包 App 页面源为本地、后端在远端）
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "86400")

    def _send_json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, rel):
        # 保护：只允许 static 目录内；rel 为站内相对路径（不含前导 /）
        base = os.path.realpath(config.STATIC_DIR)
        target = os.path.realpath(os.path.join(base, rel))
        if base != os.path.commonpath([base, target]) or not os.path.isfile(target):
            self._send_json(404, {"ok": False, "error": "资源不存在"})
            return
        with open(target, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type(target))
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    # 预检请求：浏览器在跨域 POST(application/json) 前会先发 OPTIONS
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self._cors()
        self.end_headers()

    # ---- 生命周期 ----
    def _read_body(self):
        length = self.headers.get("Content-Length")
        if not length:
            return b""
        return self.rfile.read(int(length))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/media":
            # 二进制图片：由 api.media 返回 (code, payload, content_type)
            from urllib.parse import parse_qs
            q = parse_qs(parsed.query)
            user = (q.get("user", ["guest"])[0]) or "guest"
            fname = q.get("file", [""])[0]
            code, payload, ctype = api.media(user, fname)
            if ctype:
                self._send_bytes(code, ctype, payload)
            else:
                self._send_json(code, payload)
            return
        if path.startswith("/api/"):
            code, payload = api.route("GET", path, query=parsed.query)
            self._send_json(code, payload)
            return
        rel = (path if path != "/" else "/index.html").lstrip("/")
        if path.startswith("/data/"):
            self._send_json(403, {"ok": False, "error": "禁止访问"})
            return
        self._send_static(rel)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if not path.startswith("/api/"):
            self._send_json(404, {"ok": False, "error": "接口不存在"})
            return
        body = self._read_body()
        code, payload = api.route("POST", path, body_raw=body, query=parsed.query)
        self._send_json(code, payload)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if not path.startswith("/api/"):
            self._send_json(404, {"ok": False, "error": "接口不存在"})
            return
        code, payload = api.route("DELETE", path, query=parsed.query)
        self._send_json(code, payload)

    def log_message(self, *args):  # 精简控制台输出
        pass


def serve(host=None, port=None):
    host = host or os.environ.get("CLEARMAP_HOST") or config.HOST
    port = port or int(os.environ.get("CLEARMAP_PORT") or config.PORT)
    httpd = ThreadingHTTPServer((host, port), ClearMapHandler)
    print(f"ClearMap 已启动 →  http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    serve()