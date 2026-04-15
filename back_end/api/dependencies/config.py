from functools import lru_cache
from ml_library.utils.config import load_config as _load_config


@lru_cache()
def get_config(config_path: str = "config.yaml"):
    return _load_config(config_path)


def reload_config(config_path: str = "config.yaml"):
    get_config.cache_clear()
    return get_config(config_path)