# FOCUS: A Compiling Toolchain for Spatial Architectures

## Project structure

* `./compiler`: FOCUS's source code.
* `./simulator`: A cycle-accurate simulator for spatial architectures.
* `./database`: Model information dumped by the timeloop-PyTorch tool.
* `./benchmark`: Task specification files. 
* `./libs`: Timeloop executable files and their dependent dynamic libraries.
* `./visualization`: Graphics of operator graphs, task mapping results.
* `./results`: Final outputs, including tasks executed cycles. 
* `./buffer`: Intermediate files generated by timeloop and focus, these files can be used as a cache to accelerate compiling.


## Dependence

This project depends on [Timeloop](https://github.com/buxiangqimingle233/Timeloop-pro), an automatic dataflow optimization framework developed by NVIDIA. We pre-compiled Timeloop and store its executable files in `./libs`, but to execute them, you need to install its dependent libraries: 

```
libconfig++-dev
libboost-dev
libboost-iostreams-dev
libboost-serialization-dev
libyaml-cpp-dev
libncurses-dev
libtinfo-dev
libgpm-dev
```

FOCUS also relies on some python libraries, install them with
```
pip install -r requirement.txt
```

## How to use ? 
First, initialize submodules. 
```
git submodule update --init --recursive --remote
```

Then run the following code to compile the simulator. 
```
cd simulator
./rebuild.sh
cd ..
```

Execute ``run.sh`` to run the example task, which is specified by `benchmark/test.yaml`. Run the following command for a detailed description of FOCUS: 
```
python focus.py -h
```

## Inputs & Outputs

FOCUS compiles a tensor application, which is formulated as a graph of tensor operators, to instruction streams to drive the spatial architecture simulator. To describe the task, users should provide the following inputs: 
* Task specification file: describes the tensor operator graph, including tensor operators and their data dependencies. Examples include `benchmark/**.yaml`
* Tensor operator bank: details of tensor operators, such as operand dimensions, operation type, etc. Examples include `database/bert/**.yaml`.
* Dataflow constraints: describes how the processing elements are designed. Default: `database/constraints/simba_constraints.yaml`. 
* Architecture description: describes the architecture the task running on, including PE array size, inter-PE channel width, etc. Default: `database/arch/simba_512gops_256core.yaml` and `simulator/tasks/**/spatial_spec`. 

The resulting instruction streams locate in `simulator/tasks/'task_name'`, the task name concatenates all model names within your task specification file, e.g. `bert_vgg16`. Please check `simulator/README.md` for detailed formats. 

## For developers

To convert a tensor application to instruction streams of processing elements, the FOCUS compiling toolchain works in the following stages: 
* Dataflow Search: FOCUS invokes Timeloop to split the model layers into multiple sub-operators. These sub-operators form a graph where nodes dictate sub-operators and edges are data dependencies between them. Users should manually allocate the number of cores for each layer in task files. Related code locates at `compiler/timeloop_agents`. 
* Task Mapping: FOCUS maps these sub-operators to physical processing elements. The mapping process assigns each sub-operator with an attribute `p_pe` . Related code locates at `compiler/mapping_algorithms`. 
* Path Routing [ Optional ]: You can specify the routing path for each message, by adding intermediate transfer points between the message's source and destination. Related code locates at `compiler/routing_algorithms`. 


## Something to mention

We assume a DOJO-like spatial architecture, which is only capable to access off-chip memory by edge processing elements. Therefore, internal PEs rely on messages with edge these PEs to access off-chip memory, see `compiler/timeloop_agents/README.md` for details. 

We assume a fixed NVDLA-like dataflow within processing elements and flexible dataflows among processing elements. If you want to measure different processing elements, e.g. Eyeriss-like PE or MAERI-like PE that supports flexible dataflows, you need to change the timeloop constraint file: `database/constraints/simba_constraints.yaml`; If you want to modify architecture setups, e.g. the number of PE and PE performance, you need to change timeloop architecture specification file: `database/arch/simba_512gops_256core.yaml`, and the timeloop constraint file to match with it. 

