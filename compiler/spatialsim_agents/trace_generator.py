import networkx as nx
from copy import deepcopy
from op_graph.micro_op_graph import MicroOpGraph
from routing_algorithms import router
from io import TextIOWrapper
from variables import Variables
from compiler import global_control as gc
import re
import os

class TraceGenerator:
    '''Act as the driver for spatial-simulator. 
    '''

    def __init__(self) -> None:
        self.pkt_counter = 0
        self.prefix = {
            "send": "assemble # NI.send", 
            "recv": "assemble # NI.recv",
            "comp": "assemble # CPU.sleep",
            "sync": "assemble # NI.sync"
        }

    def gen_trace(self, trace_to: dict, routing_board_to: TextIOWrapper, spec_to: TextIOWrapper, \
            spec_ref: TextIOWrapper, graph: MicroOpGraph, router: router.Router):

        op_graph = deepcopy(graph.get_data())

        # Operator field
        for f in trace_to.values():
            print("operators:", file=f)
        self.__gen_op_field(trace_to, op_graph)

        # Data field
        for f in trace_to.values():
            print("\n\ndata:", file=f)
        self.__gen_data_field(trace_to, op_graph)

        # Multicast tree
        self.__gen_routing_board(routing_board_to, op_graph, router)

        # Specification
        self.__gen_specification(spec_to, spec_ref)


    def __gen_specification(self, to: TextIOWrapper, ref: TextIOWrapper):
        trace_file_names = Variables.get_trace_file_names(gc.array_size)
        working_dir = Variables.gen_working_dir(gc.spatial_sim_root, gc.taskname)
        inst_latency_path = Variables.get_inst_latency_path(gc.spatial_sim_root)
        routing_board_path = Variables.get_routing_board_path(gc.spatial_sim_root, gc.taskname)

        task_pattern = re.compile(r"^tasks\s*=\s*{.*?};.*$")
        dir_pattern = re.compile(r"^working_directory\s*=.*?;.*$")
        k_pattern = re.compile(r"^k\s*=.*?;.*$")
        latency_pattern = re.compile(r"^micro_instr_latency\s*=.*?;.*$")
        rb_pattern = re.compile(r"^routing_board\s*=.*?;.*$")

        for line in ref:
            if task_pattern.match(line):
                line = r"tasks = {" + ",".join(trace_file_names) + r"};" + "\n"
            elif dir_pattern.match(line):
                line = "working_directory = {};\n".format(working_dir)
            elif k_pattern.match(line):
                line = "k = {};\n".format(gc.array_diameter)
            elif latency_pattern.match(line):
                line = "micro_instr_latency = {};\n".format(inst_latency_path)
            elif rb_pattern.match(line):
                line = "routing_board = {};\n".format(routing_board_path)
            print(line, file=to, end="")

    def __gen_routing_board(self, to: TextIOWrapper, op_graph: nx.DiGraph, router: router.Router):

        # The Branching Tree
        data_pkt_endpoints = self.__get_pkt_endpoints(op_graph, "data")

        cache = {}
        for pid, endpoints in data_pkt_endpoints.items():
            # Ignore unicast packets
            if len(endpoints["dst"]) == 1:
                continue
            if endpoints["fid"] not in cache:
                node2core = lambda x: op_graph.nodes[x]["p_pe"]
                src = node2core(endpoints["src"])
                dsts = list(map(node2core, endpoints["dst"]))

                mc_tree = router.route(src, dsts)
                cache[endpoints["fid"]] = mc_tree
            else:
                mc_tree = cache[endpoints["fid"]]
            print("{} {} {}".format(pid, src, " ".join(map(str, dsts))), file=to)
            for seg_src, seg_dst in mc_tree.edges():
                print("{} {}".format(seg_src, seg_dst), file=to)
            print("\n", file=to)

    def __gen_data_field(self, to: dict, op_graph: nx.DiGraph):
        # generate data packets
        data_pkt_tuples = self.__get_pkt_endpoints(op_graph, "data")
        for pid, pkt_endpoints in data_pkt_tuples.items():
            assert len(pkt_endpoints["dst"]) >= 1
            src, dsts = pkt_endpoints["src"], pkt_endpoints["dst"]
            size = op_graph.edges[src, dsts[0]]["size"]
            src_core = op_graph.nodes[src]["p_pe"]
            dst_cores = map(lambda x: op_graph.nodes[x]["p_pe"], dsts)
            print("{} # {} # {}".format(pid, ", ".join(map(str, dst_cores)), size), file=to[src_core])

        # generate control packets
        control_pkt_tuples = self.__get_pkt_endpoints(op_graph, "control")
        for pid, pkt_endpoints in control_pkt_tuples.items():
            assert len(pkt_endpoints["dst"]) == 1
            size = 1
            src, dsts = pkt_endpoints["src"], pkt_endpoints["dst"]
            src_core = op_graph.nodes[src]["p_pe"]
            dst_cores = map(lambda x: op_graph.nodes[x]["p_pe"], dsts)
            print("{} # {} # {}".format(pid, ", ".join(map(str, dst_cores)), size), file=to[src_core])

    def __gen_op_field(self, to: dict, op_graph: nx.DiGraph):

        assert nx.is_directed_acyclic_graph(op_graph)
        for _, __, attr in op_graph.edges(data=True):
            attr["vis"] = False
            attr["pkt"] = []

        pf = self.prefix
        instrs = to
        for node in nx.topological_sort(op_graph):

            assert "p_pe" in op_graph.nodes[node]
            nattr = op_graph.nodes[node]
            assert nattr["p_pe"] in instrs

            node2pe = lambda x: op_graph.nodes[x]["p_pe"]

            # The instructions generated by this operator at each iteration
            iteration_cnt = int(nattr["cnt"])
            instrution_list = [[] for _ in range(iteration_cnt)]

            # Firstly, the operator consumes its dependent data and control signals from its fan-in edges
            for u, v, eattr in op_graph.in_edges(node, data=True):
                # We ignore packets received from the sender itself
                if node2pe(u) == node2pe(v):
                    continue
                # The incoming edges must be visited
                assert eattr["vis"]
                if eattr["edge_type"] == "data":
                    # Where to add data dependency instruction, i.e. NI.recv. 
                    self.__observe_dependent_data(eattr["pkt"], instrution_list, pf["recv"])
                elif eattr["edge_type"] == "control":
                    self.__observe_sync_signal(eattr["pkt"], instrution_list, pf["sync"])
 
            # Secondly, the operator occupies the CPU or Acc several cycles ... 
            for it in instrution_list:
                it.append("{} {:.0f}".format(pf["comp"], nattr["delay"]))

            # Thirdly, for every output data-edge, the operator generates one tensor per iteration.
            # We ignore the packet sent to the sender itself
            data_edges = [(u, v) for u, v, t in op_graph.out_edges(node, data="edge_type") if t == "data" and node2pe(u) != node2pe(v)]
            for it in instrution_list:
                flows = {op_graph.edges[e]["fid"] for e in data_edges}      # Remove duplicates
                fid_to_pid = {fid: pid for fid, pid in zip(flows, range(self.pkt_counter, self.pkt_counter+len(flows)))}
                self.pkt_counter += len(fid_to_pid)

                # Push tensors to its out edges
                pid_to_dests = {pid: [] for pid in fid_to_pid.values()}
                for u, v in data_edges:
                    pid = fid_to_pid[op_graph.edges[u, v]["fid"]]
                    op_graph.edges[u, v]["pkt"].append(pid)
                    op_graph.edges[u, v]["vis"] = True
                    pid_to_dests[pid].append(op_graph.nodes[v]["p_pe"])

                # Generate send instructions
                for pid, dests in pid_to_dests.items():
                    it.append("{} {:.0f} {}".format(pf["send"], pid, " ".join(map(str, dests))))

            # Finally, the operator send a finish signal to sync-edges to indicate its ends
            control_edges = [(u, v) for u, v, t in op_graph.out_edges(node, data="edge_type") if t == "control" and node2pe(u) != node2pe(v)]
            for u, v in control_edges:
                pid = self.pkt_counter
                self.pkt_counter += 1
                op_graph.edges[u, v]["pkt"].append(pid)
                op_graph.edges[u, v]["vis"] = True
                instrution_list[-1].append("{} {:.0f} {}".format(pf["send"], pid, op_graph.nodes[v]["p_pe"]))

            # Write to the trace file
            collapse = [instr for step in instrution_list for instr in step]
            for inst in collapse:
                print(inst, file=instrs[nattr["p_pe"]])

    def __get_pkt_endpoints(self, op_graph: nx.DiGraph, edge_type: str) -> dict:
        # {pid: {"src": src, "dst": [d1, d2], "size": size}}
        if edge_type == "data":
            data_graph = nx.subgraph_view(op_graph, filter_edge= \
                lambda u, v: op_graph.edges[u, v]["edge_type"] == "data")

            fid_to_endpoints = {f: {"src": -1, "dst": []} for _, _, f in data_graph.edges(data="fid")}
            for u, v, f in data_graph.edges(data="fid"):
                assert data_graph.edges[u, v]["edge_type"] == "data"
                src = fid_to_endpoints[f]["src"]
                assert src == -1 or data_graph.nodes[src]["p_pe"] == data_graph.nodes[u]["p_pe"]
                fid_to_endpoints[f]["src"] = u
                fid_to_endpoints[f]["dst"].append(v)
                fid_to_endpoints[f]["fid"] = f

            pid_to_fid = {}
            for _, __, eattr in data_graph.edges(data=True):
                for pid in eattr["pkt"]:
                    pid_to_fid[pid] = eattr["fid"]

            ret = {pid: fid_to_endpoints[fid] for pid, fid in pid_to_fid.items()}

        elif edge_type == "control":
            control_graph = nx.subgraph_view(op_graph, filter_edge= \
                lambda u, v: op_graph.edges[u, v]["edge_type"] == "control")
            ret = {}
            for u, v, eattr in control_graph.edges(data=True):
                for pid in eattr["pkt"]:
                    ret[pid] = {"src": u, "dst": [v]}
        else:
            assert False

        return ret

    def __observe_dependent_data(self, dependent_data: list, instruction_list: list, instr_prefix):
        op_iters = len(instruction_list)
        dep_num = len(dependent_data)

        # One must be exactly divided by the other
        assert op_iters % dep_num == 0 or dep_num % op_iters == 0
        if dep_num <= op_iters:
            iter_interval = op_iters // dep_num
            for i in range(0, op_iters, iter_interval):
                instruction_list[i].append("{} {}".format(instr_prefix, dependent_data[i // iter_interval]))
        else:
            tensors_per_iter = dep_num // op_iters
            for i in range(0, op_iters):
                for j in range(tensors_per_iter):
                    instruction_list[i].append("{} {}".format(instr_prefix, dependent_data[i * tensors_per_iter + j]))

    def __observe_sync_signal(self, sync_signals: list, instruction_list: list, instr_prefix):
        for s in sync_signals:
            instruction_list[0].append("{} {}".format(instr_prefix, s))