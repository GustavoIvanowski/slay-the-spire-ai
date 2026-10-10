# slay-the-spire-ai

A bot that plays [Slay the Spire](https://store.steampowered.com/app/646570/Slay_the_Spire/) on its own. It reads the game state over [CommunicationMod](https://github.com/ForgottenArbiter/CommunicationMod) and sends back commands.

## About this project

This is a learning project. I'm building it together with [Claude](https://claude.ai) (Anthropic's AI assistant) and using it as a way to learn:

- how to work with an AI collaborator on a real codebase: asking questions, debugging, and reviewing what it suggests,
- how a game exposes its state to an outside program, and how to write an agent loop around it,
- and, over time, the game AI techniques listed under [future goals](#future-goals): reinforcement learning, search, and planning.

The aim is to understand every piece, not just to get a bot that wins. So the code stays simple and readable, and gets more capable one step at a time.

## Requirements

- **Slay the Spire** (Steam)
- **Python 3.12+** (the script uses only the standard library)
- These Steam Workshop mods:

| Mod | Why it's needed |
|---|---|
| [ModTheSpire](https://steamcommunity.com/sharedfiles/filedetails/?id=1605060445) | Mod loader. Launch the game through it. |
| [BaseMod](https://steamcommunity.com/sharedfiles/filedetails/?id=1605833019) | Modding API that CommunicationMod depends on |
| [CommunicationMod](https://steamcommunity.com/sharedfiles/filedetails/?id=2131373661) | Starts the bot and passes JSON game state and text commands over stdin/stdout |

[StSLib](https://steamcommunity.com/sharedfiles/filedetails/?id=1609158507) is optional. CommunicationMod doesn't need it, but many other mods do.

## Setup

1. Subscribe to the mods above in the Steam Workshop.
2. Launch Slay the Spire and choose **Play with Mods**. In the ModTheSpire window, enable BaseMod and CommunicationMod.
3. Launch once so CommunicationMod creates its config file, then close the game.
4. Edit the CommunicationMod config file:
   - macOS: `~/Library/Preferences/ModTheSpire/CommunicationMod/config.properties`
   - Windows: `%LOCALAPPDATA%\ModTheSpire\CommunicationMod\config.properties`

   Point `command` at your Python interpreter and this repo's script. Use absolute paths:

   ```properties
   command=/path/to/python3 /path/to/slay-the-spire-ai/scripts/main.py
   runAtGameStart=true
   ```

5. Launch the game with mods. The bot starts automatically.

## How it works

CommunicationMod runs `scripts/main.py` as a subprocess:

1. On startup, the script prints `ready`. This is the handshake. The mod sends nothing until it gets it.
2. Whenever the game is waiting for input, the mod writes the full game state as one line of JSON to the script's stdin.
3. The script picks an action and prints **one** command to stdout, such as `play 1 0`, `end`, `choose 0` or `proceed`.

Anything printed to stdout is treated as a command, so debug output goes to a log file instead:

```sh
tail -f /tmp/sts_ai_debug.log   # watch states and commands live
rm /tmp/sts_ai_debug.log        # clear the log
```

If the script crashes, its Python errors end up in `communication_mod_errors.log` in the game's install folder.

### Current behavior

The bot is a deliberately naive baseline. It:
- plays the first playable card in hand, aimed at the first living enemy,
- ends the turn when no card can be played,
- takes the first option on every reward, event and map screen,
- starts a new Ironclad run from the main menu.

It can't win anything yet. Its job is to make sure the loop runs end to end without getting stuck.

## Roadmap

### Near term: rule-based play
- [x] CommunicationMod handshake and state logging
- [x] Baseline bot that takes the first available action
- [ ] Combat heuristics: block against incoming attacks, focus the lowest-HP enemy, spend energy efficiently
- [ ] Card reward choices (pick or skip based on deck needs)
- [ ] Map pathing (balance elites, rest sites, shops)
- [ ] Event, shop and rest-site handling
- [ ] Run statistics: floor reached, cause of death, win rate

### Future goals

**Planning and search**
- Simulate a combat turn so the bot can compare possible card orders before playing
- Search-based combat (e.g. Monte Carlo Tree Search or beam search over each turn's actions)
- Longer-range planning for pathing and deck building

**Reinforcement learning**
- Turn game states into feature vectors an RL agent can use
- Train agents first on narrow sub-problems (single combats, card choices), then on full runs
- Compare learned policies against the rule-based and search-based bots
- Possibly use a headless simulator for faster training than the real game allows

## Project layout

```
scripts/main.py   # the bot: handshake, state loop, decision logic
```

## Acknowledgments

- [ForgottenArbiter/CommunicationMod](https://github.com/ForgottenArbiter/CommunicationMod), which made this project possible. Its README documents the full command protocol.
- Mega Crit, for making Slay the Spire.
- Built with help from Claude.
