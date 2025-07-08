import asyncio
import json
import os
import subprocess
import platform
import traceback
from telegram import Update
from asyncio.windows_events import WindowsProactorEventLoopPolicy
from bot.bot import TelegramBot
from llm.ollama import OllamaClient
from llm.google import GoogleClient
from llm.openai import OpenAIClient
from mcp_client.client import StdioMCPClient


async def register_mcp_servers(llm_selector):
    config_path = "config/mcp_servers.json"
    if not os.path.exists(config_path):
        print(f"MCP servers config file not found at {config_path}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    mcp_servers_config = config.get("mcpServers", {})

    for server_name, server_info in mcp_servers_config.items():
        server_type = server_info.get("type", "http")

        process = None
        if server_type == "stdio":
            command = server_info.get("command")
            args = server_info.get("args", [])
            env = server_info.get("env", {})

            if not command:
                print(f"Skipping Stdio MCP server '{server_name}': "
                      "'command' is missing.")
                continue

            print(f"Starting Stdio MCP server '{server_name}' with "
                  f"command: {command} {' '.join(args)}")
            try:
                process = await asyncio.create_subprocess_exec(
                    command,
                    *args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env={**os.environ, **env}
                )
            except Exception as e:
                print(f"Error starting Stdio MCP server '{server_name}': "
                      f"{e}\n{traceback.format_exc()}")
                continue

        try:
            client_instance = llm_selector.register_mcp_server(
                server_name, server_info, process
            )
            print(f"Successfully registered MCP server '{server_name}'.")

            if isinstance(client_instance, StdioMCPClient):
                async def read_stderr(proc, client_inst, name):
                    while True:
                        line = await proc.stderr.readline()
                        if not line:
                            break
                        try:
                            decoded_line = line.decode('utf-8').strip()
                        except UnicodeDecodeError:
                            # Fallback for problematic encodings
                            decoded_line = line.decode(
                                'utf-8', errors='replace').strip()
                        print(f"[{name} STDERR]: {decoded_line}")
                        await client_inst.add_stderr_message(decoded_line)

                asyncio.create_task(read_stderr(
                    process, client_instance, server_name))
            elif server_type == "http" or server_type == "sse":
                server_url = server_info.get(
                    "url") or server_info.get("server_url")
            # Wait for the MCP server to be ready
            print(f"Waiting for MCP server '{server_name}' to be ready...")
            is_ready = await client_instance.wait_until_ready(timeout=60)
            if is_ready:
                print(f"MCP server '{server_name}' is ready.")
            else:
                print(f"WARNING: MCP server '{server_name}' did not become ready "
                      f"within the specified timeout (60 seconds). "
                      "This might indicate a configuration issue or a problem "
                      "with the server itself. Functionality relying on this "
                      "server may be limited or unavailable. Please check "
                      "the server's logs and configuration.")

        except Exception as e:
            print(f"Error registering MCP server '{server_name}': "
                  f"{e}\n{traceback.format_exc()}")


async def setup_bot_application():
    bot = TelegramBot()

    bot.llm_selector.provider_manager.register_provider(OllamaClient)
    bot.llm_selector.provider_manager.register_provider(GoogleClient)
    bot.llm_selector.provider_manager.register_provider(OpenAIClient)

    await register_mcp_servers(bot.llm_selector)
    return bot.application


async def main():
    application = await setup_bot_application()
    if application is None:
        print("Ошибка: Не удалось инициализировать приложение бота. "
              "Завершение работы.")
        return

    print("Бот запущен...")

    try:
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

        print("Бот работает и ждет команд... Нажмите Ctrl+C для остановки.")

        await asyncio.Future()

    finally:
        print("\nПолучен сигнал остановки, корректно завершаем работу...")
        if application.updater and application.updater.running:
            await application.updater.stop()
        if application.running:
            await application.stop()
        print("Ресурсы бота успешно освобождены.")


if __name__ == "__main__":
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(WindowsProactorEventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")
        traceback.print_exc()
