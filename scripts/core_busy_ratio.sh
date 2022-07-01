#!/bin/bash
# Ratio of busy cycles for computing cores

# Add the following codes to focus.py, under `if gc.simulate_baseline`
# mems = [k for k, v in TaskCompiler().gen_physical_layout().items() if v != "mems"]
# simulator.plot_busy_ratio(os.path.join(gc.visualization_root, "ratio{}.png".format(gc.taskname)), set(mems))


# Run 
# for logb in {0..5}
# do
# {
#     batch=$[ 2** $logb ]
#     python3 focus.py -bm benchmark/16_16.yaml -debug -d 8 -b $batch -fr 1024-1024-512 ds > /dev/null 2>&1
# } &
# done

python3 focus.py -bm benchmark/vgg.yaml -debug -d 8 -b 1 -fr 1024-1024-512 ds > fkvgg.log 2>&1 &
python3 focus.py -bm benchmark/wide_resnet.yaml -debug -d 8 -b 1 -fr 1024-1024-512 ds > fkresnet.log 2>&1 & 
python3 focus.py -bm benchmark/bert.yaml -debug -d 8 -b 1 -fr 1024-1024-512 ds > fkbert.log 2>&1 &
