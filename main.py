import asyncio
from logging import Filter, LogRecord, config

import dotenv
from yaml import safe_load

LOG_CONF_PATH = "etc/log-conf.yaml"


class StreamHandlerFilter(Filter):
    def filter(self, record: LogRecord):
        return "auto_gen_playlist.requests" != record.name


async def main():
    dotenv.load_dotenv()  # type: ignore

    with open(LOG_CONF_PATH, "r", encoding="utf-8") as f:
        yml = safe_load(f)
    config.dictConfig(yml)


if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
