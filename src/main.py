from ad_reader import connect_to_ad, get_aws_groups


def main():
    conn = connect_to_ad()
    groups = get_aws_groups(conn)
    for group, members in groups.items():
        print(f"{group}:")
        for m in members:
            print(f"  - {m}")


if __name__ == "__main__":
    main()
