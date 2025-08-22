from ldap3 import Server, Connection, ALL, SUBTREE
from typing import Dict, List, Optional
from ldap3.core.exceptions import LDAPException, LDAPBindError, LDAPExceptionError
import logging


LOGGER = logging.getLogger(__name__)


class ADconnection:

    def __init__(self, config):
        self._conn = self._connect_to_ad(config)

    def _connect_to_ad(self, config):
        """
        Establishes a connection to the Active Directory server.
        The connection would be established using current user's credentials.
        Returns: An active LDAP connection object.
        """
        try:
            server = Server(
                config.ad_server,
                use_ssl=config.ad_use_ssl,
                port=config.ad_port,
                get_info=ALL,
            )
            connection = Connection(
                server,
                authentication="SASL",
                sasl_mechanism="GSSAPI",
                # user=config.ad_user,
                # password=config.ad_password,
                auto_bind=True,
                raise_exceptions=True,
            )
            LOGGER.info(f"Connected to AD server: {config.ad_server}")
            return connection
        except LDAPBindError as e:
            LOGGER.info(f"Failed to connect to AD: {e}")
            raise
        except LDAPException as e:
            LOGGER.info(f"LDAP connection error: {e}")
            raise

    def get_ad_groups(
        self, config, ad_group_name: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        Fetches AD groups starting with AWS_ and their members.
        Returns: { group_name: [member_email1, member_email2, ...] }
        """
        try:
            base_dn = config.ad_base_dn
            if ad_group_name:
                filter = f"(&(objectClass=group)(cn={ad_group_name}))"
            else:
                filter = f"(&(objectClass=group)(cn={config.ad_group_filter}))"
            attributes = ["cn", "member"]

            search_result = self._conn.search(
                search_base=base_dn,
                search_filter=filter,
                search_scope=SUBTREE,
                attributes=attributes,
                size_limit=1,
            )

            if not search_result:
                raise LDAPExceptionError(f"LDAP search failed: {self._conn.last_error}")

            results = {}
            for entry in self._conn.entries:
                group_name = entry.cn.value
                members_dns = entry.member.values if hasattr(entry, "member") else []
                members_emails = [self._extract_email_from_dn(dn) for dn in members_dns]
                members_emails = [
                    email for email in members_emails if email
                ]  # Filter out None
                results[group_name] = members_emails

            LOGGER.info(f"Found {len(results)} AWS groups.")
            self._conn.unbind()
            return results
        except LDAPExceptionError as e:
            LOGGER.info(f"LDAP search error: {e}")
            raise
        except Exception as e:
            LOGGER.info(f"Unexpected error in LDAP search: {e}")
            raise

    def _extract_email_from_dn(self, dn: str) -> str:
        """
        Given a user's DN, returns their primary email address (mail attribute).
        Returns None if not found or error occurs.
        """
        try:
            self._conn.search(
                search_base=dn,
                search_filter="(objectClass=person)",
                attributes=["mail"],
                size_limit=1,
            )

            if self._conn.entries:
                user_entry = self._conn.entries[0]
                return user_entry.mail.value if hasattr(user_entry, "mail") else None

        except LDAPException as e:
            # Could log this for troubleshooting
            LOGGER.info(f"LDAP lookup failed for {dn}: {e}")

        return None
