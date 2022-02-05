import json
import os


def set_environment_var() -> None:
    with open("lastfm-utils/config/config.json") as f:
        vars = json.load(f)
        for name, value in vars.items():
            os.environ[name] = value
