"""
Dynamic AI Text-Adventure Engine
================================
An LLM acts as the Game Master. Python owns the mechanics (health,
inventory, location); the model owns the narrative and interprets
freeform player actions.

Setup:
    pip install anthropic
    export ANTHROPIC_API_KEY="sk-ant-..."

Run:
    python adventure_engine.py

The model is forced to reply in strict JSON:
    {
        "narrative":     "...story text shown to the player...",
        "state_updates": {
            "inventory_add":    ["item", ...],   # optional
            "inventory_remove": ["item", ...],   # optional
            "health_change":    -10,             # optional int
            "location":         "new location"   # optional
        }
    }
"""

import json
import sys

from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"
MAX_JSON_RETRIES = 2  # re-ask the model this many times if JSON is invalid

# ---------------------------------------------------------------------------
# Game state — Python is the source of truth, never the model.
# ---------------------------------------------------------------------------
game_state = {
    "health": 100,
    "location": "a dimly lit office",
    "inventory": ["empty tea cup", "notepad"],
}

SYSTEM_PROMPT = """You are the Game Master for a noir-flavored text adventure.
The player is a weary private detective. Keep the tone moody, wry, and vivid,
and keep each narrative beat to 2-5 sentences. Never speak for the player.

You will receive the current game state and the player's action. Respond to
ANY player input, however unexpected, but keep consequences grounded in the
provided state (the player can only use items they actually carry).

CRITICAL OUTPUT RULES:
- Reply with ONLY a single valid JSON object. No markdown fences, no preamble,
  no trailing commentary.
- The JSON must contain exactly two top-level keys:
  "narrative": string — the story text to show the player.
  "state_updates": object — the mechanical changes, using only these optional
      keys: "inventory_add" (list of strings), "inventory_remove" (list of
      strings), "health_change" (integer, negative for damage), "location"
      (string).
- If nothing mechanical changes, "state_updates" must be an empty object {}.
- Only remove inventory items that exist in the player's inventory.
"""


def build_user_message(player_action: str) -> str:
    """Bundle the player's action with the authoritative game state."""
    return json.dumps(
        {
            "current_state": game_state,
            "player_action": player_action,
        },
        indent=2,
    )


def call_game_master(client: Anthropic, player_action: str) -> dict | None:
    """
    Send the action + state to the model and return the parsed JSON dict.
    Retries with an error notice if the model returns invalid JSON.
    Returns None if all retries fail.
    """
    messages = [{"role": "user", "content": build_user_message(player_action)}]

    for attempt in range(1 + MAX_JSON_RETRIES):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=1000,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
        except Exception as exc:  # network / auth / rate-limit errors
            print(f"\n[!] API error: {exc}")
            return None

        raw = response.content[0].text.strip()

        # Be forgiving if the model wraps output in code fences anyway.
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            data = json.loads(raw)
            if "narrative" in data and "state_updates" in data:
                return data
            raise ValueError("missing required keys")
        except (json.JSONDecodeError, ValueError) as exc:
            if attempt < MAX_JSON_RETRIES:
                # Feed the bad output back and demand a correction.
                messages.append({"role": "assistant", "content": raw})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Your previous reply was not valid ({exc}). "
                            "Respond again with ONLY the required JSON object "
                            'containing "narrative" and "state_updates".'
                        ),
                    }
                )
            else:
                print("\n[!] The Game Master kept returning invalid JSON. "
                      "Skipping this turn.")
                return None
    return None


def apply_state_updates(updates: dict) -> None:
    """Mutate the local game state. Python validates everything."""
    if not isinstance(updates, dict):
        return

    for item in updates.get("inventory_add", []) or []:
        if isinstance(item, str) and item not in game_state["inventory"]:
            game_state["inventory"].append(item)

    for item in updates.get("inventory_remove", []) or []:
        if item in game_state["inventory"]:
            game_state["inventory"].remove(item)

    delta = updates.get("health_change", 0)
    if isinstance(delta, int):
        game_state["health"] = max(0, min(100, game_state["health"] + delta))

    loc = updates.get("location")
    if isinstance(loc, str) and loc.strip():
        game_state["location"] = loc.strip()


def print_status() -> None:
    inv = ", ".join(game_state["inventory"]) or "nothing"
    print(f"\n  [HP: {game_state['health']} | "
          f"Location: {game_state['location']} | Carrying: {inv}]")


def main() -> None:
    client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment

    print("=" * 60)
    print("  THE LAST CUP — an AI text adventure")
    print("  (type 'quit' to leave, 'status' to check yourself)")
    print("=" * 60)
    print(
        "\nThe office is dim, lit by a desk lamp with opinions about "
        "flickering. Rain taps the window like an impatient client. "
        "You drain the last of your tea — cold, bitter, appropriate — "
        "and set the cup down on a stack of unpaid bills."
    )
    print_status()

    while game_state["health"] > 0:
        try:
            action = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nThe city swallows you whole. Goodbye.")
            break

        if not action:
            continue
        if action.lower() in ("quit", "exit"):
            print("You hang up your hat. Case closed.")
            break
        if action.lower() == "status":
            print_status()
            continue

        result = call_game_master(client, action)
        if result is None:
            continue

        print(f"\n{result['narrative']}")
        apply_state_updates(result.get("state_updates", {}))
        print_status()

    if game_state["health"] <= 0:
        print("\nYour vision fades. Somewhere, a saxophone plays. GAME OVER.")

    sys.exit(0)


if __name__ == "__main__":
    main()
