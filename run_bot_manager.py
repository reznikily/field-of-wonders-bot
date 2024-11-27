import os

from aiohttp.web import run_app

from app.web.app import setup_bot_manager

run_app(
    setup_bot_manager(
        config_path=os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "etc/cfg.yaml"
        )
    ),
    port=8001,
)
