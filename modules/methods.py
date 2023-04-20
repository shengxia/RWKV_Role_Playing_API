import flask
import os
from modules.common import return_error, return_success, model
import json
import pickle

methods = flask.Blueprint('methods', __name__)

@methods.before_request
def before():
  user_name = flask.request.values.get('user_name')
  token = flask.request.values.get('token')
  if not user_name or not token:
    return return_error('关键参数为空')
  user_cache = f'./cache/{user_name}'
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
  path = f'./chars/{user_name}/'
  files=os.listdir(path)
  file_list = []
  for f in files:
    file_name_arr = f.split('.')
    if file_name_arr[-1] == 'json':
      file_list.append(file_name_arr[0])
  data = {
    'list': file_list
  }
  return return_success(data)

# 获取角色详情
@methods.route("/characters/get", methods=['post'])
def characters_get():
  user_name = flask.request.values.get('user_name')
  character_name = flask.request.values.get('character_name')
  if not character_name:
    return return_error('缺少关键参数')
  character_path = f'./chars/{user_name}/{character_name}.json'
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
  if not user or not bot or not greeting or not bot_persona:
    return return_error('缺少关键参数')
  with open(f"./chars/{user_name}/{bot}.json", 'w', encoding='utf8') as f:
    data = {
      'user': user, 
      'bot': bot, 
      'greeting': greeting, 
      'bot_persona': bot_persona
    }
    json.dump(data, f, indent=2, ensure_ascii=False)
  return return_success()

# 加载角色
@methods.route("/characters/load", methods=['post'])
def characters_load():
  user_name = flask.request.values.get('user_name')
  char_name = flask.request.values.get('char_name')
  if not char_name:
    return return_error('关键参数为空')
  char_path = f'./chars/{user_name}/{char_name}.json'
  if not os.path.exists(char_path):
    return return_error('角色不存在')
  with open(char_path, 'r', encoding='utf-8') as f:
    char = json.loads(f.read())
  user = char['user']
  bot = char['bot']
  bot_persona = char['bot_persona']
  greeting = char['greeting']
  model_tokens = []
  model_state = None
  init_prompt = f"{user}: 你是{bot}，{bot_persona}，{bot}称呼我为{user}。\n\n"
  if greeting:
    init_prompt += f"{bot}: {greeting}\n\n{user}:"
  init_prompt = init_prompt.strip().split('\n')
  for c in range(len(init_prompt)):
    init_prompt[c] = init_prompt[c].strip().strip('\u3000').strip('\r')
  init_prompt = '\n'.join(init_prompt).strip()
  out, model_tokens, model_state = model.run_rnn(model_tokens, model_state, model.pipeline.encode(init_prompt))
  model.save_all_stat(user_name, 'chat_init', out, model_tokens, model_state, char)
  if os.path.exists(f'save/{user_name}/{bot}.sav'):
    save_data = load_chat(user_name, bot)
    model.save_all_stat(user_name, 'chat', save_data['out'], save_data['model_tokens'], save_data['model_state'], save_data['role_info'])
    model.save_all_stat(user_name, 'chat_pre', save_data['out_pre'], save_data['model_tokens_pre'], save_data['model_state_pre'], save_data['role_info'])
  else:
    model.save_all_stat(user_name, 'chat', out, model_tokens, model_state, char)
  data = {
    'reply': greeting
  }
  return return_success(data)

# 对话
@methods.route("/chat/reply", methods=['post'])
def chat_reply():
  user_name = flask.request.values.get('user_name')
  prompt = flask.request.values.get('prompt')
  top_p = flask.request.values.get('top_p', 0.6)
  top_k = flask.request.values.get('top_k', 0)
  temperature = flask.request.values.get('temperature', 1.5)
  presence_penalty = flask.request.values.get('presence_penalty', 0.2)
  frequency_penalty = flask.request.values.get('frequency_penalty', 0.2)
  if not prompt:
    return return_error('关键参数为空')
  try:
    out, model_tokens, model_state, role_info = model.load_all_stat(user_name, 'chat')
  except:
    return return_error('尚未加载角色')
  model.save_all_stat(user_name, 'chat_pre', out, model_tokens, model_state, role_info)
  new = f" {prompt}\n\n{role_info['bot']}:"
  out, model_tokens, model_state = model.run_rnn(model_tokens, model_state, model.pipeline.encode(new))
  chat_param = model.format_chat_param(top_p, top_k, temperature, presence_penalty, frequency_penalty)
  new_reply = gen_msg(out, chat_param, model_tokens, model_state, user_name, role_info)
  data = {
    'reply': new_reply
  }
  return return_success(data)

# 重说
@methods.route("/chat/resay", methods=['post'])
def chat_resay():
  user_name = flask.request.values.get('user_name')
  top_p = flask.request.values.get('top_p', 0.6)
  top_k = flask.request.values.get('top_k', 0)
  temperature = flask.request.values.get('temperature', 1.5)
  presence_penalty = flask.request.values.get('presence_penalty', 0.2)
  frequency_penalty = flask.request.values.get('frequency_penalty', 0.2)
  try:
    out, model_tokens, model_state, role_info = model.load_all_stat(user_name, 'chat_pre')
  except:
    return return_error('尚未开始对话')
  chat_param = model.format_chat_param(top_p, top_k, temperature, presence_penalty, frequency_penalty)
  new_reply = gen_msg(out, chat_param, model_tokens, model_state, user_name, role_info) 
  data = {
    'reply': new_reply
  }
  return return_success(data)

# 重置
@methods.route("/chat/reset", methods=['post'])
def chat_reset():
  user_name = flask.request.values.get('user_name')
  out, model_tokens, model_state, role_info = model.load_all_stat(user_name, 'chat_init')
  model.save_all_stat(user_name, 'chat', out, model_tokens, model_state, role_info)
  save_file = f"save/{user_name}/{role_info['bot']}.sav"
  if os.path.exists(save_file):
    os.remove(save_file)
  data = {
    'reply': role_info['greeting']
  }
  return return_success(data)

@methods.route("/debug/token", methods=['post'])
def debug_token():
  user_name = flask.request.values.get('user_name')
  state = model.load_all_stat(user_name, 'chat')
  data = {
    'token_state': state[0]
  }
  return return_success(data)

def gen_msg(out, chat_param, model_tokens, model_state, user_name, role_info):
  new_reply, out, model_tokens, model_state = model.get_reply(model_tokens, model_state, out, chat_param, role_info['user'])
  model.save_all_stat(user_name, 'chat', out, model_tokens, model_state, role_info)
  save_chat(user_name)
  return new_reply

def save_chat(user_name):
  os.makedirs(f'save/{user_name}', exist_ok=True)
  out, model_tokens, model_state, role_info = model.load_all_stat(user_name, 'chat')
  out_pre, model_tokens_pre, model_state_pre, role_info_pre = model.load_all_stat(user_name, 'chat_pre')
  data = {
    "out": out,
    "model_tokens": model_tokens,
    "model_state": model_state,
    "out_pre": out_pre,
    "model_tokens_pre": model_tokens_pre,
    "model_state_pre": model_state_pre,
    "role_info": role_info
  }
  with open(f"save/{user_name}/{role_info_pre['bot']}.sav", 'wb') as f:
    pickle.dump(data, f)

def load_chat(user_name, bot):
  with open(f'save/{user_name}/{bot}.sav', 'rb') as f:
    data = pickle.load(f)
  return data