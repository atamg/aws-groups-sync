import logging

# from .ad_reader import connect_to_ad, get_aws_groups
from .config import Config
from .utils import setup_logging
from .google_directory import GoogleDirectory

# from .sync_service import SyncService


def main():
    try:
        # Setup logging
        setup_logging("info")
        LOGGER = logging.getLogger(__name__)

        # Load configuration
        cfg = Config.load()
        LOGGER.info("Configuration loaded successfully")

        def build_google_directory(cfg: Config) -> GoogleDirectory:
            creds_info = cfg.get_service_account_info()
            return GoogleDirectory(
                creds_info=creds_info,
                delegated_subject=cfg.delegated_subject,
                google_api_scopes=cfg.gauth_scopes,
            )

        # Initialize Google Directory service

        gd = build_google_directory(cfg)
        if gd:
            LOGGER.info("Google Directory service initialized successfully")

        """"
        cred = cfg.get_service_account_info()
        print(f"Loaded credentials: {cred}")
        
        conn = connect_to_ad(cfg)
        groups = get_aws_groups(conn, cfg)
        for group, members in groups.items():
            print(f"{group}:")
            for m in members:
                print(f"  - {m}")
        """
    except Exception as e:
        print(f"An error occurred: {e}")
        exit(1)


if __name__ == "__main__":
    main()
