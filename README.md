## 一个基于Flask实现的RWKV角色扮演API

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
python api.py --listen --model model/fp16i8_RWKV-4-Raven-7B-v9x-Eng49-Other1%-20230418-ctx4096
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
		"user": "小蓝",
		"bot": "小红",
		"greeting": "小蓝，来和我一起玩吧。",
		"bot_persona": "是一名年轻女性。爱好是看书、旅游。职业是服装设计师。喜欢吃生鱼片。敢爱敢恨，偶尔有些任性，喜欢帮助别人。印象最深的一件事是曾将一位晕倒的陌生女孩儿送去医院，结果发现这个女孩正是自己暗恋多年的男神的妹妹。"
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
| token | 是 | 令牌，从登录接口中获取 | String |
| bot | 是 | 角色名称 | String |  
| user | 是 | 角色如何称呼用户 | String |
| greeting | 是 | 角色的开场白 | String |
| bot_persona | 是 | 角色的性格 | String |

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

### 5.加载角色

***URL***

`/characters/load`

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
		"reply": "小蓝，来和我一起玩吧。"
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

### 6.对话

***URL***

`/chat/reply`

***Method***

`POST`

***Param***

|参数|必须|说明|取值|
|:--:|:--:|:--:|:--:|
| user_name | 是 | 用户名 | String |
| token | 是 | 令牌，从登录接口中获取 | String |
| prompt | 是 | 用户输入的内容 | String |  
| top_p | 否 | top_p值，默认为0.6 | Number |  
| top_k | 否 | top_k值，默认为0 | Number |  
| temperature | 否 | temperature值，默认为1.8 | Number |  
| presence_penalty | 否 | presence_penalty值，默认为0.2 | Number |  
| frequency_penalty | 否 | frequency_penalty值，默认为0.2 | Number |  

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

### 7.重说

***URL***

`/chat/resay`

***Method***

`POST`

***Param***

|参数|必须|说明|取值|
|:--:|:--:|:--:|:--:|
| user_name | 是 | 用户名 | String |
| token | 是 | 令牌，从登录接口中获取 | String |
| top_p | 否 | top_p值，默认为0.6 | Number |  
| top_k | 否 | top_k值，默认为0 | Number |  
| temperature | 否 | temperature值，默认为1.8 | Number |  
| presence_penalty | 否 | presence_penalty值，默认为0.2 | Number |  
| frequency_penalty | 否 | frequency_penalty值，默认为0.2 | Number |  

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

### 8.重置

***URL***

`/chat/reset`

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
		"reply": "小蓝，来和我一起玩吧。"
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