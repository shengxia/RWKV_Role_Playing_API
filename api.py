import argparse
from flask import Flask
parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default="8888")
parser.add_argument("--model", type=str, default="model/fp16i8-RWKV-4-World-CHNtuned-7B-v1-20230709-ctx4096")
parser.add_argument("--strategy", type=str, default="cuda fp16 *19 -> cuda fp16i8")
parser.add_argument("--cuda_on", type=str, default="1", help="RWKV_CUDA_ON value")
cmd_opts = parser.parse_args()

import os
os.environ["RWKV_CUDA_ON"] = cmd_opts.cuda_on

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