"""
Central configuration.
Reads environment variables once and exposes a simple dataclass.
"""

import json
import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional, List
from google.cloud import secretmanager


load_dotenv()


@dataclass(frozen=True)
class Config:
    delegated_subject: str
    group_domain: str
    log_level: str
    service_account_json_path: Optional[str]
    service_account_json_inline: Optional[str]
    service_account_secret_manager: Optional[bool]
    ad_server: str
    ad_user: str
    ad_password: str
    ad_base_dn: str
    ad_group_filter: str
    ad_use_ssl: bool
    ad_port: int
    gauth_secret_key_id: Optional[str]
    gauth_secret_ver: Optional[str]
    gauth_secret_type: Optional[str]
    gauth_scopes: Optional[List[str]]
    gauth_customer_id: Optional[str]
    gauth_project_id: Optional[str]
    group_name_prefix: str

    @staticmethod
    def load() -> "Config":
        config = Config(
            delegated_subject=os.getenv("GAUTH_GOOGLE_DELEGATED_SUBJECT", "").strip(),
            group_domain=os.getenv("GROUP_DOMAIN", "").strip(),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            service_account_json_path=os.getenv(
                "GOOGLE_APPLICATION_CREDENTIALS", ""
            ).strip()
            or None,
            service_account_json_inline=os.getenv("SERVICE_ACCOUNT_JSON", "").strip()
            or None,
            service_account_secret_manager=os.getenv(
                "SERVICE_ACCOUNT_SECRET_MANAGER", "true"
            )
            .strip()
            .lower()
            == "true",
            ad_server=os.getenv("AD_SERVER").strip(),
            ad_user=os.getenv("AD_USER").strip(),
            ad_password=os.getenv("AD_PASSWORD").strip(),
            ad_base_dn=os.getenv("AD_BASE_DN").strip(),
            ad_group_filter=os.getenv("AD_GROUP_FILTER", "AWS_*").strip(),
            gauth_secret_key_id=os.getenv("GAUTH_SECRET_KEY_ID", "").strip() or None,
            gauth_secret_ver=os.getenv("GAUTH_SECRET_VER", "").strip() or None,
            gauth_secret_type=os.getenv("GAUTH_SECRET_TYPE", "").strip() or None,
            gauth_scopes=(
                os.getenv("GAUTH_SCOPES", "").strip().split(",")
                if os.getenv("GAUTH_SCOPES")
                else None
            ),
            gauth_customer_id=os.getenv("GAUTH_CUSTOMER_ID", "").strip() or None,
            gauth_project_id=os.getenv("GAUTH_PROJECT_ID", "").strip() or None,
            ad_use_ssl=os.getenv("AD_USE_SSL", "true").strip().lower() == "true",
            ad_port=int(os.getenv("AD_PORT", "636").strip()),
            group_name_prefix=os.getenv("GROUP_NAME_PREFIX", "AWS_").strip(),
        )
        config.validate()
        return config

    def load_credential_from_secret_manager(self, p_id, key, ver, type="json") -> dict:
        client = secretmanager.SecretManagerServiceClient()
        project_id = p_id
        secret_id = key
        secret_version = ver
        secret_key_name = (
            f"projects/{project_id}/secrets/{secret_id}/versions/{secret_version}"
        )
        response = client.access_secret_version(request={"name": secret_key_name})

        if type == "json":
            return json.loads(response.payload.data.decode("UTF-8"))
        else:
            return response.payload.data.decode("UTF-8")

    def get_service_account_info(self) -> dict:
        """
        Returns the service account JSON content, either from file path or inline env.
        Raises ValueError if none provided.
        """
        if self.service_account_json_path:
            # Lazy import to keep module import side-effects small.
            import json as _json

            with open(self.service_account_json_path, "r", encoding="utf-8") as f:
                return _json.load(f)
        if self.service_account_json_inline:
            return json.loads(self.service_account_json_inline)
        if self.service_account_secret_manager:
            if (
                not self.gauth_project_id
                or not self.gauth_secret_key_id
                or not self.gauth_secret_ver
            ):
                raise ValueError(
                    "Service account secret manager requires GAUTH_PROJECT_ID, "
                    "GAUTH_SECRET_KEY_ID, and GAUTH_SECRET_VER to be set."
                )
            return self.load_credential_from_secret_manager(
                self.gauth_project_id,
                self.gauth_secret_key_id,
                self.gauth_secret_ver,
                self.gauth_secret_type,
            )
        raise ValueError(
            "Service account credentials not found. Provide GOOGLE_APPLICATION_CREDENTIALS (path) "
            "or SERVICE_ACCOUNT_JSON (inline JSON)."
        )

    def validate(self) -> None:
        if not self.delegated_subject:
            raise ValueError(
                "Configu is missing; GOOGLE_DELEGATED_SUBJECT is required."
            )
        if not self.group_domain:
            raise ValueError("Configu is missing; GROUP_DOMAIN is required.")
