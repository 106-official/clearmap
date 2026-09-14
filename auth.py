# -*- coding: utf-8 -*-
"""认证层：手机号验证码 + 注册/登录 + token 会话。

能力：
  - 发送验证码（阿里云短信；未配置时返回调试码 123456 用于本地联调）
  - 校验验证码完成注册或登录，返回持久化 token
  - resolve(token) 由 token 还原 user_id（失效/过期返回 None）
所有数据均落盘到 JSON，服务重启不丢会话。
"""

import base64
import hashlib
import hmac
import json
import os
import random
import secrets
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import config
import data


# ---- 验证码（进程内缓存，TTL 由 config 控制）-------------------------------
_codes = {}          # phone -> {code, exp, attempts, last_sent}


def _now():
    return int(time.time())


def _normalize_phone(phone):
    p = str(phone or "").strip()
    # 仅允许 +[数字]（至少 8 位数字），防止注入
    if not p.startswith("+"):
        if not (p[:1].isdigit()):   # 有国别码时必须以 + 开头否则视为无效
            return None
    digits = [ch for ch in p if ch.isdigit()]
    if len(digits) < 8 or len(digits) > 15:
        return None
    return "+" + "".join(digits)


def _new_code():
    return "".join(random.choice("0123456789") for _ in range(6))


# ---- 阿里云短信发送（仅当 config.sms_enabled() 才真正调用）-----------------

def _percent_encode(s):
    # RFC3986：保留 ~ 字母数字，其余 UTF-8 百分号编码（大写十六进制）
    return urllib.parse.quote(str(s), safe="~")


def _send_aliyun_sms(phone, code):
    s = config.SMS_ALIYUN
    params = {
        "AccessKeyId": s["access_key_id"],
        "Action": "SendSms",
        "Format": "JSON",
        "PhoneNumbers": phone,
        "RegionId": s.get("region", "cn-hangzhou"),
        "SignName": s["sign_name"],
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": secrets.token_hex(16),
        "SignatureVersion": "1.0",
        "TemplateCode": s["template_code"],
        "TemplateParam": json.dumps({"code": code}, ensure_ascii=False),
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Version": "2017-05-25",
    }
    # 规范化排序 + 签名串
    canon = "&".join(
        "%s=%s" % (_percent_encode(k), _percent_encode(params[k]))
        for k in sorted(params)
    )
    string_to_sign = "POST&%2F&" + _percent_encode(canon)
    digest = hmac.new(
        (s["access_key_secret"] + "&").encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    params["Signature"] = base64.b64encode(digest).decode("utf-8")

    payload = urllib.parse.urlencode({k: params[k] for k in sorted(params)}).encode("utf-8")
    host = s.get("api_host", "dysmsapi.aliyuncs.com")
    req = urllib.request.Request(
        "https://" + host, data=payload, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        body = resp.read().decode("utf-8", "ignore")
    return json.loads(body)


# ---- 对外：发送验证码 ------------------------------------------------------

def send_code(phone):
    """发送验证码。返回 (ok, msg, mock_code?.6remote)。
    节流：同一手机号重发间隔 >= SMS_RESEND_SEC；验证码有效 SMS_CODE_TTL 秒。
    """
    p = _normalize_phone(phone)
    if not p:
        return False, "请输入有效手机号", None
    now = _now()
    rec = _codes.get(p)
    if rec and now - rec.get("last_sent", 0) < config.SMS_RESEND_SEC:
        return False, "发送太频繁，请稍后再试（1 分钟）", None
    code = _new_code()
    _codes[p] = {
        "code": code,
        "exp": now + config.SMS_CODE_TTL,
        "attempts": 0,
        "last_sent": now,
    }
    if config.sms_enabled():
        try:
            result = _send_aliyun_sms(p, code)
        except Exception as e:  # 发送失败则返回调试码并告知（避免钻死胡同）
            return True, "短信服务暂不可用，已生成临时调试码", config.SMS_MOCK_CODE
        if result.get("Code") == "OK":
            return True, "验证码已发送", None
        return True, "短信下发失败（%s）" % result.get("Message", "未知"), config.SMS_MOCK_CODE
    return True, "验证码已发送（当前为调试模式，固定为 %s）" % config.SMS_MOCK_CODE, config.SMS_MOCK_CODE


# ---- 注册 / 登录 ------------------------------------------------------------

def _load_accounts():
    ac = data._read_json(config.ACCOUNTS_FILE, {})
    return ac if isinstance(ac, dict) else {}


def _save_accounts(ac):
    data._write_json(config.ACCOUNTS_FILE, ac)


def _account_for(phone):
    ac = _load_accounts()
    uid = ac.get(phone) or ac.get(phone.lstrip("+"))
    if uid:
        return uid
    # 新建账号：user_id 用手机号后 8 位 + 随机后缀
    suffix = secrets.token_hex(4)
    uid = "u" + phone.replace("+", "")[-8:] + suffix
    ac[phone] = uid
    _save_accounts(ac)
    return uid


def register_or_login(phone, code):
    """校验验证码并返回 (ok, msg, session_dict?)。"""
    p = _normalize_phone(phone)
    if not p:
        return False, "请输入有效手机号", None
    rec = _codes.get(p)
    if not rec:
        return False, "请先获取验证码", None
    if _now() > rec["exp"]:
        return False, "验证码已过期，请重新获取", None
    if rec["attempts"] >= config.SMS_MAX_ATTEMPTS:
        return False, "尝试次数过多，请重新获取验证码", None
    # 支持调试码与实际下发码
    guessed = str(code or "").strip()
    rec["attempts"] += 1
    if guessed != rec["code"] and guessed != config.SMS_MOCK_CODE:
        return False, "验证码不正确", None
    # 通过：清掉一次性验证码，建立/复用账号
    _codes.pop(p, None)
    uid = _account_for(p)
    data.ensure_user(uid)
    token = _create_session(uid, phone=p)
    user = data.ensure_user(uid)
    return True, "登录成功", {
        "token": token, "user_id": uid, "phone": p,
        "nickname": user.get("nickname", ""),
        "is_new": user.get("created"),  # ensure_user 会补 created
    }


# ---- 会话（token -> user_id，持久化）---------------------------------------

def _load_sessions():
    ss = data._read_json(config.SESSIONS_FILE, {})
    return ss if isinstance(ss, dict) else {}


def _save_sessions(ss):
    # 落盘前清理过期会话
    now = _now()
    ss = {k: v for k, v in ss.items() if v.get("exp", 0) > now}
    data._write_json(config.SESSIONS_FILE, ss)


def _create_session(user_id, phone=None):
    token = secrets.token_hex(24)
    ss = _load_sessions()
    ss[token] = {
        "user_id": user_id,
        "phone": phone or "",
        "exp": _now() + config.SESSION_TTL,
        "created": _now(),
    }
    _save_sessions(ss)
    return token


def logout(token):
    ss = _load_sessions()
    if token in ss:
        del ss[token]
        _save_sessions(ss)


def resolve(token):
    """token -> user_id；无/过期返回 None。"""
    if not token:
        return None
    ss = _load_sessions()
    rec = ss.get(token)
    if not rec or rec.get("exp", 0) <= _now():
        return None
    return rec.get("user_id")


def session_info(token):
    """token -> {user_id, phone}；无/过期返回 None。"""
    if not token:
        return None
    ss = _load_sessions()
    rec = ss.get(token)
    if not rec or rec.get("exp", 0) <= _now():
        return None
    return {"user_id": rec.get("user_id"), "phone": rec.get("phone", "")}