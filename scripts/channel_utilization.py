import os
import sys
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(root, "compiler"))

import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from compiler.focus.individual import XYRouter
from compiler.op_graph.micro_op_graph import MicroOpGraph
from compiler.routing_algorithms.meshtree_router import MeshTreeRouter, WhirlTreeRouter, RPMTreeRouter
from compiler import global_control as gc



def channel_load(op_graph: MicroOpGraph):
    flows = op_graph.get_flow_endpoints()

    # tree_router = RPMTreeRouter(gc.array_diameter)
    # tree_router = WhirlTreeRouter(gc.array_diameter)
    tree_router = MeshTreeRouter(gc.array_diameter)

    path_router = XYRouter((gc.array_diameter, gc.array_diameter))
    channels = [[0 for _ in range(6)] for _ in range(gc.array_size)]
    for pid, endpoints in flows.items():
        mc_tree = tree_router.route(endpoints["src"], endpoints["dst"]).edges()
        for src, dst in mc_tree:
            passing_channels = path_router.getPath(src, dst)
            for c in passing_channels:
                channels[c[0]][c[1]] += endpoints["total_bytes"]
    print(channels)
    board = np.full((gc.array_size, ), 0, dtype=float)
    channel_board = np.asarray_chkfinite(channels, dtype=float)
    channel_board = channel_board.reshape((gc.array_size * 6, ))
    for router in range(gc.array_size):
        board[router] = sum(channels[router])
    idx = np.argpartition(board, -10)[-10: ]
    top5 = board[idx]
    # print(sum(top5) / sum(board))
    # print(max(channel_board) / min([i for i in channel_board.tolist() if i != 0]))
    print(np.std(channel_board) / np.average(channel_board))
    fig = sns.histplot(channel_board, bins=15)
    # board = board.reshape((gc.array_diameter, gc.array_diameter))
    # fig = sns.heatmap(data=board, cmap="RdBu_r", linewidths=0.3, annot=False)
    heatmap = fig.get_figure()
    heatmap.savefig(os.path.join(gc.visualization_root, "channel_loads_{}.png".format(gc.taskname)), dpi=500)
    plt.close()