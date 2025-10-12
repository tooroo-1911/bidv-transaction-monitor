import requests
import ssl
import logging
from requests.adapters import HTTPAdapter
from src import app_config as config


logger = logging.getLogger(__name__)


class SSLAdapter(HTTPAdapter):
    """Custom adapter for SSL with strong security (production ready)."""

    def __init__(self, ssl_context=None, *args, **kwargs):
        self.ssl_context = ssl_context or self._create_ssl_context()
        super().__init__(*args, **kwargs)

    def _create_ssl_context(self):
        ctx = ssl.create_default_context()

        if not config.TLS_VERIFY:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            logger.warning("TLS verification is DISABLED (verify=False)")

        return ctx

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = self.ssl_context
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        kwargs["ssl_context"] = self.ssl_context
        return super().proxy_manager_for(*args, **kwargs)


def create_ssl_session(cert=None) -> requests.Session:
    session = requests.Session()
    session.mount("https://", SSLAdapter())

    if cert:
        session.cert = cert
        logger.debug("Mutual TLS enabled with cert: %s", cert)

    return session
