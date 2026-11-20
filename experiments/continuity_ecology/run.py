"""Single operator entry point; stdlib only."""
import argparse
import json
from pathlib import Path

try:
    from .engine import advance, delete_agent, imagine, inspect, load, new_world, save
except ImportError:
    from engine import advance, delete_agent, imagine, inspect, load, new_world, save


def main() -> None:
    p = argparse.ArgumentParser(description="ReLiC synthetic autonomous ecology")
    p.add_argument("command", choices=("init", "tick", "inspect", "imagine", "delete"))
    p.add_argument("--state", default=str(Path(__file__).with_name("state.json")))
    p.add_argument("--ticks", type=int, default=12)
    p.add_argument("--seed", type=int, default=19)
    p.add_argument("--id", dest="identity")
    a = p.parse_args()
    path = Path(a.state)
    if a.command == "init":
        if path.exists():
            p.error("State already exists: refusing to erase history")
        state = new_world(seed=a.seed)
        save(state, path)
    else:
        state = load(path)
        if a.command == "tick":
            advance(state, a.ticks)
            save(state, path)
        elif a.command == "delete":
            if not a.identity:
                p.error("delete requires --id")
            delete_agent(state, a.identity)
            save(state, path)
    result = inspect(state)
    if a.command == "imagine":
        result["protected_projection"] = imagine(state, a.ticks)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
