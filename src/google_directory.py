"""
Thin wrapper around Google Admin SDK Directory API.

Responsibilities:
- Authenticate via Service Account w/ Domain-Wide Delegation
- List groups + members
- Create groups
- Add members (idempotent handling: ignore 409 alreadyExists)
"""

import httplib2
import logging
from typing import Dict, Set, Optional, Iterable

from google_auth_httplib2 import AuthorizedHttp
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .utils import retry

LOGGER = logging.getLogger(__name__)


class GoogleDirectory:
    def __init__(
        self,
        creds_info: dict,
        delegated_subject: str,
        google_api_scopes: Optional[Iterable[str]] = None,
        http_timeout: float = 30.0,
    ):
        """
        :param creds_info: service account json (dict)
        :param delegated_subject: admin email to impersonate
        """
        creds = service_account.Credentials.from_service_account_info(
            creds_info, scopes=google_api_scopes
        )
        delegated = creds.with_subject(delegated_subject)

        # HTTP client with timeout
        base_http = httplib2.Http(timeout=http_timeout)
        authed_http = AuthorizedHttp(delegated, http=base_http)

        # cache_discovery=False avoids file writes in some environments
        self._svc = build(
            "admin", "directory_v1", http=authed_http, cache_discovery=False
        )
        self._num_retries = 3

    # ---------- Group listing ----------

    @retry((HttpError,), tries=5)
    def _groups_list(
        self,
        domain: Optional[str] = None,
        customer: Optional[str] = None,
        page_token: Optional[str] = None,
    ):
        return (
            self._svc.groups()
            .list(
                domain=domain, customer=customer, pageToken=page_token, maxResults=200
            )
            .execute(num_retries=self._num_retries)
        )

    @retry((HttpError,), tries=5)
    def _members_list(self, group_email: str, page_token: Optional[str] = None):
        return (
            self._svc.members()
            .list(groupKey=group_email, pageToken=page_token, maxResults=200)
            .execute(num_retries=self._num_retries)
        )

    def get_all_groups_with_members(
        self,
        domain: Optional[str] = None,
        customer: Optional[str] = None,
        prefix: Optional[str] = None,
    ) -> Dict[str, Set[str]]:
        """
        Returns: { group_email: {member_email, ...}, ... }
        """
        LOGGER.info(
            "Fetching Google groups (domain=%s, customer=%s, prefix=%s)",
            domain,
            customer,
            prefix,
        )
        groups: Dict[str, Set[str]] = {}
        next_token: Optional[str] = None

        while True:
            try:
                resp = self._groups_list(
                    domain=domain, customer=customer, page_token=next_token
                )
            except HttpError as e:
                LOGGER.error("Failed to list groups: %s", e)
                raise

            for g in resp.get("groups", []):
                g_name = g.get("name", "")
                if prefix and not g_name.startswith(prefix):
                    continue
                g_email = g.get("email")
                if not g_email:
                    continue
                groups[g_email] = set()

                # members
                m_token = None
                while True:
                    try:
                        m_resp = self._members_list(
                            group_email=g_email, page_token=m_token
                        )
                        for m in m_resp.get("members", []):
                            # only include active members; filter out non-user types if desired
                            m_email = m.get("email")
                            if m_email:
                                groups[g_email].add(m_email.lower())
                        m_token = m_resp.get("nextPageToken")
                        if not m_token:
                            break
                    except HttpError as e:
                        if e.resp.status == 404:
                            # group has no members
                            break
                        LOGGER.error("Failed to list members for %s: %s", g_email, e)
                        raise

            next_token = resp.get("nextPageToken")
            if not next_token:
                break

        LOGGER.info("Fetched %d groups from Google", len(groups))
        return groups

    # ---------- Group creation & membership ----------

    @retry((HttpError,), tries=5)
    def create_group(
        self,
        group_email: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> dict:
        body = {
            "email": group_email,
            "name": name,
            "description": description or "Provisioned by AD - Google sync",
        }
        LOGGER.info("Creating Google group %s", group_email)
        return self._svc.groups().insert(body=body).execute()

    @retry((HttpError,), tries=5)
    def add_member(
        self, group_email: str, member_email: str, role: str = "MEMBER"
    ) -> Optional[dict]:
        body = {"email": member_email, "role": role}
        try:
            return self._svc.members().insert(groupKey=group_email, body=body).execute()
        except HttpError as e:
            if e.resp.status == 409:
                # already a member
                LOGGER.debug("Member %s already in %s", member_email, group_email)
                return None
            raise

    def add_members_bulk(self, group_email: str, members: Iterable[str]) -> None:
        for m in members:
            try:
                self.add_member(group_email, m)
            except HttpError as e:
                LOGGER.error("Failed to add %s to %s: %s", m, group_email, e)
                # continue; do not abort entire sync

    @retry((HttpError,), tries=5)
    def get_group_by_email(self, group_email: str) -> Optional[dict]:
        """
        Fetch a group by its unique email address.
        Returns full group metadata or None if not found.
        """
        try:
            return self._svc.groups().get(groupKey=group_email).execute()
        except HttpError as e:
            if e.resp.status == 404:
                return None
            raise
