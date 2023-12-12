import gc
import torch
from rwkv.utils import PIPELINE
from rwkv.model import RWKV
import random

torch.backends.cudnn.benchmark = True
torch.backends.cudnn.allow_tf32 = True
torch.backends.cuda.matmul.allow_tf32 = True


def format_chat_param(top_p, top_k, temperature, presence_penalty, frequency_penalty):
    chat_param = {
        'top_p': top_p,
        'top_k': top_k,
        'temperature': temperature,
        'presence_penalty': presence_penalty,
        'frequency_penalty': frequency_penalty
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

    def get_reply(self, model_tokens, model_state, out, chat_param, occurrence_tokens=[]):
        clear_cache()
        begin = len(model_tokens)
        out_last = begin
        occurrence = {}
        for t in occurrence_tokens:
            if t in self.AVOID_REPEAT_TOKENS:
                continue
            if t in occurrence:
                occurrence[t] += 1
            else:
                occurrence[t] = 1
        for i in range(512):
            for n in occurrence:
                out[n] -= (chat_param['presence_penalty'] + occurrence[n] * 
                           chat_param['frequency_penalty'])
            token = self.pipeline.sample_logits(
                out, chat_param['temperature'], chat_param['top_p'], chat_param['top_k'])
            out, model_tokens, model_state = self.run_rnn(
                model_tokens, model_state, [token])
            out[self.END_OF_TEXT] = self.NEG_INF
            for xxx in occurrence:
                occurrence[xxx] *= 0.996
            if token not in occurrence:
                occurrence[token] = 1
            else:
                occurrence[token] += 1
            xxx = self.pipeline.decode(model_tokens[out_last:])
            if '\ufffd' not in xxx:  # avoid utf-8 display issues
                out_last = begin + i + 1
            send_msg = self.pipeline.decode(model_tokens[begin:])
            if '\n\n' in send_msg:
                send_msg = send_msg.strip()
                break
            yield send_msg, out, model_tokens, model_state
        yield send_msg, out, model_tokens, model_state
