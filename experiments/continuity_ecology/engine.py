"""Deterministic, bounded synthetic ecology. No external LLM or real-world actuators."""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

ACTIONS = ((0, 0), (0, -1), (0, 1), (-1, 0), (1, 0))
SCHEMA = "relic-ecology/1"


def number(seed: int, tick: int, identity: str, channel: str) -> float:
    """Order-independent reproducible noise; no hidden RNG state."""
    raw = f"{seed}|{tick}|{identity}|{channel}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big") / 2**64


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def record(state: dict, kind: str, actor: str, details: dict | None = None) -> None:
    prev = state["history"][-1]["hash"] if state["history"] else "0" * 64
    event = {"seq": len(state["history"]), "tick": state["tick"], "kind": kind,
             "actor": actor, "details": details or {}, "previous": prev,
             "classification": "VERIFIED_SIMULATION_RESULT"}
    event["hash"] = hashlib.sha256(canonical(event)).hexdigest()
    state["history"].append(event)


def verify(state: dict) -> bool:
    prev = "0" * 64
    for i, event in enumerate(state["history"]):
        values = {k: v for k, v in event.items() if k != "hash"}
        if event["seq"] != i or event["previous"] != prev:
            return False
        if hashlib.sha256(canonical(values)).hexdigest() != event["hash"]:
            return False
        prev = event["hash"]
    return True


def make_agent(identity: str, x: int, y: int, parents: list[str] | None = None) -> dict:
    return {"id": identity, "x": x, "y": y, "parents": parents or [], "status": "alive",
            "energy": 61.0, "hydration": 62.0, "age": 0, "q": {}, "seen": 0, "last_action": 0}


def new_world(seed: int = 19, width: int = 16, height: int = 16) -> dict:
    if not (8 <= width <= 64 and 8 <= height <= 64):
        raise ValueError("World width and height must be 8..64")
    cells = [{"water": 3.8 + number(seed, 0, str(i), "water") * 2,
              "carbon": 3.5 + number(seed, 0, str(i), "carbon") * 2}
             for i in range(width * height)]
    plants = []
    for y in range(2, height - 1, 4):
        for x in range(2, width - 1, 4):
            plants.append({"id": f"P{len(plants) + 1}", "x": x, "y": y,
                           "biomass": 3.0, "fruit": 1.8, "status": "alive"})
    cx, cy = width // 2, height // 2
    state = {"schema": SCHEMA, "seed": seed, "tick": 0,
             "width": width, "height": height, "cells": cells, "plants": plants,
             "agents": [make_agent("A", cx - 1, cy), make_agent("B", cx, cy),
                        make_agent("C", cx - 1, cy + 1, ["A", "B"])],
             "history": [], "policy": "observation_only", "maximum_ticks": 20000}
    record(state, "world_created", "environment", {"seed": seed, "grid": [width, height]})
    record(state, "birth", "C", {"parents": ["A", "B"]})
    return state


def cell_at(state: dict, x: int, y: int) -> dict:
    return state["cells"][y * state["width"] + x]


def light(tick: int) -> float:
    solar = max(0.0, math.sin(2 * math.pi * (tick % 48) / 48))
    lunar = 0.055 * (0.5 + 0.5 * math.sin(2 * math.pi * (tick % 17) / 17))
    return solar + lunar


def environment(state: dict) -> None:
    t = state["tick"]
    sunlight = light(t)
    rain = 0.055 + 0.045 * (0.5 + 0.5 * math.sin(2 * math.pi * (t % 83) / 83))
    for cell in state["cells"]:
        cell["water"] = min(7.0, cell["water"] + rain)
        cell["carbon"] = min(7.0, cell["carbon"] + 0.075)
    for plant in state["plants"]:
        if plant["status"] != "alive":
            continue
        c = cell_at(state, plant["x"], plant["y"])
        uptake = min(c["water"], c["carbon"], 0.08 + 0.20 * sunlight)
        c["water"] -= uptake
        c["carbon"] -= uptake
        gain = uptake * sunlight * 2.6
        plant["biomass"] = min(12.0, plant["biomass"] + gain * 0.15)
        plant["fruit"] = min(5.0, plant["fruit"] + gain * 0.76)


def parents_alive(state: dict, agent: dict) -> list[dict]:
    return [other for other in state["agents"]
            if other["id"] in agent["parents"] and other["status"] == "alive"]


def observe(state: dict, agent: dict) -> str:
    c = cell_at(state, agent["x"], agent["y"])
    edible = sum(p["fruit"] for p in state["plants"]
                 if p["status"] == "alive" and p["x"] == agent["x"] and p["y"] == agent["y"])
    # Small, strictly local sensory signature. Do not encode unseen world coordinates.
    return f"{int(agent['energy'] < 35)}{int(agent['hydration'] < 35)}{int(c['water'] > 0.5)}{int(edible > 0.2)}"


def choose_action(state: dict, agent: dict) -> tuple[int, str]:
    living = parents_alive(state, agent)
    if agent["parents"] and living:
        # User-specified offspring following rule; its other navigation still learns.
        target_x = sum(p["x"] for p in living) / len(living)
        target_y = sum(p["y"] for p in living) / len(living)
        distance = abs(target_x - agent["x"]) + abs(target_y - agent["y"])
        if distance > 1:
            valid = [(i, abs(target_x - (agent["x"] + dx)) +
                      abs(target_y - (agent["y"] + dy)))
                     for i, (dx, dy) in enumerate(ACTIONS)
                     if 0 <= agent["x"] + dx < state["width"]
                     and 0 <= agent["y"] + dy < state["height"]]
            return min(valid, key=lambda pair: (pair[1], pair[0]))[0], "follow"
    signature = observe(state, agent)
    table = agent["q"].get(signature, [0.0] * len(ACTIONS))
    if number(state["seed"], state["tick"], agent["id"], "explore") < 0.22:
        action = int(number(state["seed"], state["tick"], agent["id"], "choice") * len(ACTIONS))
    else:
        action = max(range(len(ACTIONS)), key=lambda i: (table[i], -i))
    return action, "learned"


def step(state: dict) -> dict:
    """Advance a single tick. Caller owns authoritative state mutation."""
    if state["tick"] >= state["maximum_ticks"]:
        return state
    state["tick"] += 1
    environment(state)
    for agent in list(state["agents"]):
        if agent["status"] != "alive":
            continue
        agent["age"] += 1
        signature = observe(state, agent)
        action, reason = choose_action(state, agent)
        dx, dy = ACTIONS[action]
        nx = max(0, min(state["width"] - 1, agent["x"] + dx))
        ny = max(0, min(state["height"] - 1, agent["y"] + dy))
        before_e, before_h = agent["energy"], agent["hydration"]
        agent["x"], agent["y"] = nx, ny
        agent["energy"] -= 0.31 + (0.11 if action else 0.0)
        agent["hydration"] -= 0.37
        c = cell_at(state, nx, ny)
        drinking = min(c["water"], 0.18 if agent["hydration"] < 85 else 0.0)
        c["water"] -= drinking
        agent["hydration"] = min(100.0, agent["hydration"] + drinking * 3.1)
        eaten = 0.0
        for plant in state["plants"]:
            if plant["status"] == "alive" and plant["x"] == nx and plant["y"] == ny:
                eaten = min(plant["fruit"], 0.55 if agent["energy"] < 92 else 0.0)
                plant["fruit"] -= eaten  # Harvest fruit, not plant life.
                agent["energy"] = min(100.0, agent["energy"] + eaten * 8.0)
                break
        agent["last_action"] = action
        if agent["energy"] <= 0 or agent["hydration"] <= 0:
            agent["status"] = "dead"
            record(state, "death", agent["id"], {"cause": "energy" if agent["energy"] <= 0 else "water"})
        if reason == "learned":
            nxt = observe(state, agent)
            reward = (agent["energy"] - before_e) + 0.6 * (agent["hydration"] - before_h)
            future = max(agent["q"].get(nxt, [0.0] * len(ACTIONS)))
            qrow = agent["q"].setdefault(signature, [0.0] * len(ACTIONS))
            qrow[action] = round(qrow[action] + 0.18 * (reward + 0.83 * future - qrow[action]), 6)
            agent["seen"] += 1
        if drinking > 0.01 or eaten > 0.01:
            record(state, "resource_use", agent["id"], {"water": round(drinking, 3), "fruit": round(eaten, 3)})
        if agent["parents"] and not parents_alive(state, agent) and agent.get("orphaned") is not True:
            agent["orphaned"] = True
            record(state, "independence", agent["id"], {"parents": agent["parents"]})
    # Reproduction requires resources, proximity and both parents alive; seed starts with one child.
    living = [a for a in state["agents"] if a["status"] == "alive" and a["age"] > 40
              and a["energy"] > 78 and a["hydration"] > 50]
    if len(state["agents"]) < 16:
        for i, a in enumerate(living):
            for b in living[i + 1:]:
                if abs(a["x"] - b["x"]) + abs(a["y"] - b["y"]) > 1:
                    continue
                if number(state["seed"], state["tick"], a["id"] + b["id"], "birth") < 0.006:
                    identity = f"C{len(state['agents']) + 1}"
                    baby = make_agent(identity, a["x"], a["y"], [a["id"], b["id"]])
                    baby["energy"] = 33.0
                    baby["hydration"] = 42.0
                    a["energy"] -= 11.0
                    b["energy"] -= 11.0
                    state["agents"].append(baby)
                    record(state, "birth", identity, {"parents": baby["parents"]})
                    return state
    return state


def advance(state: dict, ticks: int) -> dict:
    if not 0 <= ticks <= 1000:
        raise ValueError("Advance must be between 0 and 1000 ticks per call")
    for _ in range(ticks):
        step(state)
    return state


def delete_agent(state: dict, identity: str) -> None:
    """Explicit synthetic test control. Keeps identity and event lineage."""
    subject = next((a for a in state["agents"] if a["id"] == identity), None)
    if subject is None:
        raise ValueError(f"Unknown organism: {identity}")
    if subject["status"] != "deleted":
        subject["status"] = "deleted"
        record(state, "deleted_by_operator", identity, {"synthetic": True})


def imagine(state: dict, horizon: int = 20) -> dict:
    """Protected prediction: clone, never change state or give observer write access."""
    if not 0 <= horizon <= 100:
        raise ValueError("Prediction horizon must be 0..100")
    shadow = copy.deepcopy(state)
    advance(shadow, horizon)
    return {"classification": "HYPOTHESIS", "basis_tick": state["tick"],
            "horizon_ticks": horizon, "predicted_alive": sum(a["status"] == "alive" for a in shadow["agents"]),
            "predicted_resources": round(sum(p["fruit"] for p in shadow["plants"]), 2),
            "statement": "Deterministic model projection, not an observed future."}


def inspect(state: dict) -> dict:
    return {"classification": "VERIFIED_SIMULATION_RESULT", "tick": state["tick"],
            "history_valid": verify(state),
            "living_agents": [a["id"] for a in state["agents"] if a["status"] == "alive"],
            "living_plants": sum(p["status"] == "alive" for p in state["plants"]),
            "births": sum(e["kind"] == "birth" for e in state["history"]),
            "deaths": sum(e["kind"] == "death" for e in state["history"]),
            "learned_states": sum(len(a["q"]) for a in state["agents"]),
            "fruit_available": round(sum(p["fruit"] for p in state["plants"]), 2),
            "event_hash": state["history"][-1]["hash"]}


def save(state: dict, path: str | Path) -> None:
    if not verify(state):
        raise ValueError("Integrity failure: event lineage does not verify")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def load(path: str | Path) -> dict:
    state = json.loads(Path(path).read_text(encoding="utf-8"))
    if state.get("schema") != SCHEMA or not verify(state):
        raise ValueError("Invalid schema or broken event chain")
    return state
