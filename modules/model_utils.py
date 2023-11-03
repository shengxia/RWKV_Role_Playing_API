import gc
import torch
from rwkv.utils import PIPELINE
from rwkv.model import RWKV

torch.backends.cudnn.benchmark = True
torch.backends.cudnn.allow_tf32 = True
torch.backends.cuda.matmul.allow_tf32 = True


def format_chat_param(top_p, temperature, presence_penalty, frequency_penalty, max_len=0):
    chat_param = {
        'top_p': top_p,
        'temperature': temperature,
        'presence_penalty': presence_penalty,
        'frequency_penalty': frequency_penalty,
        'max_len': max_len
    }
    return chat_param

def clear_cache():
    gc.collect()
    torch.cuda.empty_cache()

class ModelUtils:
    model = None
    pipeline = None
    CHUNK_LEN = 100
    END_OF_TEXT = 0
    DOUBLE_END_OF_LINE = 261
    NEG_INF = -999999999
    AVOID_REPEAT = '.!?,()[]{}。！？，（）:：'
    AVOID_REPEAT_TOKENS = []

    def __init__(self, args):
        self.load_model(args.model, args.strategy)

    def load_model(self, model_path, strategy):
        self.model = RWKV(model=model_path, strategy=strategy)
        self.pipeline = PIPELINE(self.model, "rwkv_vocab_v20230424")
        for i in self.AVOID_REPEAT:
            dd = self.pipeline.encode(i)
            assert len(dd) == 1
            self.AVOID_REPEAT_TOKENS += dd

    def run_rnn(self, model_tokens, model_state, tokens):
        tokens = [int(x) for x in tokens]
        model_tokens += tokens
        while len(tokens) > 0:
            out, model_state = self.model.forward(
                tokens[:self.CHUNK_LEN], model_state)
            tokens = tokens[self.CHUNK_LEN:]
        if model_tokens[-1] in self.AVOID_REPEAT_TOKENS:
            out[model_tokens[-1]] = self.NEG_INF
        return out, model_tokens, model_state

    def get_reply(self, model_tokens, model_state, out, chat_param):
        clear_cache()
        begin = len(model_tokens)
        out_last = begin
        for i in range(1024):
            if chat_param['max_len'] >0:
                if i <= 0:
                    nl_bias = self.NEG_INF
                elif i <= chat_param['max_len']:
                    nl_bias = (i - chat_param['max_len']) * 0.1
                else:
                    nl_bias = 0
                out[self.DOUBLE_END_OF_LINE] += nl_bias
            occurrence = {}
            if out_last > 256:
                tokens_chunk = model_tokens[(out_last - 256):]
            else:
                tokens_chunk = model_tokens[begin:]
            for token in tokens_chunk:
                if token in self.AVOID_REPEAT_TOKENS:
                    continue
                occurrence[token] = 1 + (occurrence[token] if token in occurrence else 0)
            for n in occurrence:
                out[n] -= (chat_param['presence_penalty'] + occurrence[n] * 
                           chat_param['frequency_penalty'])
            token = self.pipeline.sample_logits(
                out, chat_param['temperature'], chat_param['top_p'])
            out, model_tokens, model_state = self.run_rnn(
                model_tokens, model_state, [token])
            out[self.END_OF_TEXT] = self.NEG_INF
            xxx = self.pipeline.decode(model_tokens[out_last:])
            if '\ufffd' not in xxx:  # avoid utf-8 display issues
                out_last = begin + i + 1
            send_msg = self.pipeline.decode(model_tokens[begin:])
            if '\n\n' in send_msg:
                send_msg = send_msg.strip()
                break
            yield send_msg, out, model_tokens, model_state
        yield send_msg, out, model_tokens, model_state
