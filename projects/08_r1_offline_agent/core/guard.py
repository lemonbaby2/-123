#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线网络护栏 (offline guard)

开启 strict_offline 后, 任何指向非回环地址的 socket 连接都会被拦截,
确保 agent 在断网 / 无 WiFi 环境下不会偷偷外联。本地 Ollama (127.0.0.1)
与 Tailscale 为可选放行项, 由 allow 列表控制。

注意: 仅在 agent 进程内生效, 不改变系统防火墙。用于"内测/上线"前的
离线合规自检。
"""
from __future__ import annotations
import socket

_INSTALLED = False
_STRICT = False
_ALLOW_HOSTS = {"127.0.0.1", "::1", "localhost"}


def is_loopback(host: str) -> bool:
    if host in _ALLOW_HOSTS:
        return True
    try:
        info = socket.getaddrinfo(host, None)
        for res in info:
            ip = res[4][0]
            if ip == "127.0.0.1" or ip == "::1" or ip.startswith("127."):
                return True
    except Exception:
        pass
    return False


def _patched_connect(orig_connect):
    def connect(self, address):
        if isinstance(address, tuple) and len(address) >= 2:
            host = address[0]
            if _STRICT and not is_loopback(host):
                raise PermissionError(
                    "[offline-guard] 拒绝外部连接 %s (strict_offline=True)" % host)
        return orig_connect(self, address)
    return connect


def install(strict: bool = True, allow_tailscale: bool = False):
    global _INSTALLED, _STRICT
    _STRICT = strict
    if allow_tailscale:
        # 100.x.x.x 为 Tailscale 网段, 若需本地多机协同可放行
        _ALLOW_HOSTS.update({"100.%d.%d.%d" % (a, b, c)
                             for a in (100,) for b in range(0, 128) for c in range(0, 256)})
    if not _INSTALLED:
        socket.socket.connect = _patched_connect(socket.socket.connect)
        _INSTALLED = True


def set_strict(v: bool):
    global _STRICT
    _STRICT = v


def status():
    return {"installed": _INSTALLED, "strict": _STRICT, "allow": sorted(_ALLOW_HOSTS)[:8]}
