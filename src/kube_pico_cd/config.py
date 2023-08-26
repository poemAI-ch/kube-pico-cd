
from dynaconf import Dynaconf
import pkg_resources
import logging

_logger = logging.getLogger(__name__)

settings_path = pkg_resources.resource_filename('kube_pico_cd', 'settings.toml')

settings = Dynaconf(
    envvar_prefix="KUBE_PICO_CD",
    settings_files=[settings_path],
)

logging.basicConfig(level=logging.INFO, format=settings.log_format)


def get_current_namespace():
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r") as f:
            return f.read().strip()
    except IOError as e:
        _logger.debug(f"An IOError occurred while determining the namespace: {e}")
        return None


# After you've instantiated your settings object
if 'namespace' not in settings:
    namespace = get_current_namespace()
    if namespace:
        settings.set('namespace', namespace)

