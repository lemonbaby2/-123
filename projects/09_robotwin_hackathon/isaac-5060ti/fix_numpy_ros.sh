#!/bin/bash
# 修复 ROS 2 Humble 的 rclpy 段错误：把 ~/.local 里与 ROS ABI 不兼容的 numpy 2.x 换成 1.26.4。
# 背景：rclpy 按 numpy 1.x 构建；numpy 2.x 的 OpenBLAS 会在 ld-linux 里把进程带崩。
# 1.26.4 是 1.x 的最后一版，ROS 与主流 ML 栈都兼容。
# 注意：**不要开 set -e** —— 第 1 步的诊断命令本身就会因 numpy 崩溃退出。

echo "=== 当前 numpy 来源（此步崩属预期，正是要修的问题）==="
python3 -c "import numpy; print('  版本', numpy.__version__); print('  路径', numpy.__file__)" 2>&1 | tail -3
echo "  (退出码 $?)"

echo
echo "=== 把 ~/.local 的 numpy 降到 1.26.4 ==="
pip3 install --user --no-cache-dir --timeout 60 --retries 10 \
  -i https://mirrors.aliyun.com/pypi/simple/ \
  --force-reinstall "numpy==1.26.4" 2>&1 | tail -6

echo
echo "=== 修复后 numpy 来源 ==="
python3 -c "import numpy; print('  版本', numpy.__version__); print('  路径', numpy.__file__)"

echo
echo "=== ROS 端到端验证：rclpy 建节点 ==="
source /opt/ros/humble/setup.bash
python3 - << 'PYEOF'
import rclpy, numpy
from rclpy.node import Node
print("  numpy in ROS :", numpy.__version__)
rclpy.init()
n = Node("probe")
print("  NODE OK      :", n.get_name())
n.destroy_node(); rclpy.shutdown()
print("  rclpy 全链路  : 通过")
PYEOF

echo
echo "=== ROS 端到端验证：talker/listener 对跑 8 秒 ==="
rm -f /tmp/rt.log /tmp/rl.log
ros2 run demo_nodes_cpp talker > /tmp/rt.log 2>&1 &
TP=$!
ros2 run demo_nodes_py listener > /tmp/rl.log 2>&1 &
LP=$!
sleep 8
kill $TP $LP 2>/dev/null || true
wait 2>/dev/null || true
echo "  talker 发布   : $(grep -c 'Publishing' /tmp/rt.log) 条"
echo "  listener 收到 : $(grep -c 'I heard' /tmp/rl.log) 条"
grep -oE "I heard: \[Hello World: [0-9]+\]" /tmp/rl.log | tail -2 | sed 's/^/    /'
echo "=== 完成 ==="
