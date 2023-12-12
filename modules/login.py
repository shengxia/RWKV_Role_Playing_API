import flask
import os
import uuid
import glob
import shutil
from modules.common import return_error, return_success

user_login = flask.Blueprint('user_login', __name__)

def copyfiles(src,dst):
    file_names = glob.glob(src)
    for file_name in file_names:
        shutil.copy(file_name, dst)


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
    os.makedirs(f"./chars/{user_name}/init_state", exist_ok=True)
    os.makedirs(f"./save/{user_name}", exist_ok=True)
    try:
        copyfiles('./chars/*.json', f'./chars/{user_name}/')
    except:
        return return_error('登陆失败')
    data = {
        'user_name': user_name,
        'token': token
    }
    return return_success(data)

# 游客登录
@user_login.route("/login/tmp", methods=['post'])
def login_tmp():
    user_name = 'tmp-' + str(uuid.uuid1()).replace('-', '')
    save_path = f"./tmp/cache/{user_name}"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    os.makedirs(f"./tmp/chars/{user_name}/init_state", exist_ok=True)
    os.makedirs(f"./tmp/save/{user_name}", exist_ok=True)
    try:
         copyfiles('./chars/*.json', f'./tmp/chars/{user_name}/')
    except:
        return return_error('登陆失败')
    with open(save_path, 'w') as f:
        f.write(user_name)
    data = {
        'user_name': user_name,
        'token': user_name
    }
    return return_success(data)
