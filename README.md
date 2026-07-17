# The Last Cup — an AI Text-Adventure Engine

A terminal-based text adventure where an LLM acts as the Game Master. Instead
of hard-coding branching `if/else` paths for every possible player action,
Python owns the game *mechanics* (health, inventory, location) while the model
improvises the *narrative* and interprets freeform input — you can type
anything, and the game responds.

```
> search the desk drawers

The top drawer sticks, then gives. Inside: a matchbook from a bar
that burned down in '52, and a brass key with no label. The kind
of key that opens exactly one door in this city.

  [HP: 100 | Location: a dimly lit office | Carrying: empty tea cup, notepad, brass key]
```

## Architecture

![Architecture diagram](docs/architecture.png)

The core design decision: **Python is the referee, not the model.**

1. Each turn, the player's freeform action is bundled with the authoritative
   game state into a structured prompt.
2. The model is instructed (via system prompt) to reply in **strict JSON**
   with exactly two keys: `narrative` (story text) and `state_updates`
   (mechanical changes: inventory add/remove, health delta, location).
3. A parsing layer validates the response. Invalid JSON is fed back to the
   model with a correction demand and retried up to 2 times before the turn
   is skipped — the game never crashes on a malformed reply.
4. `apply_state_updates()` enforces the rules in Python: no duplicate items,
   no removing items the player doesn't carry, health clamped to 0–100.
   The model can *suggest* mechanics; it cannot break them.

This separation prevents the classic failure mode of LLM games — the model
"forgetting" your inventory or hallucinating items — because state never
lives in the model's memory at all.

## Setup

Requires Python 3.10+ and an [Anthropic API key](https://console.anthropic.com).

```bash
git clone https://github.com/YOUR_USERNAME/ai-text-adventure.git
cd ai-text-adventure
pip install -r requirements.txt

# Mac / Linux
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
# Windows PowerShell
$env:ANTHROPIC_API_KEY="sk-ant-your-key-here"

python adventure_engine.py
```

In-game commands: type anything to act, `status` to check your stats,
`quit` to exit.

## Customizing

The entire tone and genre of the game live in one place: the `SYSTEM_PROMPT`
string at the top of `adventure_engine.py`. Change "noir detective" to
"derelict space station" or "cursed fantasy tavern" and the whole game
reskins itself — no logic changes required.

Other easy knobs:

- `MODEL` — swap in any Claude model string (e.g. `claude-sonnet-5`)
- `game_state` — change the starting health, location, and inventory
- `MAX_JSON_RETRIES` — how forgiving the parser is

## Roadmap

- [ ] Save/load game state to a JSON file
- [ ] Conversation-history window so the GM remembers earlier scenes
- [ ] `game_over` flag in `state_updates` so the model can end story arcs
- [ ] Unit tests for `apply_state_updates()`

## How it was built

Initial engine scaffolded with AI assistance from a structured spec
(architecture and JSON contract designed first, code second), then extended
and maintained by hand. The architecture diagram in `docs/` reflects the
original design.

## License

MIT — see [LICENSE](LICENSE).
