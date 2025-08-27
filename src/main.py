import logging

from .ad_reader import ADconnection
from .config import Config
from .utils import setup_logging
from .google_directory import GoogleDirectory
from .sync_service import SyncService


def build_google_directory(cfg: Config) -> GoogleDirectory:
    creds_info = cfg.get_service_account_info()
    return GoogleDirectory(
        creds_info=creds_info,
        delegated_subject=cfg.delegated_subject,
        google_api_scopes=cfg.gauth_scopes,
    )


def main():
    try:
        # Setup logging
        setup_logging("debug")
        LOGGER = logging.getLogger(__name__)

        # Load configuration
        cfg = Config.load()
        LOGGER.info("Configuration loaded successfully")

        # Initialize Google Directory service

        gd = build_google_directory(cfg)
        if gd:
            LOGGER.info("Google Directory service initialized successfully")

        svc = SyncService(
            gd,
            group_domain=cfg.group_domain,
            customer_id=cfg.gauth_customer_id,
            group_name_prefix=cfg.group_name_prefix,
        )
        LOGGER.info("SyncService initialized successfully")

        cfg.get_service_account_info()

        ad = ADconnection(cfg)
        groups = ad.get_ad_groups(cfg)
        # ad_group_name="AWS_Additionalservice-Service_PowerUser"

        LOGGER.info("Fetched %d groups from AD", len(groups))

        # Convert lists to sets for easier membership operations

        ad_groups = {k: set(v) for k, v in groups.items()}

        svc.union_update_group_members(ad_groups)

        LOGGER.info("Group synchronization completed successfully")

    except Exception as e:
        print(f"An error occurred: {e}")
        exit(1)


if __name__ == "__main__":
    main()
