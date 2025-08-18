from ldap3 import Server, Connection, ALL, SUBTREE
from typing import Dict, List
from ldap3.core.exceptions import LDAPException, LDAPBindError, LDAPExceptionError


def connect_to_ad(config):
    """
    Establishes a connection to the Active Directory server using GSSAPI for authentication.
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
        conn = Connection(
            server,
            authentication="SASL",
            sasl_mechanism="GSSAPI",
            # user=config.ad_user,
            # password=config.ad_password,
            auto_bind=True,
            raise_exceptions=True,
        )
        print(f"Connected to AD server: {config.ad_server}")
        return conn
    except LDAPBindError as e:
        print(f"Failed to connect to AD: {e}")
        raise
    except LDAPException as e:
        print(f"LDAP connection error: {e}")
        raise


def get_aws_groups(conn, config) -> Dict[str, List[str]]:
    """
    Fetches AD groups starting with AWS_ and their members.
    Returns: { group_name: [member_email1, member_email2, ...] }
    """
    try:
        base_dn = config.ad_base_dn
        filter = f"(&(objectClass=group)(cn={config.ad_group_filter}))"
        attributes = ["cn", "member"]

        search_result = conn.search(
            search_base=base_dn,
            search_filter=filter,
            search_scope=SUBTREE,
            attributes=attributes,
            size_limit=1,
        )

        if not search_result:
            raise LDAPExceptionError(f"LDAP search failed: {conn.last_error}")

        results = {}
        for entry in conn.entries:
            group_name = entry.cn.value
            members_dns = entry.member.values if hasattr(entry, "member") else []
            members_emails = [extract_email_from_dn(conn, dn) for dn in members_dns]
            members_emails = [
                email for email in members_emails if email
            ]  # Filter out None
            results[group_name] = members_emails

        print(f"Found {len(results)} AWS groups.")
        conn.unbind()
        return results
    except LDAPExceptionError as e:
        print(f"LDAP search error: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error in LDAP search: {e}")
        raise


def extract_email_from_dn(conn, dn: str) -> str:
    """
    Given a user's DN, returns their primary email address (mail attribute).
    Returns None if not found or error occurs.
    """
    try:
        conn.search(
            search_base=dn,
            search_filter="(objectClass=person)",
            attributes=["mail"],
            size_limit=1,
        )

        if conn.entries:
            user_entry = conn.entries[0]
            return user_entry.mail.value if hasattr(user_entry, "mail") else None

    except LDAPException as e:
        # Could log this for troubleshooting
        print(f"LDAP lookup failed for {dn}: {e}")

    return None
