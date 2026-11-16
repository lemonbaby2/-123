#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""仓库完整性与安全性检查：python tests/test_package_layout.py -v"""

import os
import re
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

try:  # CI 不强制安装第三方包；缺 PyYAML 时退化为缩进/格式检查
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT / "ros2_ws"
# 拼接构造，避免测试文件自身触发脱敏扫描
FORBIDDEN = ("192.168." + "1.217", "100.97." + "27.19", "dgx_w13_" + "ed25519",
             "密码：" + "nvidia", "ssh -i " + "dgx_w13")


def all_files():
    return [p for p in ROOT.rglob("*") if p.is_file()]


class TestLayout(unittest.TestCase):
    def test_required_files(self):
        required = [
            "README.md", "ros2_ws/README.md",
            "ros2_ws/env.sh", "ros2_ws/00_一键构建.sh",
            "ros2_ws/01_启动课堂.sh", "ros2_ws/02_停止全部.sh",
            "ros2_ws/dashboard/server.py", "ros2_ws/dashboard/index.html",
            "ros2_ws/src/week12_odometry/launch/demo_w12.launch.py",
            "ros2_ws/src/week12_odometry/scripts/velocity_arbiter.py",
            "ros2_ws/src/week12_odometry/scripts/check_w12.sh",
            "ros2_ws/src/week12_odometry/worlds/arena_w12.sdf",
            "portal/index.html", "portal/range_server.py",
            "src/course_algorithms.py", "tests/test_course_algorithms.py",
            "evidence/selfcheck_w12.txt", "evidence/gazebo_world.png",
            "evidence/rviz_odom_slam.png", "evidence/web_dashboard.png",
            "evidence/course_demo_5min.mp4",
            "teaching/ROS2与Ubuntu全量命令与验证代码手册_20261116.xlsx",
        ]
        missing = [f for f in required if not (ROOT / f).exists()]
        self.assertEqual(missing, [], f"missing files: {missing}")

    def test_readme_local_links(self):
        pattern = re.compile(r"\[[^]]+\]\((?!https?://|#|mailto:)([^)]+)\)")
        for doc in [ROOT / "README.md", *ROOT.rglob("*/README.md")]:
            for target in pattern.findall(doc.read_text(encoding="utf-8")):
                clean = target.split("#", 1)[0]
                if clean:
                    self.assertTrue((doc.parent / clean).exists(),
                                    f"broken link in {doc.name}: {target}")

    def test_no_secrets_in_text(self):
        text_ext = {".md", ".txt", ".html", ".js", ".css", ".py", ".sh",
                    ".yaml", ".xml", ".json", ".rviz", ".sdf", ".xacro"}
        for p in all_files():
            if p.suffix.lower() not in text_ext:
                continue
            s = p.read_text(encoding="utf-8", errors="ignore")
            for token in FORBIDDEN:
                self.assertNotIn(token, s, f"{p.relative_to(ROOT)} contains {token}")

    def test_no_secrets_in_office_files(self):
        for p in ROOT.rglob("*"):
            if p.suffix.lower() not in {".xlsx", ".docx"}:
                continue
            with zipfile.ZipFile(p) as z:
                for n in z.namelist():
                    if n.endswith((".xml", ".rels")):
                        s = z.read(n).decode("utf-8", "ignore")
                        for token in FORBIDDEN:
                            self.assertNotIn(token, s, f"{p.name}/{n}: {token}")

    def test_no_private_key_material(self):
        for p in all_files():
            self.assertNotIn("PRIVATE KEY", p.name)
            if p.suffix.lower() in {".pub", ".pem", ".key"}:
                self.fail(f"key-like file must not be published: {p.name}")


class TestSyntaxAndContracts(unittest.TestCase):
    def test_all_python_parses(self):
        for p in ROOT.rglob("*.py"):
            compile(p.read_text(encoding="utf-8"), str(p), "exec")

    def test_xml_files_parse(self):
        for ext in ("*.xacro", "*.sdf", "*.xml", "package.xml"):
            for p in ROOT.rglob(ext):
                ET.parse(p)

    def test_yaml_files_parse(self):
        for ext in ("*.yaml", "*.rviz"):
            for p in ROOT.rglob(ext):
                text = p.read_text(encoding="utf-8")
                self.assertNotIn("\t", text, f"tab indentation in {p.name}")
                if yaml is not None:
                    with p.open(encoding="utf-8") as f:
                        yaml.safe_load(f)

    def test_isolation_contract(self):
        env = (WS / "env.sh").read_text(encoding="utf-8")
        self.assertIn("ROS_DOMAIN_ID:-42", env)
        self.assertIn("GZ_PARTITION:-w12course", env)
        active = [ln for ln in env.splitlines()
                  if ln.strip() and not ln.lstrip().startswith("#")]
        self.assertFalse(any("set -u" in ln for ln in active),
                         "set -u must not wrap ROS setup.bash")

    def test_slam_lifecycle_contract(self):
        launch = (WS / "src/week12_odometry/launch/demo_w12.launch.py").read_text(encoding="utf-8")
        self.assertIn("online_async_launch.py", launch,
                      "slam_toolbox is a LifecycleNode: plain Node never publishes /map")

    def test_twist_stamped_contract(self):
        bridge = (WS / "src/week12_odometry/config/bridge_w12.yaml").read_text(encoding="utf-8")
        for key in ("ros_topic_name", "ros_type_name", "gz_type_name", "direction"):
            self.assertIn(key, bridge)
        launch = (WS / "src/week12_odometry/launch/demo_w12.launch.py").read_text(encoding="utf-8")
        self.assertIn("TwistStamped", launch)
        drive = (WS / "src/week12_odometry/scripts/drive_demo.sh").read_text(encoding="utf-8")
        self.assertIn("twist: {linear", drive)
        payload_lines = [ln for ln in drive.splitlines()
                         if ln.strip().startswith("local payload=")]
        self.assertTrue(payload_lines)
        self.assertNotIn("twist: {twist:", "".join(payload_lines))

    def test_selfcheck_evidence(self):
        s = (ROOT / "evidence/selfcheck_w12.txt").read_text(encoding="utf-8")
        self.assertRegex(s, r"PASS\s*=\s*24")
        self.assertRegex(s, r"FAIL\s*=\s*0")

    def test_video_is_not_empty(self):
        self.assertGreater((ROOT / "evidence/course_demo_5min.mp4").stat().st_size, 1_000_000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
