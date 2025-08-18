from .ad_reader import connect_to_ad, get_aws_groups
from .config import Config


def main():
    cfg = Config.load()
    conn = connect_to_ad(cfg)
    groups = get_aws_groups(conn, cfg)
    for group, members in groups.items():
        print(f"{group}:")
        for m in members:
            print(f"  - {m}")


if __name__ == "__main__":
    main()
