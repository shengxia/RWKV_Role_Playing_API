## 一个基于Flask实现的RWKV角色扮演API

因为这个项目引入了用户的概念，所以可以支持多用户，我把生成的状态保存在了硬盘上，这样应该是可以及时释放内存和显存，不至于人一多就爆显存了吧……

有个简单的前端演示项目

https://github.com/shengxia/RWKV_Role_Playing_UI

感兴趣的话可以看看，使用Vue.js和Mint-UI做的。可以把这个UI项目的Release里面下载已经打包好的版本，然后把解压缩后的文件扔到API项目里的ui文件夹里面，双击里面的start_ui.bat，这样就可以通过访问 http://127.0.0.1:9000 来使用该项目了（前提是这个项目已经启动了）。

### 安装方法：

先安装依赖
```
pip install torch==1.13.1 --extra-index-url https://download.pytorch.org/whl/cu117 --upgrade

pip install -r requirements.txt
```

启动：
```
python api.py --listen --model model/path
```

以下是一个例子: 
```
python api.py --listen --model model/RWKV-4-World-CHNtuned-3B-v1-20230625-ctx4096
```
各种启动参数解释如下：

| 参数 | 解释 |
| --- | --- |
| --port | api的端口 |
| --model | 要加载的模型路径 |
| --strategy | 模型加载的策略 |
| --cuda_on | 控制RWKV_CUDA_ON这个环境变量的，0-禁用，1-启用 |

模型的加载方式（--strategy）我默认使用的是"cuda fp16i8"，如果想使用其他的加载方式可以自行调整该参数，具体有哪些值可以参考[这个文章](https://zhuanlan.zhihu.com/p/609154637)或者这张图![图片](./pic/4.jpg)

----------

### 1.用户登陆
>描述：想新增用户的话，可以在user目录下面新建一个以用户名命名的文件，没有扩展名，然后里面存放密码。

***URL***

`/login`

***Method***

`POST`

***Param***

|参数|必须|说明|取值|
|:--:|:--:|:--:|:--:|
| user_name | 是 | 用户名 | String |
| password | 是 | 密码 | String |

***Return Example***

```json
{
  "data": {
    "user_name": "sbin",
    "token": "87531baddff511ed8df938d547b88377"
  },
  "message": "success",
  "code": 200
}
```

***Code***

|状态码|说明|
|:--:|:--:|
|200|请求成功|
|400|错误|

### 2.获取角色列表

***URL***

`/characters/list`

***Method***

`POST`

***Param***

|参数|必须|说明|取值|
|:--:|:--:|:--:|:--:|
| user_name | 是 | 用户名 | String |
| token | 是 | 令牌，从登录接口中获取 | String |

***Return Example***

```json
{
  "data": {
    "list": ["小红"]
  },
  "message": "success",
  "code": 200
}
```

***Code***

|状态码|说明|
|:--:|:--:|
|200|请求成功|
|400|错误|

### 3.获取角色详情

***URL***

`/characters/get`

***Method***

`POST`

***Param***

|参数|必须|说明|取值|
|:--:|:--:|:--:|:--:|
| user_name | 是 | 用户名 | String |
| token | 是 | 令牌，从登录接口中获取 | String |
| character_name | 是 | 角色名称 | String |

***Return Example***

```json
{
	"data": {
		"user": "哥哥",
		"bot": "小雪",
		"action_start": "{",
		"action_end": "}",
		"greeting": "{看到你走了过来，欢快的向你跑了过来}哥哥，来和我聊聊天吧。",
		"bot_persona": "你扮演小雪，是一个调皮可爱，美丽性感的女孩，是我的邻居。",
		"example_message": "<user>: 我们来聊聊天吧。\n\n<bot>: {点了点头，微笑着看着你}好啊，<user>，我们聊点什么呢？\n\n<user>: 聊一些关于你的话题吧。\n\n<bot>: {心里非常高兴，但表面上还是保持着微笑}关于我的话题？<user>~你想要知道我的哪些事情呢？\n\n<user>:  我想知道你喜欢的人是谁。\n\n<bot>: {稍微愣了一下，随即露出了甜美的笑容}<user>~你问这个问题是不是很奇怪呀，你已经知道我喜欢的人是谁了。\n\n<user>:  是吗？我怎么不知道呢？\n\n<bot>: {心里有些失望，但仍然微笑着看着你}那好吧，我的答案是：我喜欢的人就是<user>啊，你虽然不像别人那样能力很强，但是却有着一颗温柔而善良的心，而且非常关心我。",
		"use_qa": false,
    "avatar": ""
	},
	"message": "success",
	"code": 200
}
```

***Code***

|状态码|说明|
|:--:|:--:|
|200|请求成功|
|400|错误|

### 4.创建/保存角色

***URL***

`/characters/save`

***Method***

`POST`

***Param***

|参数|必须|说明|取值|
|:--:|:--:|:--:|:--:|
| user_name | 是 | 用户名 | String |
| bot | 是 | 角色名称 | String |  
| user | 是 | 角色如何称呼用户 | String |
| action_start | 否 | 旁白开始符号 | String |
| action_end | 否 | 旁白结束符号 | String |
| greeting | 是 | 角色的开场白 | String |
| bot_persona | 是 | 角色的性格 | String |
| example_message | 否 | 示例对话 | String |
| use_qa | 否 | 是否使用User和Assistant代替你和角色的名字，默认为否(False)，但是建议在使用的时候，如果想设置为否，直接传空字符串 | Boolen |
| avatar | 否 | 角色形象，图片经过base64编码后的字符串 | String |
| token | 是 | 令牌，从登录接口中获取 | String |

***Return Example***

```json
{
  "data": null,
  "message": "success",
  "code": 200
}
```

***Code***

|状态码|说明|
|:--:|:--:|
|200|请求成功|
|400|错误|

### 5.删除角色

***URL***

`/characters/del`

***Method***

`POST`

***Param***

|参数|必须|说明|取值|
|:--:|:--:|:--:|:--:|
| user_name | 是 | 用户名 | String |
| character_name | 否 | 角色保存名称 | String |
| token | 是 | 令牌，从登录接口中获取 | String |

***Return Example***

```json
{
  "data": null,
  "message": "success",
  "code": 200
}
```

***Code***

|状态码|说明|
|:--:|:--:|
|200|请求成功|
|400|错误|

### 6.加载角色

***URL***

`/characters/load`

***Method***

`POST`

***Param***

|参数|必须|说明|取值|
|:--:|:--:|:--:|:--:|
| user_name | 是 | 用户名 | String |
| character_name | 是 | 角色名称 | String |  
| token | 是 | 令牌，从登录接口中获取 | String |

***Return Example***

```json
{
	"data": {
		"chat": [
			[null, "{看到你走了过来，欢快的向你跑了过来}哥哥，来和我聊聊天吧。"]
		]
	},
	"message": "success",
	"code": 200
}
```

***Code***

|状态码|说明|
|:--:|:--:|
|200|请求成功|
|400|错误|

### 7.对话

***URL***

`/chat/reply`

***Method***

`POST`

***Param***

|参数|必须|说明|取值|
|:--:|:--:|:--:|:--:|
| user_name | 是 | 用户名 | String |
| character_name | 是 | 角色名称 | String |
| prompt | 是 | 用户输入的内容 | String |  
| min_len | 否 | 最小回复长度，0为不控制，默认是0 | Number |  
| top_p | 否 | top_p值，默认为0.65 | Number |  
| temperature | 否 | temperature值，默认为2 | Number |  
| presence_penalty | 否 | presence_penalty值，默认为0.2 | Number |  
| frequency_penalty | 否 | frequency_penalty值，默认为0.2 | Number |  
| token | 是 | 令牌，从登录接口中获取 | String |

***Return Example***

```json
{
  "data": {
    "reply": "我有个好玩的想法，我们一起去参加一场冒险吧。"
  },
  "message": "success",
  "code": 200
}
```

***Code***

|状态码|说明|
|:--:|:--:|
|200|请求成功|
|400|错误|

### 8.重说

***URL***

`/chat/resay`

***Method***

`POST`

***Param***

|参数|必须|说明|取值|
|:--:|:--:|:--:|:--:|
| user_name | 是 | 用户名 | String |
| character_name | 是 | 角色名称 | String |
| min_len | 否 | 最小回复长度，0为不控制，默认是0 | Number |  
| top_p | 否 | top_p值，默认为0.6 | Number |  
| temperature | 否 | temperature值，默认为1.8 | Number |  
| presence_penalty | 否 | presence_penalty值，默认为0.2 | Number |  
| frequency_penalty | 否 | frequency_penalty值，默认为0.2 | Number |  
| token | 是 | 令牌，从登录接口中获取 | String |

***Return Example***

```json
{
  "data": {
    "reply": "小蓝，你有没有听说过那个网络红人？"
  },
  "message": "success",
  "code": 200
}
```

***Code***

|状态码|说明|
|:--:|:--:|
|200|请求成功|
|400|错误|

### 9.重置

***URL***

`/chat/reset`

***Method***

`POST`

***Param***

|参数|必须|说明|取值|
|:--:|:--:|:--:|:--:|
| user_name | 是 | 用户名 | String |
| character_name | 是 | 角色名称 | String |
| token | 是 | 令牌，从登录接口中获取 | String |

***Return Example***

```json
{
	"data": {
		"chat": [
			[null, "{看到你走了过来，欢快的向你跑了过来}哥哥，来和我聊聊天吧。"]
		]
	},
	"message": "success",
	"code": 200
}
```

***Code***

|状态码|说明|
|:--:|:--:|
|200|请求成功|
|400|错误|

### 9.调试

***URL***

`/debug/token`

***Method***

`POST`

***Param***

|参数|必须|说明|取值|
|:--:|:--:|:--:|:--:|
| user_name | 是 | 用户名 | String |
| character_name | 是 | 角色名称 | String |
| token | 是 | 令牌，从登录接口中获取 | String |

***Return Example***

```json
{
  "data": {
    "token_count": 198,
    "token_state": "小蓝: 你是小红，是一名年轻女性。爱好是看书、旅游。职业是服装设计师。喜欢吃生鱼片。敢爱敢恨，偶尔有些任性，喜欢帮助别人。印象最深的一件事是曾将一位晕倒的陌生女孩儿送去医院，结果发现这个女孩正是自己暗恋多年的男神的妹妹。小红称呼我为小蓝。\n\n小红: 小蓝，来和我一起玩吧。\n\n"
  },
  "message": "success",
  "code": 200
}
```

***Code***

|状态码|说明|
|:--:|:--:|
|200|请求成功|
|400|错误|

### 10.回溯对话

***URL***

`/chat/back`

***Method***

`POST`

***Param***

|参数|必须|说明|取值|
|:--:|:--:|:--:|:--:|
| user_name | 是 | 用户名 | String |
| character_name | 是 | 角色名称 | String |
| log_index | 否 | 回溯对话的节点，用户和角色进行一次对话（用户和角色各说了一条）视为一个节点，角色的开场白（该组对话没有用户的发言，这个节点值通常是0）也算是一个节点，节点从0开始，比如和某个角色进行了三组对话，我想回溯到第二组，那么这个值是1，如果不传这个参数，那么程序会取默认值为0 | Number |
| token | 是 | 令牌，从登录接口中获取 | String |

***Return Example***

```json
{
  "data": null,
  "message": "success",
  "code": 200
}
```

***Code***

|状态码|说明|
|:--:|:--:|
|200|请求成功|
|400|错误|

### 11.替角色说

***URL***

`/chat/tamper`

***Method***

`POST`

***Param***

|参数|必须|说明|取值|
|:--:|:--:|:--:|:--:|
| user_name | 是 | 用户名 | String |
| character_name | 是 | 角色名称 | String |
| message | 是 | 要替角色说的话 | String |
| token | 是 | 令牌，从登录接口中获取 | String |

***Return Example***

```json
{
  "data": null,
  "message": "success",
  "code": 200
}
```

***Code***

|状态码|说明|
|:--:|:--:|
|200|请求成功|
|400|错误|