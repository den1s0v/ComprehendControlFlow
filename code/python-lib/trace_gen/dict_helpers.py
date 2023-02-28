# dict_helpers.py


def get_ith_expr_value(expr_values: tuple, i: int):
    """Decodes the result of `parse_expr_values` function.
    Return None if `i` is out of range
    """
    if "(" not in expr_values:
        return expr_values[i] if i < len(expr_values) else None

    b_i = expr_values.index("(")
    if i < b_i:
        return expr_values[i]

    repeat_i = i - b_i

    b_i += 1  # skip the "(" element itself
    assert expr_values[-1] == ")", str(expr_values)
    e_i = expr_values.index(")")
    repeat_len = e_i - b_i
    if repeat_len <= 0:  # in the case of stupid empty repeat: (True, "(", ")")
        return None

    return expr_values[b_i + repeat_i % repeat_len]


def find_by_key_in(key, dict_or_list, _not_entry=None):
    """Find a dict having `key` within given structure of nested lists and dicts"""
    _not_entry = _not_entry or set()
    _not_entry.add(id(dict_or_list))
    if isinstance(dict_or_list, dict):
        for k, v in dict_or_list.items():
            if k == key:
                yield dict_or_list
            elif id(v) not in _not_entry:
                yield from find_by_key_in(key, v, _not_entry)
    elif isinstance(dict_or_list, (list, tuple, set)):
        for d in dict_or_list:
            if id(d) not in _not_entry:
                yield from find_by_key_in(key, d, _not_entry)


def find_by_keyval_in(key, val, dict_or_list):
    """Find a dict having `key` mapped to value `val` within given structure of nested lists and dicts"""
    if isinstance(dict_or_list, dict):
        for k, v in dict_or_list.items():
            if k == key and v == val:
                yield dict_or_list
            else:
                yield from find_by_keyval_in(key, val, v)
    elif isinstance(dict_or_list, (list, tuple, set)):
        for d in dict_or_list:
            yield from find_by_keyval_in(key, val, d)

