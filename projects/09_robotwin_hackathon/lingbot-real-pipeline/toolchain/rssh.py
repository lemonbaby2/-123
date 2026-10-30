"""SSH/SFTP 助手：直连 SOCKS5 代理（<PROXY_USER>/<PROXY_PASSWORD>），不依赖 Proxifier。
用法:
    from rssh import connect
    cli = connect()
    out = run(cli, "uptime")
"""
import socket as _socket
import socks
import paramiko

PROXY = ("<PROXY_HOST>", 5502)
PROXY_AUTH = ("<PROXY_USER>", "<PROXY_PASSWORD>")
ROBOT = ("<ROBOT_HOST>", 22)
USER, PWD = "<ROBOT_USER>", "<ROBOT_PASSWORD>"

_orig_socket = _socket.socket


def connect(timeout=25):
    socks.set_default_proxy(socks.SOCKS5, PROXY[0], PROXY[1],
                            username=PROXY_AUTH[0], password=PROXY_AUTH[1])
    _socket.socket = socks.socksocket
    try:
        cli = paramiko.SSHClient()
        cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        cli.connect(ROBOT[0], ROBOT[1], USER, PWD, timeout=timeout,
                    allow_agent=False, look_for_keys=False, banner_timeout=timeout)
        return cli
    finally:
        _socket.socket = _orig_socket


def run(cli, cmd, t=90):
    si, so, se = cli.exec_command(cmd, timeout=t)
    out = so.read().decode(errors="replace")
    err = se.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


def upload(cli, local, remote):
    socks.set_default_proxy(socks.SOCKS5, PROXY[0], PROXY[1],
                            username=PROXY_AUTH[0], password=PROXY_AUTH[1])
    _socket.socket = socks.socksocket
    try:
        sftp = cli.open_sftp()
        sftp.put(local, remote)
        sftp.close()
        return True
    finally:
        _socket.socket = _orig_socket


if __name__ == "__main__":
    cli = connect()
    print(run(cli, "echo SSH_OK && uptime && df -h /home | tail -1"))
    cli.close()
