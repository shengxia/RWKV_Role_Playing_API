import json
from modules.model_utils import ModelUtils

model = None

def set_model(model_class:ModelUtils):
  global model
  model = model_class

def return_success(data=None, message='成功', code=200):
  result = {
    'data': data,
    'message': message,
    'code': code
  }
  return json.dumps(result, ensure_ascii=False)

def return_error(message='错误', code=400, data=None):
  result = {
    'data': data,
    'message': message,
    'code': code
  }
  return json.dumps(result, ensure_ascii=False)