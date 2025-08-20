import logging

# from .ad_reader import connect_to_ad, get_aws_groups
from .config import Config
from .utils import setup_logging


def main():
    try:
        # Setup logging
        setup_logging("info")
        LOGGER = logging.getLogger(__name__)

        # Load configuration
        cfg = Config.load()
        LOGGER.info("Configuration loaded successfully")

        cred = cfg.get_service_account_info()
        print(f"Loaded credentials: {cred}")
        """
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
