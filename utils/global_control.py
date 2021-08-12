# Global Variables for controling





# -------------------- Timeloop -------------------------



timeloop_verbose = False

# whether to invoke timeloop-mapper

search_dataflow = False

# Search time

timeout = 30

# Core numbers (default: number specified in db/arch/arch.yaml)

top_level_cnt = None

# whether to invoke timeloop-model

dump_comm_status = False



# data orders

datatype = ["weight", "input", "output"]

# -------------------- Hardware -------------------------



# hardware setup

array_diameter = 8

array_size = array_diameter**2

arch_config = {

    "p": 6, "cp_if": 6, "cp_of": 0, "tr": 1, "ts": 2, "tw": 1,

    "n": array_diameter**2,

    "d": array_diameter,

    "w": 1024

}



# mapping_style = "Tetris"

# mapping_style = "Zig-Zag"

mapping_style = "Hilbert"





# -------------------- Tasks -------------------------



# layer_names = [

#     "resnet50_layer43", "resnet50_layer44", "resnet50_layer45", "resnet50_layer46", \

#     "vgg16_layer1", "vgg16_layer2", "vgg16_layer3", "vgg16_layer4", \

#     "inception_layer1", "inception_layer2", "inception_layer3", "inception_layer4"

# ]



# layer_names = [

#     "resnet50_layer43", "resnet50_layer44", \

#     "vgg16_layer1", "vgg16_layer2", \

#     "inception_layer1", "inception_layer2"

# ]



# cores = [

#     8, 16, 1, 8, 16, 2

# ]



model = "vgg16"

layer_names = ["wide_resnet50_2_layer34", "wide_resnet50_2_layer35", "wide_resnet50_2_layer36", "wide_resnet50_2_layer37", "wide_resnet50_2_layer38", "wide_resnet50_2_layer39", "wide_resnet50_2_layer40", "wide_resnet50_2_layer41", "resnext50_32x4d_layer31", "resnext50_32x4d_layer32", "resnext50_32x4d_layer33", "resnext50_32x4d_layer34"]
cores = [2, 2, 2, 2, 2, 2, 2, 2, 12, 12, 12, 12]


# layer_names = [

#     "resnet50_layer43", "resnet50_layer44", "resnet50_layer45",

#     "vgg16_layer1", "vgg16_layer2", "vgg16_layer3", "vgg16_layer4"

# ]

# cores = [

#     16,

#     16, 16,

#     4, 4, 

#     4, 4

# ]





# -------------------- Task Mapper -------------------------



mapper_verbose = True

# .cfg formatted file corresponding to the hardware setups

conf_filename = "ML_mapper.cfg"



# -------------------- HNOCS -------------------------



simulate_baseline = False

hnocs_working_path = "/home/wangzhao/simulator/HNOCS/simulations"



# -------------------- BookSim -------------------------



# simulate_baseline = False

booksim_working_path = "/home/wangzhao/simulator/booksim2/src"





# -------------------- FOCUS Scheduler -------------------------



focus_schedule = True

scheduler_verbose = False

n_workers = 28

population_size = 2

n_evolution = 1



slowdown_result = "slowdown_wide_resnet50_2_resnext50_32x4d.csv"


# -------------------- [Optional] Estimator -------------------------



use_estimator = False

cv = 2





# -------------------- Helping Funcions -------------------------



def debug_show(item):

    from pprint import PrettyPrinter

    pp = PrettyPrinter(indent=2)

    pp.pprint(item)

    exit(0)





def generate_config_file():

    # Generate such configure file

    import configparser as cp

    config = cp.ConfigParser()

    config["accelerator_config"] = {

        "tile_array_height": array_diameter, 

        "tile_array_width": array_diameter

    }

    config["layer_config"] = {

        "layer_num": len(cores),

        "layer_MACs": ":".join(map(lambda x: str(x), cores))

    }

    config["mapping_style"] = {

        "mapping_style": mapping_style

    }

    config.write(open(conf_filename, "w"))



generate_config_file()
