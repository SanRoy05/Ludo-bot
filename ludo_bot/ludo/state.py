from dataclasses import dataclass, field
from typing import List, Dict, Optional
import json

@dataclass
class Token:
    pos: int = 0      # 0-50 on track, 51-55 home path, 56 finished
    state: str = "home" # "home", "active", "finished"

@dataclass
class Player:
    user_id: int
    first_name: str
    color_index: int 
    tokens: List[Token] = field(default_factory=lambda: [Token() for _ in range(4)])
    is_active: bool = True

@dataclass
class GameState:
    chat_id: int
    players: List[Player]
    current_turn_index: int = 0
    dice_value: Optional[int] = None
    last_roll_time: float = 0
    is_lobby: bool = True
    winner: Optional[int] = None 
    match_id: Optional[str] = None
    tournament_id: Optional[str] = None
    
    def to_dict(self):
        return {
            "chat_id": self.chat_id,
            "players": [
                {
                    "user_id": p.user_id,
                    "first_name": p.first_name,
                    "color_index": p.color_index,
                    "tokens": [{"pos": t.pos, "state": t.state} for t in p.tokens],
                    "is_active": p.is_active
                } for p in self.players
            ],
            "current_turn_index": self.current_turn_index,
            "dice_value": self.dice_value,
            "last_roll_time": self.last_roll_time,
            "is_lobby": self.is_lobby,
            "winner": self.winner,
            "match_id": self.match_id,
            "tournament_id": self.tournament_id
        }

    @classmethod
    def from_dict(cls, data: dict):
        players = [
            Player(
                user_id=p["user_id"],
                first_name=p["first_name"],
                color_index=p["color_index"],
                tokens=[Token(pos=t["pos"], state=t["state"]) for t in p["tokens"]],
                is_active=p.get("is_active", True)
            ) for p in data["players"]
        ]
        return cls(
            chat_id=data["chat_id"],
            players=players,
            current_turn_index=data["current_turn_index"],
            dice_value=data["dice_value"],
            last_roll_time=data.get("last_roll_time", 0),
            is_lobby=data["is_lobby"],
            winner=data.get("winner"),
            match_id=data.get("match_id"),
            tournament_id=data.get("tournament_id")
        )

# Tournament Infrastructure (Structure Only)
@dataclass
class Match:
    match_id: str
    players: List[int] # user_ids
    winner: Optional[int] = None
    chat_id: Optional[int] = None

    def to_dict(self):
        return {
            "match_id": self.match_id,
            "players": self.players,
            "winner": self.winner,
            "chat_id": self.chat_id
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            match_id=data["match_id"],
            players=data["players"],
            winner=data.get("winner"),
            chat_id=data.get("chat_id")
        )

@dataclass
class Tournament:
    tournament_id: str
    players: List[int]
    rounds: List[List[Match]]
    status: str = "waiting" # "waiting", "active", "finished"
    winner: Optional[int] = None

    def to_dict(self):
        return {
            "tournament_id": self.tournament_id,
            "players": self.players,
            "rounds": [[m.to_dict() for m in r] for r in self.rounds],
            "status": self.status,
            "winner": self.winner
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            tournament_id=data["tournament_id"],
            players=data["players"],
            rounds=[[Match.from_dict(m) for m in r] for r in data["rounds"]],
            status=data["status"],
            winner=data.get("winner")
        )
