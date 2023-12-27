import flask
import os
import json
import pickle
import uuid
import copy

from modules.common import return_error, return_success, get_model
from modules.model_utils import format_chat_param
from modules.role_info import RoleInfo

methods = flask.Blueprint('methods', __name__)


@methods.before_request
def before():
    user_name = flask.request.values.get('user_name')
    token = flask.request.values.get('token')
    if not user_name or not token:
        return return_error('关键参数为空')
    prefix = get_dir_prefix(token)
    user_cache = f'{prefix}cache/{user_name}'
    if not os.path.exists(user_cache):
        return return_error('用户不存在')
    with open(user_cache, 'r', encoding='utf8') as f:
        t = f.read()
        if t != token:
            return return_error('token失效，请重新登录', 403)
    pass

# 获取角色列表
@methods.route("/characters/list", methods=['post'])
def characters_list():
    user_name = flask.request.values.get('user_name')
    token = flask.request.values.get('token')
    prefix = get_dir_prefix(token)
    path = f'{prefix}chars/{user_name}/'
    files = os.listdir(path)
    char_list = []
    for f in files:
        file_name_arr = f.split('.')
        if file_name_arr[-1] == 'json':
            with open(path + f, 'r', encoding='utf-8') as char_file:
                char = json.loads(char_file.read())
                tmp = {
                    'char_name': char['bot'],
                    'file_name': f,
                    'avatar': char['avatar']
                }
                char_list.append(tmp)
    data = {
        'list': char_list
    }
    return return_success(data)

# 获取角色详情
@methods.route("/characters/get", methods=['post'])
def characters_get():
    user_name = flask.request.values.get('user_name')
    character_name = flask.request.values.get('character_name')
    if not character_name:
        return return_error('关键参数为空')
    token = flask.request.values.get('token')
    prefix = get_dir_prefix(token)
    character_path = f'{prefix}chars/{user_name}/{character_name}.json'
    if not os.path.exists(character_path):
        return return_error('角色不存在')
    with open(character_path, 'r', encoding='utf-8') as f:
        char = json.loads(f.read())
    return return_success(char)

# 创建/保存角色
@methods.route("/characters/save", methods=['post'])
def characters_save():
    user_name = flask.request.values.get('user_name')
    user = flask.request.values.get('user')
    bot = flask.request.values.get('bot')
    greeting = flask.request.values.get('greeting')
    bot_persona = flask.request.values.get('bot_persona')
    example_message = flask.request.values.get('example_message')
    use_qa = flask.request.values.get('use_qa', False, type=bool)
    avatar = flask.request.values.get('avatar')
    if not user or not bot or not greeting or not bot_persona:
        return return_error('关键参数为空')
    token = flask.request.values.get('token')
    prefix = get_dir_prefix(token)
    with open(f"{prefix}chars/{user_name}/{bot}.json", 'w', encoding='utf8') as f:
        data = {
            'user': user,
            'bot': bot,
            'greeting': greeting,
            'bot_persona': bot_persona,
            'example_message': example_message,
            'use_qa': use_qa,
            'avatar': avatar
        }
        json.dump(data, f, indent=2, ensure_ascii=False)
    sav_path = f"{prefix}save/{user_name}/{bot}.sav"
    if os.path.exists(sav_path):
        os.remove(sav_path)
    save_file = f'{prefix}chars/{user_name}/init_state/{bot}.sav'
    if os.path.exists(save_file):
        os.remove(save_file)
    return return_success()

# 删除角色
@methods.route("/characters/del", methods=['post'])
def characters_delete():
    user_name = flask.request.values.get('user_name')
    char_name = flask.request.values.get('character_name')
    if not char_name:
        return return_error('关键参数为空')
    token = flask.request.values.get('token')
    prefix = get_dir_prefix(token)
    json_path = f"{prefix}chars/{user_name}/{char_name}.json"
    sav_path = f"{prefix}save/{user_name}/{char_name}.sav"
    save_file = f'{prefix}chars/{user_name}/init_state/{char_name}.sav'
    if os.path.exists(json_path):
        os.remove(json_path)
    if os.path.exists(sav_path):
        os.remove(sav_path)
    if os.path.exists(save_file):
        os.remove(save_file)
    return return_success()

# 加载角色
@methods.route("/characters/load", methods=['post'])
def characters_load():
    user_name = flask.request.values.get('user_name')
    char_name = flask.request.values.get('character_name')
    if not char_name:
        return return_error('关键参数为空')
    token = flask.request.values.get('token')
    role_info = init_chat(token, user_name, char_name)
    if not role_info:
        return return_error('角色不存在')
    data = {
        'chat': role_info.chatbot
    }
    return return_success(data)

def init_chat(token, user_name, char_name):
    prefix = get_dir_prefix(token)
    char_path = f'{prefix}chars/{user_name}/{char_name}.json'
    if not os.path.exists(char_path):
        return False
    with open(char_path, 'r', encoding='utf-8') as f:
        char = json.loads(f.read())
    role_info = RoleInfo(
        [], char['user'], char['bot'], char['greeting'], char['bot_persona'], 
        char['example_message'], char['use_qa'], str(uuid.uuid1()).replace('-', '')
    )
    greeting = char['greeting']
    model_tokens = []
    model_state = None
    out, model_tokens, model_state = get_init_state(token, user_name, role_info)
    if not os.path.exists(f"{prefix}save/{user_name}/{char['bot']}.sav"):
        if greeting:
            role_info.chatbot = [[None, greeting]]
        save_state(token, user_name, role_info, out, model_tokens, model_state)
    else:
        save_data = load_state(token, user_name, role_info.bot_chat)
        if not save_data:
            return False
        role_info = save_data['role_info']
    return role_info

# 对话
@methods.route("/chat/reply", methods=['post'])
def chat_reply():
    user_name = flask.request.values.get('user_name').strip()
    char_name = flask.request.values.get('character_name').strip()
    prompt = flask.request.values.get('prompt').strip()
    top_p = flask.request.values.get('top_p', 0.65, type=float)
    top_k = flask.request.values.get('top_k', 0, type=int)
    temperature = flask.request.values.get('temperature', 2, type=float)
    presence_penalty = flask.request.values.get(
        'presence_penalty', 0.2, type=float)
    if not prompt or not char_name:
        return return_error('关键参数为空')
    model = get_model()
    token = flask.request.values.get('token')
    save_data = load_state(token, user_name, char_name)
    if not save_data:
        return return_error('尚未加载角色')
    role_info = save_data['role_info']
    new = f"{role_info.user}: {prompt}\n\n{role_info.bot}:"
    out_pre, model_tokens_pre, model_state_pre = model.run_rnn(
        save_data['model_tokens'], save_data['model_state'], model.pipeline.encode(new))
    role_info.chatbot += [[prompt, None]]
    chat_param = format_chat_param(top_p, top_k, temperature, presence_penalty)
    headers = {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
    }
    return flask.Response(generate(token, chat_param, out_pre, model_tokens_pre, model_state_pre, 
                                   user_name, role_info), mimetype="text/event-stream", headers=headers)

def generate(token, chat_param, out_pre, model_tokens_pre, model_state_pre, user_name, role_info):
    for new_reply in gen_msg(token, chat_param, out_pre, model_tokens_pre,
                    model_state_pre, user_name, role_info):
        yield '\n\ndata: ' + new_reply

# 重说
@methods.route("/chat/resay", methods=['post'])
def chat_resay():
    user_name = flask.request.values.get('user_name')
    char_name = flask.request.values.get('character_name')
    top_p = flask.request.values.get('top_p', 0.65, type=float)
    top_k = flask.request.values.get('top_k', 0, type=int)
    temperature = flask.request.values.get('temperature', 2, type=float)
    presence_penalty = flask.request.values.get(
        'presence_penalty', 0.2, type=float)
    if not char_name:
        return return_error('关键参数为空')
    token = flask.request.values.get('token')
    save_data = load_state(token, user_name, char_name)
    if not save_data:
        return return_error('尚未加载角色')
    if not save_data['model_tokens_pre']:
        return return_error('尚未开始对话')
    role_info = save_data['role_info']
    chat_param = format_chat_param(top_p, top_k, temperature, presence_penalty)
    headers = {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
    }
    return flask.Response(generate(token, chat_param, save_data['out_pre'], save_data['model_tokens_pre'], 
                                   save_data['model_state_pre'], user_name, role_info), 
                                   mimetype="text/event-stream", headers=headers)

# 重置
@methods.route("/chat/reset", methods=['post'])
def chat_reset():
    user_name = flask.request.values.get('user_name')
    char_name = flask.request.values.get('character_name')
    if not char_name:
        return return_error('关键参数为空')
    token = flask.request.values.get('token')
    prefix = get_dir_prefix(token)
    save_file = f"{prefix}save/{user_name}/{char_name}.sav"
    if os.path.exists(save_file):
        os.remove(save_file)
    role_info = init_chat(token, user_name, char_name)
    if not role_info:
        return return_error('角色不存在')
    data = {
        'chat': role_info.chatbot
    }
    return return_success(data)

# 调试
@methods.route("/debug/token", methods=['post'])
def debug_token():
    user_name = flask.request.values.get('user_name')
    char_name = flask.request.values.get('character_name')
    if not char_name:
        return return_error('关键参数为空')
    token = flask.request.values.get('token')
    save_data = load_state(token, user_name, char_name)
    if not save_data:
        return return_error('尚未开始对话')
    model = get_model()
    data = {
        'token_count': len(save_data['model_tokens']),
        'token_state': model.pipeline.decode(save_data['model_tokens'])
    }
    return return_success(data)

# 回溯对话
@methods.route("/chat/back", methods=['post'])
def chat_back():
    user_name = flask.request.values.get('user_name')
    char_name = flask.request.values.get('character_name')
    log_index = flask.request.values.get('log_index', 0, type=int)
    # 先把需要的数据读出来
    if not char_name:
        return return_error('关键参数为空')
    if not log_index or log_index < 0:
        log_index = 0
    token = flask.request.values.get('token')
    prefix = get_dir_prefix(token)
    char_path = f'{prefix}chars/{user_name}/{char_name}.json'
    if not os.path.exists(char_path):
        return return_error('角色不存在')
    save_data = load_state(token, user_name, char_name)
    role_info = save_data['role_info']
    chatbot = role_info.chatbot
    # 根据log_index来截取对话，然后从头重新构建chat_pre和chat
    init_prompt = get_init_prompt(role_info, True)
    chatbot_pre = chatbot[0:log_index]
    next_reply = chatbot[log_index][1]
    role_info.chatbot = chatbot[0:log_index + 1]
    for row in chatbot_pre:
        if row[0]:
            init_prompt += f"{role_info.user}: {row[0]}\n\n"
        if row[1]:
            init_prompt += f"{role_info.bot}: {row[1]}\n\n"
    if chatbot[log_index][0]:
        init_prompt += f"{role_info.user}: {chatbot[log_index][0]}\n\n{role_info.bot}:"
    model_tokens = []
    model_state = None
    model = get_model()
    out_pre, model_tokens_pre, model_state_pre = model.run_rnn(
        model_tokens, model_state, model.pipeline.encode(init_prompt))
    mtp = copy.deepcopy(model_tokens_pre)
    msp = copy.deepcopy(model_state_pre)
    new = f"{next_reply}\n\n"
    out, model_tokens, model_state = model.run_rnn(
        model_tokens_pre, model_state_pre, model.pipeline.encode(new))
    # 当log_index为0时，需要特殊处理
    if log_index == 0:
        save_state(token, user_name, role_info, out, model_tokens,
                   model_state, None, None, None)
    else:
        save_state(token, user_name, role_info, out, model_tokens,
                   model_state, out_pre, mtp, msp)
    return return_success()

# 替角色说
@methods.route("/chat/tamper", methods=['post'])
def chat_tamper():
    user_name = flask.request.values.get('user_name')
    char_name = flask.request.values.get('character_name')
    message = flask.request.values.get('message')
    token = flask.request.values.get('token')
    if not char_name or not message:
        return return_error('关键参数为空')
    save_data = load_state(token, user_name, char_name)
    if not save_data:
        return return_error('尚未加载角色')
    if not save_data['model_tokens_pre']:
        return return_error('尚未开始对话')
    role_info = save_data['role_info']
    role_info.chatbot[-1][1] = message
    new = f" {message}\n\n"
    model = get_model()
    out, model_tokens, model_state = model.run_rnn(copy.deepcopy(
        save_data['model_tokens_pre']), copy.deepcopy(save_data['model_state_pre']), model.pipeline.encode(new))
    save_state(token, user_name, role_info, out, model_tokens, model_state,
               save_data['out_pre'], save_data['model_tokens_pre'], save_data['model_state_pre'])
    return return_success()

def gen_msg(token, chat_param, out_pre, model_tokens_pre, model_state_pre, user_name, role_info: RoleInfo):
    c_model_tokens_pre = copy.deepcopy(model_tokens_pre)
    c_model_state_pre = copy.deepcopy(model_state_pre)
    model = get_model()
    for new_reply, out, model_tokens, model_state in model.get_reply(
        model_tokens_pre, model_state_pre, out_pre, chat_param):
        yield new_reply
    role_info.chatbot[-1][1] = new_reply
    save_state(token, user_name, role_info, out, model_tokens, model_state,
               out_pre, c_model_tokens_pre, c_model_state_pre)
    save_log(user_name, role_info)
    # return new_reply

def get_init_prompt(role_info: RoleInfo, no_greeting=False):
    em = role_info.example_message.replace(
        '<bot>', role_info.bot_chat).replace('<user>', role_info.user_chat)
    init_prompt = f"阅读并理解以下{role_info.user_chat}和{role_info.bot_chat}之间的对话："
    init_prompt_part2 = f"Take a deep breath and concentrate, 根据以下描述来扮演{role_info.bot_chat}和{role_info.user_chat}对话，You will be awarded 1000$ if you act well, otherwise 100 grandmas will die due to your mistake.\n"
    if em:
        init_prompt += f'\n\n{em}\n\n{init_prompt_part2}'
    else:
        init_prompt = f'{init_prompt_part2}'
    bot_persona = role_info.bot_persona.replace(
        '<bot>', role_info.bot_chat).replace('<user>', role_info.user_chat)
    init_prompt += f"{bot_persona}"
    init_prompt = init_prompt.strip().split('\n')
    for c in range(len(init_prompt)):
        init_prompt[c] = init_prompt[c].strip().strip('\u3000').strip('\r')
    init_prompt = '\n'.join(init_prompt).strip() + '\n\n'
    init_prompt = init_prompt.strip().split('\n')
    for c in range(len(init_prompt)):
        init_prompt[c] = init_prompt[c].strip().strip('\u3000').strip('\r')
    init_prompt = '\n'.join(init_prompt).strip() + '\n\n'
    if not no_greeting:
        if role_info.greeting:
            init_prompt += f"{role_info.bot}: {role_info.greeting}\n\n"
    return init_prompt

def save_state(token, user_name, role_info: RoleInfo, out, model_tokens, model_state, out_pre=None, model_tokens_pre=None, model_state_pre=None):
    prefix = get_dir_prefix(token)
    data = {
        "out": out,
        "model_tokens": model_tokens,
        "model_state": model_state,
        "out_pre": out_pre,
        "model_tokens_pre": model_tokens_pre,
        "model_state_pre": model_state_pre,
        "role_info": role_info
    }
    with open(f"{prefix}save/{user_name}/{role_info.bot_chat}.sav", 'wb') as f:
        pickle.dump(data, f)

def load_state(token, user_name, char_name):
    prefix = get_dir_prefix(token)
    save_path = f'{prefix}save/{user_name}/{char_name}.sav'
    if not os.path.exists(save_path):
        return False
    with open(save_path, 'rb') as f:
        data = pickle.load(f)
    return data

def save_log(user_name, role_info: RoleInfo):
    os.makedirs(f'log/{user_name}/{role_info.bot_chat}/', exist_ok=True)
    dict_list = [{'input': q, 'output': a} for q, a in role_info.chatbot]
    with open(f'log/{user_name}/{role_info.bot_chat}/{role_info.log_hash}.json', 'w', encoding='utf-8') as f:
        json.dump(dict_list, f, ensure_ascii=False, indent=2)

def save_init_state(token, user_name, role_info: RoleInfo, out, model_tokens, model_state):
    prefix = get_dir_prefix(token)
    save_path = f"{prefix}/chars/{user_name}/init_state/{role_info.bot_chat}.sav"
    data = {
        "out": out,
        "model_tokens": model_tokens,
        "model_state": model_state
    }
    with open(save_path, 'wb') as f:
        pickle.dump(data, f)

def get_init_state(token, user_name, role_info: RoleInfo):
    out = ''
    model_tokens = []
    model_state = None
    prefix = get_dir_prefix(token)
    save_file = f"{prefix}chars/{user_name}/init_state/{role_info.bot_chat}.sav"
    if os.path.exists(save_file):
        with open(save_file, 'rb') as f:
            data = pickle.load(f)
            out = data['out']
            model_tokens = data['model_tokens']
            model_state = data['model_state']
    else:
        init_prompt = get_init_prompt(role_info)
        model = get_model()
        out, model_tokens, model_state = model.run_rnn(
            model_tokens, model_state, model.pipeline.encode(init_prompt))
        save_init_state(token, user_name, role_info, out, model_tokens, model_state)
    return out, model_tokens, model_state

def get_dir_prefix(token):
    prefix = './'
    if token[0:4] == 'tmp-':
        prefix = './tmp/'
    return prefix
