"""
Sync logic: one-way union update from AD -> Google.
"""

import logging
from typing import Dict, Set, Optional

from .google_directory import GoogleDirectory

LOGGER = logging.getLogger(__name__)


def to_group_email(group_key: str, group_domain: str) -> str:
    """
    Map a group key from AD to a Google group email.
    If the key already contains '@', return as-is; otherwise append '@{group_domain}'.
    """
    group_key = group_key.strip()
    if "@" in group_key:
        return group_key.lower()
    return f"{group_key.lower()}@{group_domain}".lower()


class SyncService:
    def __init__(
        self,
        gd: GoogleDirectory,
        group_domain: str,
        customer_id: Optional[str] = None,
        group_name_prefix: Optional[str] = None,
    ):
        self.gd = gd
        self.group_domain = group_domain
        self.customer_id = customer_id
        self.prefix = group_name_prefix

    def fetch_google_state(self) -> Dict[str, Set[str]]:
        """
        Returns current Google groups: { group_email: {member_email, ...} }
        """
        return self.gd.get_all_groups_with_members(
            domain=self.group_domain, customer=self.customer_id, prefix=self.prefix
        )

    def union_update_group_members(self, ad_groups: Dict[str, Set[str]]) -> None:
        """
        For each AD group:
          - Ensure Google group exists (create if missing)
          - Compute union(existing_google_members, ad_members)
          - Add missing members (no removals)
        """
        LOGGER.info("Starting update for %d AD groups", len(ad_groups))
        google_groups = self.fetch_google_state()  # {email: set(members)}

        for ad_group_key, ad_members in ad_groups.items():
            group_email = to_group_email(ad_group_key, self.group_domain)
            ad_members_norm = {m.strip().lower() for m in ad_members if m and "@" in m}

            if group_email not in google_groups:
                LOGGER.info("Group %s not found in Google. Creating...", group_email)
                self.gd.create_group(group_email, name=ad_group_key)
                LOGGER.info("Created group %s", group_email)
                # Newly created group has no members; add all AD members
                if len(ad_members_norm) != 0:
                    self.gd.add_members_bulk(group_email, ad_members_norm)
                    LOGGER.info(
                        "Added %d members to new group %s",
                        len(ad_members_norm),
                        group_email,
                    )
                else:
                    LOGGER.info("No members to add to new group %s", group_email)
                continue

            current = google_groups.get(group_email, set())
            desired_union = current.union(ad_members_norm)

            missing = desired_union - current
            if not missing:
                LOGGER.info(
                    "Group %s already up-to-date (size=%d)", group_email, len(current)
                )
                continue

            LOGGER.info("Adding %d missing member(s) to %s", len(missing), group_email)
            LOGGER.debug("The group: %s  missing members:\n%s", group_email, missing)
            self.gd.add_members_bulk(group_email, missing)

        LOGGER.info("Union update completed.")
