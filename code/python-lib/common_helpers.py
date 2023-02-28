# common_helpers.py

import re
from timeit import default_timer as timer


class jsObj(dict):
    """JS-object-like dict (access to `foo`: `obj.foo` as well as `obj["foo"]`).
    See also: `adict` library on PyPI
    """
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

    # Example:
    # >>> d = jsObj()
    # >>> d.ax = '123'
    # >>> d
        # {'ax': '123'}


class Checkpointer():  # dict
    """Measures time between hits. Requires the `from timeit import default_timer as timer` import."""
    def __init__(self, start=True):
        super().__init__()
        self.first = timer()
        self.last = self.first

    def reset_now(self):
        self.__init__(start=False)

    def hit(self, label=None) -> float:
        now = timer()
        delta = now - self.last
        if label:
            print((label or 'Checkpoint') + ':', "%.4f" % delta, 's')
        self.last = now
        return delta

    def since_start(self, label=None, hit=False) -> float:
        now = timer()
        delta = now - self.first
        if label:
            print(label or 'Total:', "%.4f" % delta, 's')
        if hit:
            self.last = now
        return delta


__CAMELCASE_RE = re.compile(r"([a-z])([A-Z])")

def camelcase_to_snakecase(s: str, sep='_') -> str:
    """Reformat `LongCamelCaseWords` to better-looking `long_snake_case_words`
    inserting underscore as default separator """
    return __CAMELCASE_RE.sub(lambda m: f"{m.group(1)}{sep}{m.group(2)}", s).lower()

