#!/bin/sh
cd $HOME/mnt/Gaussian
for sb in 0.3 1.5 3.0; do for sp in 4 7 10; do echo "$sb $sp"; done; done | xargs -P 2 -L 1 sh -c 'python3 research/checks/as_ka_decision_agreement_20261105.py $0 $1 12 36 research/checks/ka_out/sb$0_sp$1_b.json > research/checks/ka_out/sb$0_sp$1_b.log 2>&1'
echo done > research/checks/ka_out/run_b.done
