import os
import asyncio
import discord

from dotenv import load_dotenv

from utils import default


def main():
    load_dotenv()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    isTest = False

    intent = discord.Intents.all()

    client = default.DiscordBot(
        command_prefix="$", help_command=None, case_insensitive=True, intents=intent, loop=loop, isTest = isTest
    )

    TOKEN = os.environ["BOT_TEST_TOKEN"] if isTest else os.environ["BOT_TOKEN"]
    
    # try:
    #     loop.run_until_complete(client.start(TOKEN))
    # finally:
    #     loop.close()

    loop.create_task(client.run(TOKEN))
    loop.run_forever()

if __name__ == "__main__":
    # yappi.start()
    main()
    # yappi.stop()
    # threads = yappi.get_thread_stats()
    # for thread in threads:
    #     print(
    #         "Function stats for (%s) (%d)" % (thread.name, thread.id)
    #     )  # it is the Thread.__class__.__name__
    #     yappi.get_func_stats(ctx_id=thread.id).print_all()
