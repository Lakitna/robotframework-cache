from robot.utils.dotdict import DotDict


def dotdict_to_dict(inp: dict | DotDict) -> dict:
    """Recursively cast every DotDict instance to plain dict"""
    res = {}
    for key, val in inp.items():
        if isinstance(val, DotDict):
            val = dict(val)  # noqa: PLW2901

        if isinstance(val, dict):
            val = dotdict_to_dict(val)  # noqa: PLW2901

        res[key] = val

    return res
