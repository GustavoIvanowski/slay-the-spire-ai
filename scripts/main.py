#!/usr/bin/env python3
import sys
import json

# to view logs, > tail -f /tmp/sts_ai_debug.log
# to clear logs, > rm /tmp/sts_ai_debug.log
LOG_FILE = "/tmp/sts_ai_debug.log"


def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")


def send_command(command):
    print(command, flush=True)
    log(f">>> SENT: {command}")

def choose_action(state):
    cmds = state.get("available_commands", [])
    g = state.get("game_state", {})

    if "play" in cmds:
        combatState = g["combat_state"]
        alive = [i for i, m in enumerate(combatState["monsters"]) if not m["is_gone"]]
        for index, card in enumerate(combatState["hand"], start=1):
            # play first playable card on first attackable enemy
            if card["is_playable"]:
                if card["has_target"]:
                    return f"play {index} {alive[0]}"
                return f"play {index}"
            # if no more cards playable, end
            return "end"
    if "end" in cmds:
        return "end"
    if "choose" in cmds:
        return "choose 0"
    for c in ("proceed", "skip", "return", "confirm", "leave"):
        if c in cmds:
            return c
    if "start" in cmds:
        return "start ironclad"
    return "state"

def main():
    log("=== main.py started, waiting for CommunicationMod ===")
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
            log(f"!!! ERROR: {state["error"]}")
        if state.get("ready_for_command"):
            action = choose_action(state)
            send_command(action)


if __name__ == "__main__":
    main()


