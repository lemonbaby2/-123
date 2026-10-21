#!/bin/bash
set -x
export HF_ENDPOINT=https://hf-mirror.com
export HOME=/home/nvidia
export PATH=/home/nvidia/.local/bin:$PATH
CR=/home/nvidia/microduck-course-run
mkdir -p "$CR/jump-home"
$CR/envs/lightnav/bin/python /home/nvidia/jump_prep.py
