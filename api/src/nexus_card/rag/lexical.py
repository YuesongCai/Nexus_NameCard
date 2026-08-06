"""BM25 over a CJK-aware tokenizer.

Latin runs tokenize as words; CJK runs tokenize as character bigrams (plus unigrams), which
is what makes "客户数据安全吗" retrievable without shipping a segmentation model.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

_LATIN = re.compile(r"[a-z0-9][a-z0-9+._-]*")
_CJK = re.compile(r"[㐀-鿿豈-﫿]+")

_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "for", "on", "it", "that",
    "this", "with", "as", "at", "by", "be", "from", "we", "you", "your", "our", "what",
    "how", "does", "do", "can", "i", "me", "my", "s", "t",
    "的", "了", "是", "在", "和", "与", "吗", "呢", "有", "我", "你", "他", "它", "们",
}

_K1 = 1.4
_B = 0.72


def tokenize(text: str) -> list[str]:
    text = text.lower()
    tokens: list[str] = []
    for match in _LATIN.finditer(text):
        tok = match.group(0)
        if len(tok) > 1 and tok not in _STOP:
            tokens.append(tok)
    for match in _CJK.finditer(text):
        run = match.group(0)
        for ch in run:
            if ch not in _STOP:
                tokens.append(ch)
        for i in range(len(run) - 1):
            tokens.append(run[i : i + 2])
    return tokens


@dataclass(slots=True)
class Bm25:
    doc_tokens: list[list[str]]
    _tf: list[Counter[str]]
    _df: Counter[str]
    _lengths: list[int]
    _avg_len: float
    _n: int

    @classmethod
    def build(cls, documents: list[str]) -> Bm25:
        doc_tokens = [tokenize(d) for d in documents]
        tf = [Counter(toks) for toks in doc_tokens]
        df: Counter[str] = Counter()
        for counter in tf:
            df.update(counter.keys())
        lengths = [len(toks) for toks in doc_tokens]
        avg = (sum(lengths) / len(lengths)) if lengths else 1.0
        return cls(doc_tokens, tf, df, lengths, avg or 1.0, len(documents))

    def scores(self, query: str) -> list[float]:
        q_tokens = tokenize(query)
        if not q_tokens or self._n == 0:
            return [0.0] * self._n

        out = [0.0] * self._n
        for token in set(q_tokens):
            df = self._df.get(token, 0)
            if df == 0:
                continue
            idf = math.log(1 + (self._n - df + 0.5) / (df + 0.5))
            for i, counter in enumerate(self._tf):
                freq = counter.get(token, 0)
                if not freq:
                    continue
                norm = 1 - _B + _B * (self._lengths[i] / self._avg_len)
                out[i] += idf * (freq * (_K1 + 1)) / (freq + _K1 * norm)
        return out
