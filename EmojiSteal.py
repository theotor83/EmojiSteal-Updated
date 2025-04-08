from discord import Client, Intents
from discord.errors import HTTPException  # new import for handling HTTP errors
from rich.console import Console
from rich.table import Table
from rich.prompt import IntPrompt, Prompt, Confirm
from time import sleep
import sys
import aiohttp  # Added import for aiohttp
from PIL import Image  # added import for resizing
from io import BytesIO  # added import for BytesIO

console = Console()
intents = Intents.all()
client = Client(intents=intents)
console.clear()

console.print('[bold yellow]___________                  __.__  _________ __                .__  v1.0 ')
console.print('[bold yellow]\_   _____/ _____   ____    |__|__|/   _____//  |_  ____ _____  |  |  ')
console.print('[bold yellow] |    __)_ /     \ /  _ \   |  |  |\_____  \\   __\/ __ \\__  \ |  |  ')
console.print('[bold yellow] |        \  Y Y  (  <_> )  |  |  |/        \|  | \  ___/ / __ \|  |__')
console.print('[bold yellow]/_______  /__|_|  /\____/\__|  |__/_______  /|__|  \___  >____  /____/')
console.print('[bold yellow]        \/      \/      \______|          \/           \/     \/      ')
console.print()

token = console.input('[[cyan]?[/]]Enter your [cyan bold]user token[/] : [green]')

async def exit_code():
	console.log('Code exitted.')
	await client.close()
	sleep(1)
	sys.exit()

@client.event
async def on_ready():
	try:
		console.log(f'Successfully logged in as [green bold]{client.user}[/]')
		guild_count = len(client.guilds)
		with console.status('[bold green]Fetching guild list...') as status:
			sleep(1.5)
			guild_list = Table(title="[magenta bold]Guild List")
			guild_list.add_column('SRL_ID', justify='right', style='bold green', no_wrap=True)
			guild_list.add_column('Guild Name', style='dim')
			guild_list.add_column('Guild_ID', style='bold cyan',  no_wrap=True)
			i = 0
			for guild in client.guilds:
				guild_list.add_row(f'{i}', guild.name, f'{guild.id}')
				i += 1
			console.log('Fetched [bold green]guild list')
			console.print(guild_list)

		while True:
			source = IntPrompt.ask(f'[[cyan]?[/]]Enter [cyan bold]SRL_ID[/] of the guild [yellow bold]from[/] which to steal emojis [magenta bold](0-{guild_count - 1})[/]')
			if source >= 0 and source < guild_count:
				break
			console.print(f'[red]SRL_ID must be between 0 and {guild_count - 1}[/]')

		while True:
			sink = IntPrompt.ask(f'[[cyan]?[/]]Enter [cyan bold]SRL_ID[/] of the guild [yellow bold]to[/] which copy the emojis [magenta bold](0-{guild_count - 1})[/]')
			if sink >= 0 and sink < guild_count:
				break
			console.print(f'[red]SRL_ID must be between 0 and {guild_count - 1}[/]')

		source_guild = client.guilds[source]
		sink_guild = client.guilds[sink]
		if not sink_guild.me.guild_permissions.manage_emojis:
			console.print(f'[[bold red]ERROR[/]][red]You do not have permissions to manage emojis of guild \'{sink_guild.name}\'')
			await exit_code()

		with console.status(f'[bold green]Fetching emoji list for guild {source_guild.name}...') as status:
			sleep(1)
			emoji_list = Table(title="[magenta bold]Emoji List")
			emoji_list.add_column('SRL_ID', justify='right', style='bold green', no_wrap=True)
			emoji_list.add_column('Emoji Name', style='dim')
			emoji_list.add_column('Emoji_ID', style='cyan', no_wrap=True)
			emoji_list.add_column('Animated?')
			i = 0
			for emoji in source_guild.emojis:
				emoji_list.add_row(f'{i}', emoji.name, f'{emoji.id}', 'Yes' if emoji.animated else 'No')
				i += 1
			
			console.log(f'Fetched [bold green]emoji list[/] for [dim]{source_guild.name}')
			console.print(emoji_list)

		free_slots = sink_guild.emoji_limit - len(sink_guild.emojis)
		if free_slots == 0:
			console.print(f'[[bold red]ERROR[/]][red]Guild {sink_guild.name} has no free emoji slot!')
			await exit_code()

		console.print(f'Guild [bold green]{sink_guild.name}[/] has [bold green]{free_slots}[/] free emoji slots.')
		values = Prompt.ask('[[cyan]?[/]]Enter [bold yellow]coma-separated[/] values of [cyan bold]SRL_ID[/] of the emojis to steal [dim](TIP: Type all to steal all emojis)[/]', default='all')
		if values == 'all':
			emojis_to_steal = source_guild.emojis
		else:
			def to_emoji(index):
				return source_guild.emojis[int(index.strip())]
			emojis_to_steal = list(map(to_emoji, values.split(',')))

		if len(emojis_to_steal) > free_slots:
			console.print(f'[[bold red]ERROR[/]][red]Guild {sink_guild.name} does not have enough free emoji slots!')
			await exit_code()

		transaction = Table(title="[magenta bold]Steal Transactions")
		transaction.add_column('From',style='bold yellow')
		transaction.add_column('To', style='bold yellow')
		transaction.add_column('Emojis Stolen')
		def to_names(emoji):
			return emoji.name
		transaction.add_row(source_guild.name, sink_guild.name, '\n'.join(list(map(to_names ,emojis_to_steal))))
		console.print(transaction)

		if not Confirm.ask("[[cyan]?[/]]Apply transactions?", default=True):
			await exit_code()

		with console.status('[bold green]Stealing emojis...') as status:
			async with aiohttp.ClientSession() as session:
				for emoji in emojis_to_steal:
					async with session.get(str(emoji.url)) as response:
						image = await response.read()
						# Check and downsize image if larger than 262144 bytes (256KB)
						if len(image) > 262144 and not emoji.animated:
							im = Image.open(BytesIO(image))
							while True:
								buf = BytesIO()
								im.save(buf, format='PNG')
								new_image = buf.getvalue()
								if len(new_image) <= 262144:
									image = new_image
									break
								new_size = (int(im.width * 0.9), int(im.height * 0.9))
								if new_size[0] < 16 or new_size[1] < 16:  # fallback if too small to reduce further
									image = new_image
									break
								im = im.resize(new_size, Image.LANCZOS)
							if len(image) > 262144:
								console.print(f'Failed to resize {emoji.name}, skipping.')
								continue
					try:
						await sink_guild.create_custom_emoji(name=emoji.name, image=image, reason='Created using EmojiSteal script.')
						console.print(f'Emoji created: [bold green]{emoji.name}')
					except HTTPException as he:
						if he.code == 50138:
							console.print(f'Failed to create {emoji.name} due to size constraints, skipping.')
							continue
						else:
							raise

		console.log(f'[bold green]Completed stealing emojis!')
		console.print()
		console.print('[cyan]Thanks for using EmojiSteal script!')
		console.print('[cyan]Coded by @DarkGuy10 https://github.com/DarkGuy10/')
		console.print('[cyan]Updated by @theotor83 https://github.com/theotor83/')
		console.print('[i]Ehe te nanayo![/]')
		await exit_code()
	
	except Exception as e:
		console.log(f"[red]ERROR:[/] {e}")
		import traceback
		traceback.print_exc()
		await exit_code()

client.run(token)