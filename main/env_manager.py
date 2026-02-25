# env_manager.py
import os
from pathlib import Path

ENV_FILE = Path(__file__).parent / '.env'

def read_env():
    """Читает .env файл и возвращает словарь переменных."""
    if not ENV_FILE.exists():
        return {}
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    env_dict = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            key, value = line.split('=', 1)
            env_dict[key.strip()] = value.strip()
    return env_dict

def write_env(env_dict):
    """Записывает словарь переменных в .env файл (перезаписывает)."""
    with open(ENV_FILE, 'w', encoding='utf-8') as f:
        for key, value in env_dict.items():
            f.write(f"{key}={value}\n")