import os
import argparse
from flask import Flask
from flask_cors import CORS

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default="8888")
parser.add_argument("--model", type=str, default="model/fp16i8-RWKV-4-World-CHNtuned-7B-v1-20230709-ctx4096")
parser.add_argument("--strategy", type=str, default="cuda fp16i8 *10 -> cuda fp16")
parser.add_argument("--cuda_on", type=str, default='1', help="RWKV_CUDA_ON value")
parser.add_argument('--jit_on', type=str, default='1')
cmd_opts = parser.parse_args()

os.environ["RWKV_CUDA_ON"] = cmd_opts.cuda_on
os.environ["RWKV_JIT_ON"] = cmd_opts.jit_on

from modules.login import user_login
from modules.methods import methods
from modules.common import set_model
from modules.model_utils import ModelUtils

set_model(ModelUtils(cmd_opts))


api = Flask(__name__)
api.register_blueprint(methods)
api.register_blueprint(user_login)
CORS(api)


if __name__ == "__main__":
    api.run(host='0.0.0.0', port=cmd_opts.port)
