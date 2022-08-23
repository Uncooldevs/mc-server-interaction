from argparse import ArgumentParser

from server_manager.server_manger import ServerManager


def main():
    parser = ArgumentParser(description='Server Manager')

    subparsers = parser.add_subparsers()

    parser.add_argument("--create", help="Create a new server", action="store_true")

    server_action = subparsers.add_parser("server", help="Server action")
    server_action.add_argument("sid", help="Sid of the server. Run `manager list` to get the sid")
    server_action.add_argument("action", help="Action to perform ['start', 'stop', 'kill']")

    parser.add_argument("--list-servers", action="store_true", help="List all servers")

    args = parser.parse_args()

    server_manager = ServerManager()

    if args.list_servers:
        servers = server_manager.get_servers()
        if not servers:
            print("No servers found")
            return
        for sid, server in servers.items():
            print(f"{sid}: {server.name}")
            return

    elif args.create:
        path = input("Enter path to server directory: ")
        version = input("Enter server version: ")
        name = input("Enter server name: ")

        server_manager.create_new_server(name, path, version)
        return

    elif args.subparser == "server":
        server = server_manager.get_server(args.sid)
        print(f"""
        Path: {server.path_data.base_path}
        Status: {server.get_status().name}
        """)
        return

    else:
        parser.print_help()


if __name__ == '__main__':
    main()