"""
Auto Configuration Helper
"""
from __future__ import absolute_import

import collections
import logging

from . import utilities

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse
import rhsm.config

from .constants import InsightsConstants as constants
from .cert_auth import rhsmCertificate

logger = logging.getLogger(__name__)
APP_NAME = constants.app_name


# Can't use enum, it's not supported in Python below 3.4
class DeploymentType:
    PRODUCTION = "production"
    STAGE = "stage"
    SATELLITE = "satellite"


def _is_console_dot(hostname):
    return hostname == 'subscription.rhsm.redhat.com'


def _is_staging_console_dot(hostname):
    return hostname == 'subscription.rhsm.stage.redhat.com'


# Can't use dataclass, it's not supported in Python below 3.7
ProxyConfig = collections.namedtuple("ProxyConfig", ["proxy", "no_proxy"])


def _read_rhsm_proxy_settings(rhsm_config):
    # type: ("rhsm.config.RhsmConfigParser") -> ProxyConfig

    rhsm_proxy_scheme = rhsm_config.get("server", "proxy_scheme").strip()  # type: str
    rhsm_proxy_hostname = rhsm_config.get('server', 'proxy_hostname').strip()  # type: str
    rhsm_proxy_port = rhsm_config.get('server', 'proxy_port').strip()  # type: str
    rhsm_proxy_user = rhsm_config.get('server', 'proxy_user').strip()  # type: str
    rhsm_proxy_pass = rhsm_config.get('server', 'proxy_password').strip()  # type: str

    proxy = None  # type: str | None
    if rhsm_proxy_hostname != "":
        proxy_credentials = ""
        obfuscated_proxy_credentials = ""
        if rhsm_proxy_user != "" and rhsm_proxy_pass != "":
            proxy_credentials = "{}:{}@".format(rhsm_proxy_user, rhsm_proxy_pass)
            obfuscated_proxy_credentials = "{}:{}@".format(rhsm_proxy_user, "***")
        proxy = "{scheme}://{credentials}{hostname}:{port}".format(
            scheme=rhsm_proxy_scheme,
            credentials=proxy_credentials,
            hostname=rhsm_proxy_hostname,
            port=rhsm_proxy_port,
        )
        logger.debug("Using RHSM proxy '{scheme}://{credentials}{hostname}:{port}'.".format(
            scheme=rhsm_proxy_scheme,
            credentials=obfuscated_proxy_credentials,
            hostname=rhsm_proxy_hostname,
            port=rhsm_proxy_port,
        ))

    rhsm_no_proxy = rhsm_config.get('server', 'no_proxy').strip()  # type: str | None
    if rhsm_no_proxy.lower() == 'none' or rhsm_no_proxy == '':
        rhsm_no_proxy = None

    return ProxyConfig(proxy, rhsm_no_proxy)


APIConfig = collections.namedtuple("APIConfig", ["url", "cert_verify", "deployment_type"])


def _read_rhsm_settings(rhsm_config):
    # type: ("rhsm.config.RhsmConfigParser") -> APIConfig

    rhsm_hostname = rhsm_config.get('server', 'hostname')  # type: str
    rhsm_port = rhsm_config.get('server', 'port')  # type: str
    logger.debug("RHSM is configured for '{}:{}'.".format(rhsm_hostname, rhsm_port))

    if _is_console_dot(rhsm_hostname):
        logger.debug("RHSM is pointed at ConsoleDot.")
        api_url = constants.consoledot_fqdn + "/api"
        deployment_type = DeploymentType.PRODUCTION
    elif _is_staging_console_dot(rhsm_hostname):
        logger.debug('RHSM is pointed at staging ConsoleDot.')
        api_url = constants.consoledot_fqdn_stage + "/api"
        deployment_type = DeploymentType.STAGE
    else:
        # Satellite, Capsule or other deployment at customer site
        logger.debug("RHSM is pointed at Satellite.")
        api_url = "{}:{}/redhat_access/r/insights".format(rhsm_hostname, rhsm_port)
        deployment_type = DeploymentType.SATELLITE

    return APIConfig(
        url=api_url,
        cert_verify=True,
        deployment_type=deployment_type,
    )


def _maybe_switch_to_legacy(client_config, api_config):
    # type: ("insights.client.config.InsightsConfig", APIConfig) -> APIConfig
    """Decide whether to use legacy API at cert-api.access.redhat.com, or newer
    ConsoleDot one at cert.{cloud,console}.redhat.com."""
    try:
        rhel_version = utilities.get_rhel_version()
        if rhel_version >= 10:
            # RHEL 10 doesn't support legacy API
            return api_config
    except ValueError:
        pass

    if client_config.legacy_upload is False:
        return api_config

    legacy_api_config = APIConfig(
        url="cert-api.access.redhat.com/r/insights",
        cert_verify=None,  # the connection.py treats None as 'use dedicated certificate'
        deployment_type=DeploymentType.PRODUCTION,
    )
    return legacy_api_config


def autoconfigure_network(client_config):
    # type: ("insights.client.config.InsightsConfig") -> None
    """Autoconfigure to connect to Hosted or Satellite."""
    logger.debug("Determining API URIs.")
    if client_config.offline:
        logger.debug("Autoconfiguration is not necessary in offline mode.")
        return
    if not rhsmCertificate.existsAndValid():
        logger.debug("No reason to autoconfigure, host isn't registered with subscription-manager.")
        return
    if not client_config.auto_config:
        logger.debug("Autoconfiguration is disabled, API URI is '{}'.".format(client_config.base_url))
        return

    rhsm_config = rhsm.config.get_config_parser()  # type: "rhsm.config.RhsmConfigParser"
    api_config = _read_rhsm_settings(rhsm_config)  # type: APIConfig
    proxy_config = _read_rhsm_proxy_settings(rhsm_config)  # type: ProxyConfig

    if api_config.deployment_type == DeploymentType.PRODUCTION:
        api_config = _maybe_switch_to_legacy(client_config, api_config)

    logger.debug("Parsed RHSM configuration: deployment={deployment}, authorization={authn}.".format(
        deployment=api_config.deployment_type,
        authn="legacy API certificate" if api_config.cert_verify is None else str(api_config.cert_verify),
    ))

    apply_network_configuration(
        client_config,
        api_url=api_config.url,
        cert_verify=api_config.cert_verify,
        proxy=proxy_config.proxy,
        no_proxy=proxy_config.no_proxy,
    )

    logger.debug("API URI is '{}'.".format(client_config.base_url))


def apply_network_configuration(client_config, api_url, cert_verify, proxy, no_proxy):
    """Update configuration based on discovered data.

    :param client_config: Configuration object to be modified.
    :type client_config: insights.client.config.InsightsConfig
    :param api_url: API URL.
    :type api_url: str
    :param cert_verify: TLS validation rules.
        "true": Properly enforce TLS certificates.
        "false": Ignore all TLS certificates.
        None: Use packaged CA certificate for 'cert-api.access.redhat.com'.
    :type cert_verify: str | None
    :param proxy: 'user:password@domain:port' or None.
    :type proxy: str | None
    :param no_proxy: Domains that shouldn't use given proxy.
    :type no_proxy: str | None
    """
    client_config.base_url = api_url

    if cert_verify is not None:
        client_config.cert_verify = cert_verify

    if proxy is not None:
        client_config.proxy = proxy
    if no_proxy is not None:
        client_config.no_proxy = no_proxy
