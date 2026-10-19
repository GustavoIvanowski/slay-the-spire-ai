#!/usr/bin/env python3
import sys
import json
import random

# to view logs, > tail -f /tmp/sts_ai_debug.log
# to clear logs, > rm /tmp/sts_ai_debug.log
LOG_FILE = "/tmp/sts_ai_debug.log"

# Which behavior drives the bot. Must be a key in BEHAVIORS (bottom of file).
BEHAVIOR = "random"

# Seed for the random behavior. Set to a fixed number to replay the same choices.
SEED = random.randrange(2**32)
rng = random.Random(SEED)

# Floor where the random bot skipped a card reward. Skipping sends us back to
# the combat reward screen with the card reward still listed, so we remember
# it to avoid reopening it forever.
skipped_card_floor = None


def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")


def send_command(command):
    print(command, flush=True)
    log(f">>> SENT: {command}")


# ---------- shared helpers ----------

def alive_monsters(combat_state):
    """Indices of monsters that can still be targeted."""
    return [i for i, m in enumerate(combat_state["monsters"]) if not m["is_gone"]]


def default_action(cmds):
    """Fallback for any screen a behavior doesn't handle: take the first option."""
    if "choose" in cmds:
        return "choose 0"
    for c in ("proceed", "skip", "return", "confirm", "leave"):
        if c in cmds:
            return c
    if "start" in cmds:
        return "start ironclad"
    return "state"


def take_all_rewards(g, cmds):
    """Collect every combat reward we can, then leave."""
    has_free_potion_slot = any(p["id"] == "Potion Slot" for p in g.get("potions", []))
    for index, reward in enumerate(g["screen_state"]["rewards"]):
        kind = reward["reward_type"]
        # a potion can't be picked up with full slots, it would loop forever
        if kind == "POTION" and not has_free_potion_slot:
            continue
        if kind == "CARD" and skipped_card_floor == g["floor"]:
            continue
        return f"choose {index}"
    return "proceed" if "proceed" in cmds else default_action(cmds)


# ---------- behavior: first ----------

def first_action(state):
    """Always take the first available option."""
    cmds = state.get("available_commands", [])
    g = state.get("game_state", {})

    if "play" in cmds:
        combat_state = g["combat_state"]
        alive = alive_monsters(combat_state)
        # play first playable card on first attackable enemy
        for index, card in enumerate(combat_state["hand"], start=1):
            if card["is_playable"]:
                if card["has_target"]:
                    return f"play {index} {alive[0]}"
                return f"play {index}"
        # if no more cards playable, end
        return "end"
    if "end" in cmds:
        return "end"
    if g.get("screen_type") == "COMBAT_REWARD":
        return take_all_rewards(g, cmds)
    return default_action(cmds)


# ---------- behavior: random ----------

def random_combat_action(g, cmds):
    """Play a random playable card or use a random potion, on a random enemy.
    Only ends the turn when nothing else can be done."""
    combat_state = g["combat_state"]
    alive = alive_monsters(combat_state)
    options = []

    if "play" in cmds:
        for index, card in enumerate(combat_state["hand"], start=1):
            if card["is_playable"]:
                if card["has_target"]:
                    options.append(f"play {index} {rng.choice(alive)}")
                else:
                    options.append(f"play {index}")

    if "potion" in cmds:
        for slot, potion in enumerate(g.get("potions", [])):
            if potion["can_use"]:
                if potion["requires_target"]:
                    options.append(f"potion use {slot} {rng.choice(alive)}")
                else:
                    options.append(f"potion use {slot}")

    return rng.choice(options) if options else "end"


def random_card_reward(g, cmds):
    """Pick a random card, with skipping as one more option."""
    global skipped_card_floor
    options = [f"choose {i}" for i in range(len(g["screen_state"]["cards"]))]
    if "skip" in cmds:
        options.append("skip")
    choice = rng.choice(options)
    if choice == "skip":
        skipped_card_floor = g["floor"]
    return choice


def random_action(state):
    """Random combat, map and reward choices. Other screens take the first option."""
    cmds = state.get("available_commands", [])
    g = state.get("game_state", {})
    screen = g.get("screen_type")

    if "play" in cmds or "end" in cmds:
        return random_combat_action(g, cmds)
    if screen == "MAP" and "choose" in cmds:
        return f"choose {rng.randrange(len(g['choice_list']))}"
    if screen == "COMBAT_REWARD":
        return take_all_rewards(g, cmds)
    if screen == "CARD_REWARD" and "choose" in cmds:
        return random_card_reward(g, cmds)
    return default_action(cmds)


BEHAVIORS = {
    "first": first_action,
    "random": random_action,
}


def main():
    log("=== main.py started, waiting for CommunicationMod ===")
    log(f"=== behavior: {BEHAVIOR}, seed: {SEED} ===")
    choose_action = BEHAVIORS[BEHAVIOR]
    # Handshake: CommunicationMod sends nothing until we say we're ready.
    send_command("ready")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            state = json.loads(line)
        except json.JSONDecodeError:
            log("!!! Failed to parse JSON, skipping")
            continue

        # Dump the raw JSON, pretty-printed, so it's easy to read/explore.
        # CommunicationMod pushes a new state whenever the game changes, so no
        # reply is needed here (replying "state" would just echo it back in a loop).
        log(json.dumps(state, indent=2))
        if "error" in state:
            log(f"!!! ERROR: {state['error']}")
        if state.get("ready_for_command"):
            action = choose_action(state)
            send_command(action)


if __name__ == "__main__":
    main()
