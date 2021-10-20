# Global Variables for controling



# -------------------- Hardware Setup -------------------------

result_dir = "result-512g"



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

array_diameter = 16

array_size = array_diameter**2

arch_config = {

    "p": 6, "cp_if": 6, "cp_of": 0, "tr": 1, "ts": 2, "tw": 1,

    "n": array_diameter**2,

    "d": array_diameter,

    "w": 4096

}



# mapping_style = "Tetris"

# mapping_style = "Zig-Zag"

mapping_style = "Hilbert"





# -------------------- Tasks -------------------------





model = "vgg16"

layer_names = ["unet_layer1", "unet_layer2", "unet_layer3", "unet_layer4", "unet_layer5", "unet_layer6", "unet_layer7", "unet_layer8", "unet_layer9", "unet_layer10", "unet_layer11", "unet_layer12", "unet_layer13", "unet_layer14", "unet_layer15", "unet_layer16", "vgg16_layer1", "vgg16_layer2", "vgg16_layer3", "vgg16_layer4", "mnasnet_layer1", "mnasnet_layer2", "mnasnet_layer3", "mnasnet_layer4", "inception_layer1", "inception_layer2", "inception_layer3", "inception_layer4", "inception_layer5", "inception_layer6", "inception_layer7", "inception_layer8"]
cores = [8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 16, 16, 16, 16, 8, 8, 8, 8, 4, 4, 4, 4, 4, 4, 4, 4]




# -------------------- Task Mapper -------------------------



mapper_verbose = True

# .cfg formatted file corresponding to the hardware setups

conf_filename = "ML_mapper.cfg"



# -------------------- HNOCS -------------------------



simulate_baseline = True

hnocs_working_path = "/home/wangzhao/simulator/HNOCS/simulations"



# -------------------- BookSim -------------------------



# simulate_baseline = False

booksim_working_path = "/home/wangzhao/simulator/booksim2/src"





# -------------------- FOCUS Scheduler -------------------------



focus_schedule = False

scheduler_verbose = False

n_workers = 28

population_size = 100

n_evolution = 50



slowdown_result = "slowdown_unet_vgg16_mnasnet_inception.csv"


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
