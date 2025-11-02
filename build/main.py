import json
from typing import Dict

from build_manager import Builder

def load_config(path: str) -> Dict:
    with open(path, 'r') as f:
        return json.load(f)

def main():
    config = load_config('build.cfg.json')
    builder = Builder(config)
    builder.build()

if __name__ == "__main__":
    main()