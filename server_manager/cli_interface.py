import logging

from server_manager.server_manger import ServerManager

menu = """
1. Create Server
2. List available Servers
3. Show server info
"""

logging.basicConfig(
    format="[%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)


class Options:
    CREATE = 1
    LIST = 2
    SHOW = 3


def main():
    server_manager = ServerManager()
    while True:
        print(menu)
        try:
            input_text = int(input("Select option: "))
        except ValueError:
            print("Not a valid input")
            continue
        if input_text not in list(range(1, 4)):
            print("Selected option does not exist")
            continue

        if input_text == Options.LIST:
            servers = server_manager.get_servers()
            if not servers:
                print("No servers found")
            for sid, server in servers.items():
                print(f"{server.server_config.name} : sid:{sid}")

        elif input_text == Options.CREATE:
            while True:
                version = input(
                    "Enter version ('help' to list all available versions(many), Leave empty to use latest): ")
                if version == "help":
                    print(" ".join(list(server_manager.available_versions.available_versions.keys())))
                    continue
                break
            if version == "":
                version = server_manager.available_versions.get_latest_version()
            while True:
                name = input("Enter server name: ")
                if name == "":
                    print("Name cannot be empty")
                    continue
                break

            print("Creating server...")
            server_manager.create_new_server(name, version)

        elif input_text == Options.SHOW:
            servers = server_manager.get_servers()
            if not servers:
                print("No servers found")
                continue
            for sid, server in servers.items():
                print(f"{sid}: {server.server_config.name}")

            sid = input("Enter server id: ")
            server = server_manager.get_server(sid)
            if not server:
                print("Server not found")
                continue

            while True:

                print(f"""
Path: {server.server_config.path}
Status: {server.get_status().name}
                """)

                print("""
1. Start Server
2. Delete Server
3. Go back            
                """)
                user_input = input("Select option: ")
                if user_input == "1":
                    server_manager.start_server(sid)
                    print("Server started")
                elif user_input == "2":
                    server_manager.delete_server(sid)
                    print("Server deleted")
                    break
                elif user_input == "3":
                    break


if __name__ == '__main__':
    main()
