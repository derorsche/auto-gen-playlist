import asyncio
from logging import config

from yaml import safe_load

LOG_CONF_PATH = "etc/log-conf.yaml"


async def main():
    with open(LOG_CONF_PATH, "r", encoding="utf-8") as f:
        yml = safe_load(f)
    config.dictConfig(yml)


if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
