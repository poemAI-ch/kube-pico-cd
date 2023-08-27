import logging

import pkg_resources
from dynaconf import Dynaconf

_logger = logging.getLogger(__name__)

settings_path = pkg_resources.resource_filename("kube_pico_cd", "settings.toml")

settings = Dynaconf(
    envvar_prefix="KUBE_PICO_CD",
    settings_files=[settings_path],
)

log_format = None
if "log_format" in settings:
    log_format = settings.log_format
logging.basicConfig(level=logging.INFO, format=log_format)


def get_current_namespace():
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r") as f:
            return f.read().strip()
    except IOError as e:
        _logger.debug(f"An IOError occurred while determining the namespace: {e}")
        return None


# After you've instantiated your settings object
if "kube_namespace" not in settings:
    kube_namespace = get_current_namespace()
    if kube_namespace:
        settings.set("kube_namespace", kube_namespace)
        _logger.info(
            f"Using namespace {kube_namespace}, retrieved from service account"
        )
