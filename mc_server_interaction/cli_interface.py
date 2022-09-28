"""
This is not for productive usage
"""

import asyncio
import logging

import aioconsole

from mc_server_interaction.exceptions import DirectoryNotEmptyException
from mc_server_interaction.interaction.models import ServerStatus
from mc_server_interaction.log import set_console_log_level
from mc_server_interaction.manager import ServerManager

set_console_log_level(logging.DEBUG)

menu = """
1. Create Server
2. List available Servers
3. Show server info
4. Exit App
"""


class Options:
    CREATE = 1
    LIST = 2
    SHOW = 3
    EXIT = 4


async def main():
    server_manager = ServerManager()
    await server_manager.available_versions.load()
    while True:
        print(menu)
        try:
            input_text = int(await aioconsole.ainput("Select option: "))
        except ValueError:
            print("Not a valid input")
            continue

        if input_text == Options.LIST:
            servers = server_manager.get_servers()
            if not servers:
                print("No servers found")
            for sid, server in servers.items():
                print(f"{server.server_config.name} : sid:{sid}")

        elif input_text == Options.CREATE:
            while True:
                version = await aioconsole.ainput(
                    "Enter version ('help' to list all available versions(many), Leave empty to use latest): "
                )
                if version == "help":
                    print(
                        " ".join(
                            list(
                                server_manager.available_versions.available_versions.keys()
                            )
                        )
                    )
                    continue
                break
            if version == "":
                version = "latest"
            while True:
                name = await aioconsole.ainput("Enter server name: ")
                if name == "":
                    print("Name cannot be empty")
                    continue
                break

            print("Creating server...")
            try:
                new_sid, new_server = await server_manager.create_new_server(
                    name, version
                )
                await server_manager.install_server(new_sid)
            except DirectoryNotEmptyException:
                pass
            else:
                print("Server created successfully")
        elif input_text == Options.SHOW:
            servers = server_manager.get_servers()
            if not servers:
                print("No servers found")
                continue
            for sid, server in servers.items():
                print(f"{sid}: {server.server_config.name}")

            sid = await aioconsole.ainput("Enter server id: ")
            server = server_manager.get_server(sid)
            if not server:
                print("Server not found")
                continue

            while True:

                print(
                    f"""
Path: {server.server_config.path}
Status: {server.status.name}
                """
                )
                action = "Start" if server.status == ServerStatus.STOPPED else "Stop"
                print(
                    f"""
1. {action} Server
2. Delete Server
3. Send command
4. Go back            
                """
                )
                user_input = await aioconsole.ainput("Select option: ")
                if user_input == "1":
                    print(server.status)
                    if server.status == ServerStatus.STOPPED:
                        await server.start()
                    else:
                        await server.stop()

                    print("Server started")
                elif user_input == "2":
                    server_manager.delete_server(sid)
                    print("Server deleted")
                    break
                elif user_input == "3":
                    await server.send_command(
                        await aioconsole.ainput("Enter command: ")
                    )
                elif user_input == "4":
                    break

        elif input_text == Options.EXIT:
            await server_manager.stop_all_servers()
            break


def run_app():
    asyncio.run(main())


if __name__ == "__main__":
    run_app()
