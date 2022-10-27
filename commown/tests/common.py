import os
from contextlib import contextmanager

from odoo.addons.server_environment import server_env
from odoo.addons.server_environment.models import server_env_mixin


@contextmanager
def fake_slimpay_server_env_config(config=None):
    "Fake a server env config for slimpay acquirer using env variables"

    # Default config if not given
    if config is None:
        config = "\n".join(
            [
                "[payment_acquirer.Slimpay]",
                "slimpay_api_url=https://example.com",
                "slimpay_creditor=creditor",
                "slimpay_app_id=slimpay_app_id",
                "slimpay_app_secret=slimpay_app_secret",
            ]
        )

    # Save server environment state
    old_server_env_dir = server_env._dir
    old_server_env_config = server_env_mixin.serv_config
    old_env_server_env_config = os.environ.get("SERVER_ENV_CONFIG")

    try:
        # Execute the decorated function in the modified server environment
        server_env._dir = None
        os.environ["SERVER_ENV_CONFIG"] = config
        server_env_mixin.serv_config = server_env._load_config()
        yield
    finally:
        # Restore previous server environment state
        server_env._dir = old_server_env_dir
        server_env_mixin.serv_config = old_server_env_config
        if not old_env_server_env_config:
            del os.environ["SERVER_ENV_CONFIG"]
        else:
            os.environ["SERVER_ENV_CONFIG"] = old_env_server_env_config
