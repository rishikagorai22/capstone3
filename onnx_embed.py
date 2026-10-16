import os
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

_HERE = os.path.dirname(os.path.abspath(__file__))
_session = None
_tokenizer = None


def _load():
    global _session, _tokenizer
    if _session is None:
        _tokenizer = Tokenizer.from_file(os.path.join(_HERE, "tokenizer.json"))
        _tokenizer.enable_truncation(max_length=256)
        _tokenizer.enable_padding()
        _session = ort.InferenceSession(os.path.join(_HERE, "model.onnx"),
                                        providers=["CPUExecutionProvider"])
    return _session, _tokenizer


def embed(texts):
    session, tok = _load()
    encs = tok.encode_batch(texts)
    input_ids = np.array([e.ids for e in encs], dtype=np.int64)
    attention_mask = np.array([e.attention_mask for e in encs], dtype=np.int64)
    inputs = {"input_ids": input_ids, "attention_mask": attention_mask,
              "token_type_ids": np.zeros_like(input_ids)}
    wanted = {i.name for i in session.get_inputs()}
    inputs = {k: v for k, v in inputs.items() if k in wanted}
    hidden = session.run(None, inputs)[0]
    mask = attention_mask[..., None].astype(np.float32)
    pooled = (hidden * mask).sum(axis=1) / np.clip(mask.sum(axis=1), 1e-9, None)
    norms = np.linalg.norm(pooled, axis=1, keepdims=True)
    return (pooled / np.clip(norms, 1e-12, None)).tolist()


def get_embedding(text):
    return embed([text])[0]
