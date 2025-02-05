import re
import pandas as pd
import networkx as nx
import numpy as np
import pandas as pd
import copy
import seaborn as sns
import matplotlib.pyplot as plt

from compiler import global_control as gc

# traffic = pd.DataFrame(columns=["layer", "src", "dst", "interval", "flit", "counts"])

class MicroOpGraph:

    flow_cnt = 0
    node_types = {
        "wsrc": "wsrc", 
        "insrc": "insrc",
        "sink": "sink",
        "worker": "worker"
    }
    edge_types = {
        "control": "control",
        "data": "data",
        "map_constraint": "map_constraint"
    }

    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    @staticmethod
    def __hash_node(layer_, vpe_, batch_):
        return hash(repr("{}#{}#{}".format(layer_, vpe_, batch_)))

    def get_data(self):
        return self.graph

    def add_layer(self, streams: pd.DataFrame, batch_num=2):
        operators = {}

        # Independenlty add operators at each batch
        for b in range(batch_num):
            op_per_batch = self.add_batch(streams, b)
            operators[b] = op_per_batch

        # Add a control signal between the same operator at adjacent batches: 
        # from the operator at previous batch to the operator at following batch
        for b in range(batch_num - 1):
            for u, v in zip(operators[b], operators[b+1]):
                # self.__add_control_edge(u, v)
                self.add_map_constraint_edge(u, v)

    def add_batch(self, streams: pd.DataFrame, batch) -> list:
        '''Add operators from one-batch layer to the graph
            Return: the added operator list
        '''

        op_graph = self.graph
        operators = []

        layer = streams["layer"][0]

        # Assign an unique id to every flow
        streams.loc[:, "fid"] = range(MicroOpGraph.flow_cnt, MicroOpGraph.flow_cnt + streams.shape[0])
        MicroOpGraph.flow_cnt += streams.shape[0]

        group = streams.groupby("datatype")
        worker_num = group.get_group("output").explode("src").shape[0]

        # some magic numbers ... 
        i_source_magic, w_source_magic, sink_magic = -1, -3, -2

        i_source = MicroOpGraph.__hash_node(layer, i_source_magic, batch)
        w_source = MicroOpGraph.__hash_node(layer, w_source_magic, batch)
        sink = MicroOpGraph.__hash_node(layer, sink_magic, batch)


        def get_prelayer_name(name):
            layer_number = re.findall(r"\d+", name)[-1]
            pre_layer_number = str(int(layer_number) - 1)
            prelayer_name = re.sub(layer_number[::-1], pre_layer_number[::-1], name[::-1])[::-1]
            return prelayer_name

        pre_layer = get_prelayer_name(layer)
        pre_layer_sinks = nx.subgraph_view(op_graph, \
            filter_node=lambda x: op_graph.nodes[x]["op_type"] == "sink" and op_graph.nodes[x]["layer"] == pre_layer
                                  and op_graph.nodes[x]["batch"] == batch)
        assert len(pre_layer_sinks.nodes) <= 1

        # Setup weight source
        w_cnt = group.get_group("weight")["counts"].iloc[0]
        w_delay = group.get_group("weight")["interval"].iloc[0]
        self.add_node(hash_=w_source, layer=layer, type_="wsrc", v_pe=w_source_magic, delay=w_delay, count=w_cnt, batch=batch)
        operators.append(w_source)
        
        # Add Control signals: the weight source won't activate until its preceeding layer finishes
        for s in pre_layer_sinks:
            # op_graph.add_edge(s, w_source, edge_type="control")
            self.add_control_edge(s, w_source)

        # Setup input source
        i_cnt = group.get_group("input")["counts"].iloc[0]
        i_delay = group.get_group("input")["interval"].iloc[0]
        self.add_node(hash_=i_source, layer=layer, type_="insrc", v_pe=i_source_magic, delay=i_delay, count=i_cnt, batch=batch)
        operators.append(i_source)
        # Add control signals: the input source should wait for preceeding layer to finish
        # TODO: We put hard syncronization bairrer between two adjacent layers. However, in some cases, e.g. oc-tiling to ic-tiling,
        # the suceeding layer does not have to wait for whole preceeding layer to finish, it can start once a channel is 
        # generated.

        # FIXME: What does the sink push to next layer's isource, a control signal, or the entire output data ?
        i_data_amount = group.get_group("input")["flit"].iloc[0] * group.get_group("input")["counts"].iloc[0]
        for s in pre_layer_sinks:
            self.add_data_edge(s, i_source, fid=MicroOpGraph.flow_cnt, size=i_data_amount)
            MicroOpGraph.flow_cnt += 1

        # Setup sink (merger)
        o_cnt = group.get_group("output")["counts"].iloc[0]
        o_delay = group.get_group("output")["interval"].iloc[0]
        self.add_node(hash_=sink, layer=layer, type_="sink", v_pe=sink_magic, delay=0, count=1, batch=batch)
        operators.append(sink)

        # Setup workers
        edges = {(r["src"], r["dst"]): (r["fid"], r["flit"]) for _, r in streams.explode("src").explode("dst").iterrows()}
        for w in range(worker_num):
            worker = MicroOpGraph.__hash_node(layer, w, batch)
            self.add_node(hash_=worker, layer=layer, type_="worker", v_pe=w, delay=o_delay, count=o_cnt, batch=batch)
            operators.append(worker)

            # Connect weight source to the worker
            w_flow = edges[(w_source_magic, w)]
            self.add_data_edge(w_source, worker, fid=w_flow[0], size=w_flow[1])

            # Connect input source to the worker
            i_flow = edges[(i_source_magic, w)]
            self.add_data_edge(i_source, worker, fid=i_flow[0], size=i_flow[1])

            # Connect the worker to sink
            o_flow = edges[(w, sink_magic)]
            self.add_data_edge(worker, sink, fid=o_flow[0], size=o_flow[1])

        return operators

    def add_data_edge(self, u: int, v: int, fid: int, size: int):
        self.graph.add_edge(u, v, edge_type="data", fid=fid, size=size)

    def add_control_edge(self, u: int, v: int):
        self.graph.add_edge(u, v, edge_type="control")
    
    def add_map_constraint_edge(self, u: int, v: int):
        self.graph.add_edge(u, v, edge_type="map_constraint")

    def remove_edge(self, u: int, v: int):
        self.graph.remove_edge(u, v)

    # TODO: one function for one node type
    def add_node(self, hash_: int, type_: str, layer: int, v_pe: int, delay: int, count: int, batch: int):
        assert type_ in self.node_types
        self.graph.add_node(hash_, op_type=type_, layer=layer, v_pe=v_pe, delay=delay, cnt=count, batch=batch)

    def set_physical_pe(self, node: int, pe: int):
        self.graph.nodes[node]["p_pe"] = pe

    def get_operator_type(self, node) -> str:
        return self.graph.nodes[node]["op_type"]

    def compute_cycles(self) -> int:
        wg = copy.deepcopy(self.graph)
        for u, _, attr in wg.edges(data=True):
            uattr = wg.nodes[u]
            if uattr["op_type"] == "worker":
                attr["cycle"] = uattr["delay"] * uattr["cnt"]
            else:
                attr["cycle"] = 0
        # path = nx.dag_longest_path(wg, weight="cycle", default_weight=0)
        cycle = nx.dag_longest_path_length(wg, weight="cycle", default_weight=0)
        return cycle

    def draw_graph(self, fig_path):
        seed = 123467

        G = self.get_data()
        red_edges = [(u, v) for u, v, t in G.edges(data="edge_type") if t == "control"]
        black_edges = [(u, v) for u, v in G.edges() if (u, v) not in red_edges]

        pos = nx.spring_layout(G, seed=seed, k=0.4, iterations=20)
        node_color_map = {
            "wsrc": 0,
            "insrc": 0.25,
            "worker": 0.5,
            "sink": 0.75
        }
        node_color = [node_color_map[node_type] for _, node_type in G.nodes(data="op_type")]

        nx.draw_networkx_nodes(G, pos, cmap=plt.get_cmap("Dark2"), node_size=500, node_color=node_color)
        nx.draw_networkx_labels(G, pos, labels={n: int(G.nodes[n]["delay"]) for n in G.nodes()}, font_size=10)
        nx.draw_networkx_edges(G, pos, edgelist=black_edges, arrowstyle="-|>", arrowsize=10)
        nx.draw_networkx_edges(G, pos, edgelist=red_edges, arrowstyle="-|>", arrowsize=10, edge_color="r")

        ax = plt.gca()
        ax.set_axis_off()
        plt.savefig(fig_path, dpi=500)
        plt.close()

    def draw_mapping(self, fig_path):
        G = self.get_data()
        # some magic numbers
        NULL, CTRL = -2, -1
        get_number = lambda x: int(re.findall(r"\d+", x)[-1])

        board = np.full((gc.array_size, ), NULL, dtype=float)
        for _, attr in G.nodes(data=True):
            value = get_number(attr["layer"])
            if attr["op_type"] == "sink":
                value += 0.5
            if attr["op_type"] not in ["wsrc", "insrc"]:
                board[attr["p_pe"]] = value

        board = board.reshape((gc.array_diameter, gc.array_diameter))
        fig = sns.heatmap(data=board, cmap="RdBu_r", linewidths=0.3, annot=True)
        plt.text(60, 60, "NULL: {}, CTRL: {}".format(NULL, CTRL))
        heatmap = fig.get_figure()
        heatmap.savefig(fig_path, dpi=500)
        plt.close()