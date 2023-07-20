import flask
import os
from modules.common import return_error, return_success, model
import json
import pickle
from modules.role_info import RoleInfo
import uuid, copy

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
  bot_save_name = flask.request.values.get('bot_save_name')
  user = flask.request.values.get('user')
  bot = flask.request.values.get('bot')
  action_start = flask.request.values.get('action_start')
  action_end = flask.request.values.get('action_end')
  greeting = flask.request.values.get('greeting')
  bot_persona = flask.request.values.get('bot_persona')
  example_message = flask.request.values.get('example_message')
  use_qa = flask.request.values.get('use_qa', False)
  avatar = flask.request.values.get('avatar')
  if not user or not bot or not greeting or not bot_persona:
    return return_error('缺少关键参数')
  bot_name = bot if not bot_save_name else bot_save_name
  with open(f"./chars/{user_name}/{bot_name}.json", 'w', encoding='utf8') as f:
    if not use_qa or use_qa.lower() == 'false':
      use_qa = False
    else:
      use_qa = True
    data = {
      'user': user, 
      'bot': bot, 
      'action_start': action_start,
      'action_end': action_end,
      'greeting': greeting, 
      'bot_persona': bot_persona,
      'example_message': example_message,
      'use_qa': use_qa,
      'avatar': avatar
    }
    json.dump(data, f, indent=2, ensure_ascii=False)
  return return_success()

# 删除角色
@methods.route("/characters/del", methods=['post'])
def characters_delete():
  user_name = flask.request.values.get('user_name')
  char_name = flask.request.values.get('character_name')
  if not user_name or not char_name:
    return return_error('缺少关键参数')
  json_path = f"chars/{user_name}/{char_name}.json"
  pic_path = f"chars/{user_name}/{char_name}.png"
  sav_path = f"save/{user_name}/{char_name}.sav"
  if os.path.exists(json_path):
    os.remove(json_path)
  if os.path.exists(pic_path):
    os.remove(pic_path)
  if os.path.exists(sav_path):
    os.remove(sav_path)
  return return_success()

# 加载角色
@methods.route("/characters/load", methods=['post'])
def characters_load():
  user_name = flask.request.values.get('user_name')
  char_name = flask.request.values.get('character_name')
  if not char_name:
    return return_error('关键参数为空')
  role_info = init_chat(user_name, char_name)
  data = {
    'chat': role_info.chatbot
  }
  return return_success(data)

def init_chat(user_name, char_name):
  char_path = f'./chars/{user_name}/{char_name}.json'
  if not os.path.exists(char_path):
    return return_error('角色不存在')
  with open(char_path, 'r', encoding='utf-8') as f:
    char = json.loads(f.read())
  role_info = RoleInfo([], char['user'], char['bot'], char['action_start'], char['action_end'], 
                       char['greeting'], char['use_qa'], str(uuid.uuid1()).replace('-', ''))
  greeting = char['greeting']
  model_tokens = []
  model_state = None
  init_prompt = get_init_prompt(role_info, char['bot'], char['bot_persona'], char['user'], char['example_message'])
  init_prompt = init_prompt.strip().split('\n')
  for c in range(len(init_prompt)):
    init_prompt[c] = init_prompt[c].strip().strip('\u3000').strip('\r')
  init_prompt = '\n'.join(init_prompt).strip() + '\n\n'
  init_prompt = init_prompt.strip().split('\n')
  for c in range(len(init_prompt)):
    init_prompt[c] = init_prompt[c].strip().strip('\u3000').strip('\r')
  init_prompt = '\n'.join(init_prompt).strip() + '\n\n'
  if greeting:
    init_prompt += f"{role_info.bot}: {greeting}\n\n"
    role_info.chatbot = [[None, greeting]]
  if not os.path.exists(f"save/{user_name}/{char['bot']}.sav"):
    out, model_tokens, model_state = model.run_rnn(model_tokens, model_state, model.pipeline.encode(init_prompt))
    save_state(user_name, role_info, out, model_tokens, model_state)
  else:
    save_data = load_state(user_name, role_info.bot)
    role_info = save_data['role_info']
  return role_info

# 对话
@methods.route("/chat/reply", methods=['post'])
def chat_reply():
  user_name = flask.request.values.get('user_name')
  char_name = flask.request.values.get('character_name')
  prompt = flask.request.values.get('prompt')
  min_len = flask.request.values.get('min_len', 0)
  top_p = flask.request.values.get('top_p', 0.65)
  temperature = flask.request.values.get('temperature', 2)
  presence_penalty = flask.request.values.get('presence_penalty', 0.2)
  frequency_penalty = flask.request.values.get('frequency_penalty', 0.2)
  if not user_name or not prompt or not char_name:
    return return_error('关键参数为空')
  save_data = load_state(user_name, char_name)
  if not save_data:
    return return_error('尚未加载角色')
  role_info = save_data['role_info']
  new = f"{role_info.user}: {prompt}\n\n{role_info.bot}:"
  out_pre, model_tokens_pre, model_state_pre = model.run_rnn(save_data['model_tokens'], save_data['model_state'], model.pipeline.encode(new))
  role_info.chatbot += [[prompt, None]]
  chat_param = model.format_chat_param(top_p, temperature, presence_penalty, frequency_penalty,
                                       min_len, role_info.action_start_token, role_info.action_end_token)
  occurrence = get_occurrence(role_info)
  new_reply = gen_msg(chat_param, out_pre, model_tokens_pre, model_state_pre, user_name, role_info, occurrence)
  data = {
    'reply': new_reply
  }
  return return_success(data)

# 重说
@methods.route("/chat/resay", methods=['post'])
def chat_resay():
  user_name = flask.request.values.get('user_name')
  char_name = flask.request.values.get('character_name')
  min_len = flask.request.values.get('min_len', 0)
  top_p = flask.request.values.get('top_p', 0.65)
  temperature = flask.request.values.get('temperature', 2)
  presence_penalty = flask.request.values.get('presence_penalty', 0.2)
  frequency_penalty = flask.request.values.get('frequency_penalty', 0.2)
  save_data = load_state(user_name, char_name)
  if not save_data:
    return return_error('尚未加载角色')
  if not save_data['model_tokens_pre']:
    return return_error('尚未开始对话')
  role_info = save_data['role_info']
  chat_param = model.format_chat_param(top_p, temperature, presence_penalty, frequency_penalty,
                                       min_len, role_info.action_start_token, role_info.action_end_token)
  occurrence = get_occurrence(role_info, True)
  new_reply = gen_msg(chat_param, save_data['out_pre'], save_data['model_tokens_pre'], save_data['model_state_pre'], user_name, role_info, occurrence) 
  data = {
    'reply': new_reply
  }
  return return_success(data)

# 重置
@methods.route("/chat/reset", methods=['post'])
def chat_reset():
  user_name = flask.request.values.get('user_name')
  char_name = flask.request.values.get('character_name')
  save_file = f"save/{user_name}/{char_name}.sav"
  if os.path.exists(save_file):
    os.remove(save_file)
  role_info = init_chat(user_name, char_name)
  data = {
    'chat': role_info.chatbot
  }
  return return_success(data)

# 调试
@methods.route("/debug/token", methods=['post'])
def debug_token():
  user_name = flask.request.values.get('user_name')
  char_name = flask.request.values.get('character_name')
  save_data = load_state(user_name, char_name)
  if not save_data:
    return return_error('尚未开始对话')
  data = {
    'token_count': len(save_data['model_tokens']),
    'token_state': model.pipeline.decode(save_data['model_tokens'])
  }
  return return_success(data)

def gen_msg(chat_param, out_pre, model_tokens_pre, model_state_pre, user_name, role_info:RoleInfo, occurrence):
  c_model_tokens_pre = copy.deepcopy(model_tokens_pre)
  c_model_state_pre = copy.deepcopy(model_state_pre)
  new_reply, out, model_tokens, model_state = model.get_reply(model_tokens_pre, model_state_pre, out_pre, chat_param, occurrence)
  role_info.chatbot[-1][1] = new_reply
  save_state(user_name, role_info, out, model_tokens, model_state, out_pre, c_model_tokens_pre, c_model_state_pre)
  save_log(user_name, role_info)
  return new_reply

def get_init_prompt(role_info:RoleInfo, bot:str, bot_persona:str, user:str, example_message:str):
  if role_info.action_start and role_info.action_start in example_message and role_info.action_end in example_message:
    role_info.action_start_token = model.pipeline.encode(f' {role_info.action_start}')
    role_info.action_end_token = model.pipeline.encode(role_info.action_end)
  else:
    role_info.action_start_token = None
    role_info.action_end_token = None
  em = example_message.replace('<bot>', bot).replace('<user>', user)
  init_prompt = f"阅读并理解以下{user}和{bot}之间的对话："
  init_prompt_part2 = f"根据以下描述来扮演{bot}和{user}对话，在对话中加入描述角色的感情、想法、身体动作等内容，也可以加入对环境、场面或动作产生结果的描述，以此来促进对话的进展，这些描述要合理且文采斐然。\n"
  if em:
    init_prompt += f'\n\n{em}\n\n{init_prompt_part2}'
  else:
    init_prompt = f'{init_prompt_part2}'
  init_prompt += f"{bot_persona}"
  return init_prompt

def save_state(user_name, role_info:RoleInfo, out, model_tokens, model_state, out_pre=None, model_tokens_pre=None, model_state_pre=None):
  os.makedirs(f'save/{user_name}', exist_ok=True)
  data = {
    "out": out,
    "model_tokens": model_tokens,
    "model_state": model_state,
    "out_pre": out_pre,
    "model_tokens_pre": model_tokens_pre,
    "model_state_pre": model_state_pre,
    "role_info": role_info
  }
  with open(f"save/{user_name}/{role_info.bot_chat}.sav", 'wb') as f:
    pickle.dump(data, f)

def load_state(user_name, char_name):
  if not os.path.exists(f'save/{user_name}/{char_name}.sav'):
    return False
  with open(f'save/{user_name}/{char_name}.sav', 'rb') as f:
    data = pickle.load(f)
  return data

def get_occurrence(role_info:RoleInfo, is_pre=False):
  chatbot = role_info.chatbot
  if len(chatbot) > 3:
    chatbot = chatbot[-3:]
  if is_pre:
    chatbot = chatbot[:-1]
  occurrence = {}
  for i in chatbot:
    if i[1]:
      bot_token = model.pipeline.encode(i[1])
      for t in bot_token:
        for o in occurrence:
          occurrence[o] *= model.penalty_decay
        occurrence[t] = 1 + (occurrence[t] if t in occurrence else 0)
  return occurrence

def save_log(user_name, role_info:RoleInfo):
  os.makedirs(f'log/{user_name}/{role_info.bot_chat}/', exist_ok=True)
  dict_list = [{'input': q, 'output': a} for q, a in role_info.chatbot]
  with open(f'log/{user_name}/{role_info.bot_chat}/{role_info.log_hash}.json', 'w', encoding='utf-8') as f:
    json.dump(dict_list, f, ensure_ascii=False, indent=2)