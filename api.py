import argparse
from flask import Flask
from flask import g
parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default="8888")
parser.add_argument("--model", type=str, default="model/RWKV-4-Pile-169M-20220807-8023")
# parser.add_argument("--model", type=str, default="model/fp16i8_RWKV-4-Raven-7B-v9x-Eng49-Other1%-20230418-ctx4096.pth")
parser.add_argument("--strategy", type=str, default="cuda fp16i8")
parser.add_argument("--cuda_on", type=str, default="1", help="RWKV_CUDA_ON value")
cmd_opts = parser.parse_args()

import os
os.environ["RWKV_CUDA_ON"] = cmd_opts.cuda_on
import numpy as np
np.set_printoptions(precision=4, suppress=True, linewidth=200)
from modules.model_utils import ModelUtils
from modules.common import set_model

set_model(ModelUtils(cmd_opts))

from modules.methods import methods
from modules.login import user_login

api = Flask(__name__) 
api.register_blueprint(methods)
api.register_blueprint(user_login)

if __name__ == "__main__":
  api.run(port=cmd_opts.port, host='0.0.0.0')