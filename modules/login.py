import flask
import os
import uuid
from modules.common import return_error, return_success

user_login = flask.Blueprint('user_login', __name__)

# 登录
@user_login.route("/login", methods=['post'])
def login():
  user_name = flask.request.values.get('user_name')
  password = flask.request.values.get('password')
  if not user_name or not password:
    return return_error('缺少关键参数')
  user_file = f'./user/{user_name}'
  if not os.path.exists(user_file):
    return return_error('用户不存在')
  with open(user_file, 'r', encoding='utf8') as f:
    pwd = f.read()
    if pwd != password:
      return return_error('密码不正确')
  token = str(uuid.uuid1()).replace('-', '')
  with open(f'./cache/{user_name}', 'w') as f:
    f.write(token)
  data = {
    'user_name': user_name,
    'token': token
  }
  return return_success(data)
