import os

from aiohttp.web import run_app

from app.web.app import setup_admin_api

run_app(
    setup_admin_api(
        config_path=os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "etc/cfg.yaml"
        )
    ),
    port=8080,
)
