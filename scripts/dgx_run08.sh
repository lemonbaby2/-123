#!/bin/bash
# 等待 08 双环境就绪后运行 Notebook 08（LightNav）
set -x
CR=/home/nvidia/microduck-course-run
MENV=$CR/envs/lightnav-0/bin/python
NBPY=$CR/envs/notebook/bin/python

for i in $(seq 1 80); do
  ok_model=0; ok_nb=0
  [ -x "$MENV" ] && "$MENV" -c "import lightnav" 2>/dev/null && ok_model=1
  "$NBPY" -c "import vln_mujoco" 2>/dev/null && ok_nb=1
  if [ "$ok_model" = "1" ] && [ "$ok_nb" = "1" ]; then
    echo "LIGHTNAV_ENVS_READY"
    break
  fi
  echo "waiting lightnav envs ($i) model=$ok_model nb=$ok_nb..."
  sleep 30
done
[ "$ok_model" = "1" ] && [ "$ok_nb" = "1" ] || { echo "LIGHTNAV_ENV_TIMEOUT"; exit 1; }

cd "$CR"
export LIGHTNAV_ROOT=/home/nvidia/LightNav-0
export LIGHTNAV_MODEL_ENV=$CR/envs/lightnav-0
export LIGHTNAV_MODEL_PATH=$CR/checkpoints/LightNav-0
export LIGHTNAV_ROBOT_MODEL=/home/nvidia/workspaces/microduck_rl/src/mjlab_microduck/robot/microduck/robot_allcollisions.xml
export LIGHTNAV_WALKING_POLICY=$CR/checkpoints/microduck-navigation/alpha_walking.onnx
export LIGHTNAV_OUTPUT=$CR/recordings/lightnav
export MICRODUCK_TOPIC_ROOT=$CR/topic
export MUJOCO_GL=egl OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1
export WANDB_MODE=disabled HF_HUB_OFFLINE=1
setsid nohup "$NBPY" run_notebook.py 08 > 08_validate2.log 2>&1 < /dev/null &
echo "LAUNCHED_08 pid=$!"
