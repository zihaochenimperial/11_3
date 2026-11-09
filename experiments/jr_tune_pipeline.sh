#!/bin/bash
# JR tuning pipeline (deterministic, preregistered selection rules in jr_reduce.py): wait T1 -> reduce T1 -> T2 -> reduce -> T3 -> reduce -> RIDGE (descriptive)
cd /home/claude/geo || exit 1
while pgrep -f "^python3 experiments/jr_run.py --stage tune --phase T1" >/dev/null; do sleep 20; done
echo "$(date -u +%T) T1 finished"; python3 experiments/jr_reduce.py tune T1 > outputs/JR/tune/reduce_T1.txt 2>&1 || { echo "reduce T1 FAILED"; tail -5 outputs/JR/tune/reduce_T1.txt; exit 2; }
echo "$(date -u +%T) reduced T1; starting T2"; python3 experiments/jr_run.py --stage tune --phase T2 --workers 2 > outputs/JR/tune/run_T2.log 2>&1
python3 experiments/jr_reduce.py tune T2 > outputs/JR/tune/reduce_T2.txt 2>&1 || { echo "reduce T2 FAILED"; tail -5 outputs/JR/tune/reduce_T2.txt; exit 3; }
echo "$(date -u +%T) reduced T2; starting T3"; python3 experiments/jr_run.py --stage tune --phase T3 --workers 2 > outputs/JR/tune/run_T3.log 2>&1
python3 experiments/jr_reduce.py tune T3 > outputs/JR/tune/reduce_T3.txt 2>&1 || { echo "reduce T3 FAILED"; tail -5 outputs/JR/tune/reduce_T3.txt; exit 4; }
echo "$(date -u +%T) reduced T3 (selection.json written); starting RIDGE (descriptive)"; python3 experiments/jr_run.py --stage tune --phase RIDGE --workers 2 > outputs/JR/tune/run_RIDGE.log 2>&1
python3 experiments/jr_reduce.py ridge > outputs/JR/tune/reduce_RIDGE.txt 2>&1
echo "$(date -u +%T) TUNE PIPELINE DONE"; tail -25 outputs/JR/tune/reduce_T3.txt
