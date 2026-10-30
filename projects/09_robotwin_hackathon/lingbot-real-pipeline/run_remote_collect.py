# -*- coding: utf-8 -*-
"""远程批量采集驱动器（在 Windows 本机跑，通过 SSH 指挥 <ROBOT_USER> 采集）

背景：
  机械臂 + 双相机都接在 <ROBOT_USER>（<ROBOT_HOST>，需先连图灵智新 VPN / Proxifier）。
  5070 那台机器只负责训练，和采集完全隔离 —— 本脚本不会碰它。

用法（本机）:
  python run_remote_collect.py check                     # 只探活（VPN/SSH/arm/cam）
  python run_remote_collect.py plan --per 50             # 上传脚本 + 打印采集计划
  python run_remote_collect.py start --per 50            # 后台上传并开跑（无人值守）
  python run_remote_collect.py status                    # 看进度（尾随日志 + 条数统计）
  python run_remote_collect.py pull                      # 把 episodes 打包拉回本机
  python run_remote_collect.py stop                      # 安全停止（SIGINT，会保存当前条）

  --tasks pick_place,push,stack,sweep,drawer,joint
  --per 50           每任务条数
  --minutes 180      跑满 N 分钟自动停
  --host / --user / --pass 覆盖默认 <ROBOT_HOST> / <ROBOT_USER> / <ROBOT_PASSWORD>
"""
import os
import sys
import time
import socket
import struct
import argparse
import posixpath

HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL_TC = os.path.join(os.path.dirname(HERE), "toolchain")   # 本机 toolchain 目录
REMOTE_TC = "/home/<ROBOT_USER>/lingbot_real"                        # <ROBOT_USER> 上的工作目录

HOST, USER, PWD = "<ROBOT_HOST>", "<ROBOT_USER>", "<ROBOT_PASSWORD>"

NEED_FILES = ["arm.py", "cams.py", "record.py", "collect.py", "build_dataset.py",
              "collect_batch.py"]


# ============================ SOCKS5（不依赖 Proxifier 进程规则）============================
def socks5_connect(proxy: str, dst_host: str, dst_port: int,
                   timeout: float = 15.0, user: str = "", pw: str = ""):
    """通过 SOCKS5 代理建立到 dst 的 TCP 连接，返回已连通的 socket。

    只实现 RFC1928 必需部分（CONNECT + 可选用户名密码认证）。
    为什么自己写：Proxifier 是按进程名做规则匹配的，python.exe/ssh.exe 漏加规则
    就会直连超时；直接走代理端口最稳，也方便在脚本里换机器。
    """
    ph, _, pp = proxy.partition(":")
    pp = int(pp or 1080)
    s = socket.create_connection((ph, pp), timeout)
    s.settimeout(timeout)

    # 1) 问候：声明支持 无认证 / 用户名密码
    methods = b"\x00\x02" if (user or pw) else b"\x00"
    s.sendall(b"\x05" + bytes([len(methods)]) + methods)
    rep = s.recv(2)
    if len(rep) < 2 or rep[0] != 5:
        raise OSError("不是 SOCKS5 服务")
    if rep[1] == 0xFF:
        raise OSError("SOCKS5 拒绝：无可接受认证方式")
    if rep[1] == 0x02:
        u, p = user.encode(), pw.encode()
        s.sendall(b"\x01" + bytes([len(u)]) + u + bytes([len(p)]) + p)
        r = s.recv(2)
        if len(r) < 2 or r[1] != 0:
            raise OSError("SOCKS5 用户名/密码认证失败")

    # 2) CONNECT
    try:
        ip = socket.inet_aton(dst_host)
        addr = b"\x01" + ip
    except OSError:
        h = dst_host.encode()
        addr = b"\x03" + bytes([len(h)]) + h
    s.sendall(b"\x05\x01\x00" + addr + struct.pack(">H", dst_port))
    r = s.recv(4)
    if len(r) < 4 or r[1] != 0:
        code = r[1] if len(r) > 1 else -1
        raise OSError(f"SOCKS5 CONNECT 失败 code={code}")
    # 吃掉 BND.ADDR/BND.PORT
    atyp = r[3]
    if atyp == 0x01:
        s.recv(4 + 2)
    elif atyp == 0x03:
        n = s.recv(1)[0]
        s.recv(n + 2)
    elif atyp == 0x04:
        s.recv(16 + 2)
    return s


def _detect_local_socks(timeout=1.5):
    """自动发现本机 SOCKS5 代理（TuringLink 默认监听 127.0.0.1:1080）。

    有 TuringLink 在跑就不需要再传 --proxy，直接用它。
    这里只做最小握手探测，不认证、不留连接。
    """
    for port in (1080, 1081, 7891, 10808):
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout)
            s.settimeout(timeout)
            s.sendall(b"\x05\x01\x00")
            rep = s.recv(2)
            s.close()
            if len(rep) == 2 and rep[0] == 5 and rep[1] in (0x00, 0x02):
                return f"127.0.0.1:{port}"
        except Exception:
            continue
    return ""


def connect(args, quiet=False):
    import paramiko
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    sock = None
    proxy = args.proxy
    if not proxy:
        auto = _detect_local_socks()
        if auto:
            proxy = auto
            if not quiet:
                print(f"[socks] 自动发现本机代理 {proxy}（TuringLink 在跑）")
    if proxy:
        if not quiet:
            print(f"[socks] 经 {proxy} 建隧道 -> {args.host}:22 ...")
        sock = socks5_connect(proxy, args.host, 22,
                              user=args.proxy_user, pw=args.proxy_pass)
        if not quiet:
            print("[socks] 隧道 OK")
    if not quiet:
        print(f"[ssh ] 连接 {args.user}@{args.host} ...")
    cli.connect(args.host, 22, args.user, args.password,
                timeout=15, allow_agent=False, look_for_keys=False, sock=sock)
    if not quiet:
        print("[ssh ] OK")
    return cli


def run(cli, cmd, timeout=60, quiet=False):
    si, so, se = cli.exec_command(cmd, timeout=timeout)
    out = so.read().decode(errors="replace")
    err = se.read().decode(errors="replace")
    rc = so.channel.recv_exit_status()
    if not quiet:
        if out.strip():
            sys.stdout.write(out if out.endswith("\n") else out + "\n")
        if err.strip():
            sys.stdout.write("[stderr] " + err.replace("\n", "\n[stderr] ") + "\n")
    return rc, out, err


# ============================ 各子命令 ============================
def cmd_check(args):
    """只探活，不传文件、不动机器人"""
    print("=" * 62)
    print("  1) SSH 到 <ROBOT_USER>")
    print("=" * 62)
    try:
        cli = connect(args)
    except Exception as e:
        print(f"[FATAL] SSH 连不上: {type(e).__name__}: {e}")
        print()
        print("  排查顺序：")
        print("    a) 图灵智新 VPN 客户端在线并登录？(托盘图标)")
        print(f"    b) 本机 -> {args.host} 是否通： ping {args.host}")
        print("    c) 有本地 SOCKS5 端口就直接走它，绕开 Proxifier 进程规则：")
        print("         python run_remote_collect.py check --proxy 127.0.0.1:1080")
        print("    d) 机器人侧 sshd 是否启动（现场看指示灯 / 电源）")
        return 3

    print("\n" + "=" * 62)
    print("  2) 机器人侧环境")
    print("=" * 62)
    run(cli, f"echo host=$(hostname); uptime | head -1; "
             f"df -h {REMOTE_TC} 2>/dev/null | tail -1; "
             f"python3 -V; ls {REMOTE_TC} 2>/dev/null | head -20")

    print("\n" + "=" * 62)
    print("  3) 机械臂 TCP 8080")
    print("=" * 62)
    run(cli, "timeout 5 python3 -c \"import socket;s=socket.create_connection(('<ARM_HOST>',8080),4);"
             "s.sendall(b'{\\\"command\\\":\\\"get_current_arm_state\\\"}\\n');"
             "import time;time.sleep(0.5);print(s.recv(4096)[:200])\" 2>&1 | tail -3")

    print("\n" + "=" * 62)
    print("  4) 相机节点")
    print("=" * 62)
    run(cli, "ls /dev/video* 2>/dev/null | tr '\\n' ' '; echo; "
             "ls /home/<ROBOT_USER>/lingbot_real/episodes 2>/dev/null | wc -l | xargs echo '已有 episode 目录数:'")
    cli.close()
    print("\n[结论] 若上面三段都正常，可执行: python run_remote_collect.py start --per 50")
    return 0


def upload_toolchain(cli, args):
    """只补传缺失或有变化的文件（按大小+mtime 粗判）"""
    import paramiko
    sftp = cli.open_sftp()
    run(cli, f"mkdir -p {REMOTE_TC}", quiet=True)
    for name in NEED_FILES:
        local = os.path.join(LOCAL_TC, name)
        if not os.path.exists(local):
            print(f"  [skip] 本机缺失 {name}")
            continue
        remote = posixpath.join(REMOTE_TC, name)
        lsz = os.path.getsize(local)
        try:
            rsz = sftp.stat(remote).st_size
        except IOError:
            rsz = -1
        if lsz == rsz:
            print(f"  [same] {name}")
            continue
        sftp.put(local, remote)
        print(f"  [put ] {name}  {lsz / 1024:.1f} KB")
    sftp.close()


def cmd_plan(args):
    cli = connect(args)
    print("\n[上传] 工具链 -> " + REMOTE_TC)
    upload_toolchain(cli, args)
    print("\n[计划] 机器人侧 collect_batch.py --plan")
    run(cli, f"cd {REMOTE_TC} && python3 collect_batch.py --plan "
             f"--tasks {args.tasks} --episodes-per-task {args.per}")
    cli.close()
    return 0


def cmd_start(args):
    cli = connect(args)

    print("\n[1/3] 上传工具链")
    upload_toolchain(cli, args)

    print("\n[2/3] 预检（臂 + 相机）")
    rc, out, err = run(cli, f"cd {REMOTE_TC} && timeout 90 python3 collect_batch.py --probe "
                            f"--tasks {args.tasks} --episodes-per-task {args.per} 2>&1 | tail -25")
    if "FATAL" in out or rc != 0:
        print("\n[中止] 预检未通过，未开始采集。上面日志里找 [FATAL] / FAIL 关键字。")
        cli.close()
        return 4

    print("\n[3/3] 后台启动（nohup，断开 SSH 也继续跑）")
    stamp = time.strftime("%Y%m%d_%H%M%S")
    logf = f"{REMOTE_TC}/episodes/_run_{stamp}.log"
    cmd = (f"cd {REMOTE_TC} && mkdir -p episodes && "
           f"nohup python3 -u collect_batch.py "
           f"--tasks {args.tasks} --episodes-per-task {args.per} "
           f"--max-minutes {args.minutes} --resume "
           f"> {logf} 2>&1 & echo PID=$!")
    rc, out, err = run(cli, cmd)
    print(out.strip())
    print(f"\n日志: {logf}")
    print(f"\n查看进度: python run_remote_collect.py status")
    print(f"拉回数据: python run_remote_collect.py pull")
    cli.close()
    return 0


def cmd_status(args):
    cli = connect(args)
    run(cli, f"cd {REMOTE_TC} && "
             f"echo '--- 进程 ---'; pgrep -af collect_batch.py | head -3; "
             f"echo '--- 条数 ---'; "
             f"test -f episodes/manifest.jsonl && wc -l < episodes/manifest.jsonl || echo 0; "
             f"echo '--- 各任务 ---'; "
             f"test -f episodes/manifest.jsonl && python3 -c \""
             f"import json,collections;"
             f"r=[json.loads(l) for l in open('episodes/manifest.jsonl') if l.strip()];"
             f"c=collections.Counter((x['task'],x['ok']) for x in r);"
             f"print('\\n'.join(f'  {{k[0]}} ok={{k[1]}} {{v}}' for k,v in c.items()));"
             f"print('  总帧数', sum(x['frames'] for x in r))\" 2>/dev/null; "
             f"echo '--- 磁盘 ---'; du -sh episodes 2>/dev/null; "
             f"echo '--- 最新日志 ---'; "
             f"tail -25 $(ls -t episodes/_run_*.log episodes/_batch.log 2>/dev/null | head -1) 2>/dev/null")
    cli.close()
    return 0


def cmd_stop(args):
    cli = connect(args)
    print("[stop] 发送 SIGINT（触发保存当前 episode + 回 home）")
    run(cli, "pkill -INT -f collect_batch.py; sleep 8; pgrep -af collect_batch.py || echo '已退出'")
    run(cli, f"cd {REMOTE_TC} && tail -12 $(ls -t episodes/_run_*.log 2>/dev/null | head -1) 2>/dev/null")
    cli.close()
    return 0


def cmd_pull(args):
    import tarfile
    cli = connect(args)
    outdir = os.path.join(os.path.dirname(HERE), "episodes_pull")
    os.makedirs(outdir, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    remote_tgz = f"/tmp/episodes_{stamp}.tgz"
    print(f"[pack] 机器人侧打包 episodes + manifest ...")
    rc, out, _ = run(cli, f"cd {REMOTE_TC} && tar czf {remote_tgz} episodes "
                          f"&& ls -la {remote_tgz}")
    sftp = cli.open_sftp()
    local_tgz = os.path.join(outdir, f"episodes_{stamp}.tgz")
    print("[get ] 下载中（体积大时耐心等）...")
    sftp.get(remote_tgz, local_tgz)
    sftp.close()
    size = os.path.getsize(local_tgz)
    print(f"[ok  ] {local_tgz}  {size / 1024 / 1024:.1f} MB")
    with tarfile.open(local_tgz) as t:
        t.extractall(outdir)
    n = len([d for d in os.listdir(os.path.join(outdir, "episodes"))
             if d.startswith("episode_")]) if os.path.isdir(os.path.join(outdir, "episodes")) else 0
    print(f"[ok  ] 解压到 {outdir}，共 {n} 条 episode")
    run(cli, f"rm -f {remote_tgz}", quiet=True)
    cli.close()
    return 0


def main():
    ap = argparse.ArgumentParser(description="远程批量采集驱动器")
    ap.add_argument("action", choices=["check", "plan", "start", "status", "pull", "stop"])
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--user", default=USER)
    ap.add_argument("--password", default=PWD)
    ap.add_argument("--proxy", default=os.environ.get("LINGBOT_SOCKS", ""),
                    help="SOCKS5 代理 host:port（如 127.0.0.1:1080），默认读环境变量 LINGBOT_SOCKS")
    ap.add_argument("--proxy-user", default="")
    ap.add_argument("--proxy-pass", default="")
    ap.add_argument("--tasks", default="pick_place,push,stack,sweep")
    ap.add_argument("--per", type=int, default=50)
    ap.add_argument("--minutes", type=float, default=0)
    args = ap.parse_args()

    fn = {"check": cmd_check, "plan": cmd_plan, "start": cmd_start,
          "status": cmd_status, "pull": cmd_pull, "stop": cmd_stop}[args.action]
    return fn(args)


if __name__ == "__main__":
    sys.exit(main())
