# -*- coding: utf-8 -*-
"""云同步层：把用户数据推送到/拉取自阿里云服务器。

仅当 config 中配置了 CLOUD_SYNC_URL + CLOUD_SYNC_KEY 时生效；
否则所有操作静默跳过（本地模式），不影响任何现有功能。

远端约定：
  GET  <url>?token=<KEY>&user_id=<id>  拉取该用户数据，命中返回该用户 JSON，未命中 404/空
  POST <url>?token=<KEY>               推送 {user_id, user}，返回 {"ok": true}
同步采用“尽力而为”：网络异常不抛错、不阻塞主流程。
"""

import json
import time
import urllib.error
import urllib.request
import urllib.parse

import config


def enabled():
    return config.cloud_sync_enabled()


def push(user_id, user):
    """把某个用户的完整数据推送到云端（尽力而为）。"""
    if not enabled():
        return False
    url = config.CLOUD_SYNC_URL
    sep = "&" if "?" in url else "?"
    full = url + sep + "token=" + urllib.parse.quote(config.CLOUD_SYNC_KEY)
    payload = json.dumps({"user_id": user_id, "user": user, "ts": int(time.time())},
                         ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(full, data=payload, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8", "ignore"))
        return bool(body.get("ok"))
    except (urllib.error.URLError, ValueError, OSError):
        return False


def pull(user_id):
    """从云端拉取该用户数据；未命中或失败返回 None。"""
    if not enabled():
        return None
    url = config.CLOUD_SYNC_URL
    sep = "&" if "?" in url else "?"
    full = url + sep + "token=" + urllib.parse.quote(config.CLOUD_SYNC_KEY) + \
        "&user_id=" + urllib.parse.quote(str(user_id))
    try:
        with urllib.request.urlopen(full, timeout=5) as resp:
            if resp.status != 200:
                return None
            body = json.loads(resp.read().decode("utf-8", "ignore"))
    except (urllib.error.URLError, ValueError, OSError):
        return None
    # 允许两种载荷结构：{"user": {...}} 或直接该用户对象 /200 空
    if isinstance(body, dict):
        if isinstance(body.get("user"), dict):
            return body["user"]
        if isinstance(body.get("data"), dict) and isinstance(body["data"].get("user"), dict):
            return body["data"]["user"]
    return None