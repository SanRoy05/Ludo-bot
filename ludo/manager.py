import json
import uuid
import random
from typing import Dict, List, Optional
from .state import GameState, Player, Token, Tournament, Match
from .rules import get_valid_moves, move_token, is_game_over
import db

class LudoManager:
    def __init__(self):
        pass # No in-memory state

    def _get_key(self, chat_id: int, match_id: Optional[str] = None) -> str:
        # Note: In stateless DB version, we use chat_id or match_id directly in DB queries.
        # This helper is less critical but kept for logic consistency.
        return f"m_{match_id}" if match_id else f"c_{chat_id}"

    async def create_lobby(self, chat_id: int, creator_id: int, creator_name: str, match_id: Optional[str] = None, players: List[int] = None) -> Optional[str]:
        # Check if game exists
        existing = await self.get_game_state(chat_id, match_id)
        if existing:
            return "A game is already active here!"
        
        if players:
            # Pre-filled lobby for tournament matches
            p_objs = [Player(user_id=uid, first_name=f"Player {i+1}", color_index=i) for i, uid in enumerate(players)]
            state = GameState(chat_id=chat_id, players=p_objs, is_lobby=True, match_id=match_id)
        else:
            creator = Player(user_id=creator_id, first_name=creator_name, color_index=0)
            state = GameState(chat_id=chat_id, players=[creator], is_lobby=True)
            
        await db.save_game_state(chat_id, state.to_dict())
        return None

    async def join_lobby(self, chat_id: int, user_id: int, user_name: str, match_id: Optional[str] = None) -> str:
        state = await self.get_game_state(chat_id, match_id)
        if not state: return "No active lobby!"
        if not state.is_lobby: return "Game already started!"
        if any(p.user_id == user_id for p in state.players): return "You already joined!"
        if len(state.players) >= 4: return "Lobby is full!"
        
        color_idx = len(state.players)
        state.players.append(Player(user_id=user_id, first_name=user_name, color_index=color_idx))
        await db.save_game_state(chat_id, state.to_dict())
        return f"{user_name} joined the game!"

    async def leave_lobby(self, chat_id: int, user_id: int, match_id: Optional[str] = None) -> str:
        state = await self.get_game_state(chat_id, match_id)
        if not state or not state.is_lobby: return "No active lobby!"
        
        original_count = len(state.players)
        state.players = [p for p in state.players if p.user_id != user_id]
        
        if len(state.players) == 0:
            await db.delete_game_state(chat_id)
            return "Lobby closed (no players)."
        
        if len(state.players) < original_count:
            # Re-assign colors
            for i, p in enumerate(state.players):
                p.color_index = i
            await db.save_game_state(chat_id, state.to_dict())
            return "You left the lobby."
        return "You were not in the lobby."

    async def start_game(self, chat_id: int, user_id: int, match_id: Optional[str] = None) -> str:
        state = await self.get_game_state(chat_id, match_id)
        if not state or not state.is_lobby: return "No lobby found!"
        
        if len(state.players) < 2: return "Need at least 2 players to start!"
        
        state.is_lobby = False
        random.shuffle(state.players)
        for i, p in enumerate(state.players):
             p.color_index = i # Turn order colors
        
        state.current_turn_index = 0
        state.last_roll_time = 0
        await db.save_game_state(chat_id, state.to_dict())
        return "Game started! 🎲"

    async def roll_dice(self, chat_id: int, user_id: int, match_id: Optional[str] = None) -> tuple[Optional[int], str]:
        state = await self.get_game_state(chat_id, match_id)
        if not state or state.is_lobby: return None, "No active game!"
        
        current_player = state.players[state.current_turn_index]
        if current_player.user_id != user_id: return None, "It's not your turn!"
        if state.dice_value is not None: return None, "You already rolled! Move your token."
        
        val = random.randint(1, 6)
        state.dice_value = val
        
        valid_moves = get_valid_moves(current_player, val)
        if not valid_moves:
            state.dice_value = None
            msg = f"Rolled {val}. No valid moves. Skipping turn..."
            state.current_turn_index = (state.current_turn_index + 1) % len(state.players)
            await db.save_game_state(chat_id, state.to_dict())
            return val, msg
            
        await db.save_game_state(chat_id, state.to_dict())
        return val, f"Rolled {val}! Choose a token to move."

    async def move_token(self, chat_id: int, user_id: int, token_idx: int, match_id: Optional[str] = None) -> str:
        state = await self.get_game_state(chat_id, match_id)
        if not state or state.is_lobby or state.dice_value is None: return "Action not allowed."
        
        current_player_idx = state.current_turn_index
        current_player = state.players[current_player_idx]
        if current_player.user_id != user_id: return "It's not your turn!"
        
        dice = state.dice_value
        killed = move_token(state, current_player_idx, token_idx, dice)
        
        # Check win
        if is_game_over(current_player):
            state.winner = user_id
            for p in state.players:
                rank = 1 if p.user_id == user_id else 3
                await db.update_player_game_end(p.user_id, p.first_name, rank)
            
            winner_name = current_player.first_name
            await db.delete_game_state(chat_id)
            return f"🎉 {winner_name} won the game!"

        # Extra turn on 6 or kill
        if dice == 6 or killed:
            msg = f"Moved token. Extra turn for {current_player.first_name}!"
        else:
            state.current_turn_index = (state.current_turn_index + 1) % len(state.players)
            msg = f"Moved token. It's {state.players[state.current_turn_index].first_name}'s turn."
        
        state.dice_value = None
        await db.save_game_state(chat_id, state.to_dict())
        return msg

    async def get_game_state(self, chat_id: int, match_id: Optional[str] = None) -> Optional[GameState]:
        # For simple games, we use chat_id. For matches, we could use match_id but db.py uses chat_id as PK.
        # If match_id is used, we'd need a different table or mapping.
        # For now, we'll follow the existing convention where match games are also chat-scoped.
        data = await db.get_game_state(chat_id)
        if data:
            return GameState.from_dict(data)
        return None

    async def delete_game(self, chat_id: int, match_id: Optional[str] = None) -> bool:
        state = await self.get_game_state(chat_id, match_id)
        if state:
            await db.delete_game_state(chat_id)
            return True
        return False

class TournamentManager:
    def __init__(self):
        pass

    async def create_tournament(self, creator_id: int) -> str:
        t_id = str(uuid.uuid4())[:8]
        tournament = Tournament(
            tournament_id=t_id,
            players=[creator_id],
            rounds=[],
            status="waiting"
        )
        await db.save_tournament_state(t_id, tournament.to_dict())
        return t_id

    async def join_tournament(self, t_id: str, user_id: int) -> str:
        t = await self.get_tournament(t_id)
        if not t: return "Tournament not found."
        if t.status != "waiting": return "Tournament already started."
        if user_id in t.players: return "You already joined."
        if len(t.players) >= 16: return "Tournament is full (max 16)."
        
        t.players.append(user_id)
        await db.save_tournament_state(t_id, t.to_dict())
        return "Joined successfully!"

    async def start_tournament(self, t_id: str) -> Optional[str]:
        t = await self.get_tournament(t_id)
        if not t: return "Tournament not found."
        num_players = len(t.players)
        
        if num_players < 4: return "Need at least 4 players."
        
        t.status = "active"
        random.shuffle(t.players)
        
        matches = []
        pair_list = t.players[:]
        while len(pair_list) >= 2:
            p1 = pair_list.pop(0)
            p2 = pair_list.pop(0)
            match = Match(match_id=str(uuid.uuid4())[:6], players=[p1, p2])
            matches.append(match)
            
        t.rounds.append(matches)
        await db.save_tournament_state(t_id, t.to_dict())
        return None

    async def get_tournament(self, t_id: str) -> Optional[Tournament]:
        data = await db.get_tournament_state(t_id)
        return Tournament.from_dict(data) if data else None

    async def set_match_winner(self, t_id: str, match_id: str, winner_id: int):
        t = await self.get_tournament(t_id)
        if not t: return
        
        target_match = None
        for r in t.rounds:
            for m in r:
                if m.match_id == match_id:
                    target_match = m
                    break
        
        if target_match:
            target_match.winner = winner_id
            
        # Check if current round complete
        current_round = t.rounds[-1]
        round_winners = [m.winner for m in current_round if m.winner]
        
        if len(round_winners) == len(current_round):
            if len(round_winners) == 1:
                t.status = "finished"
                t.winner = round_winners[0]
            else:
                next_matches = []
                winners_pool = round_winners[:]
                while len(winners_pool) >= 2:
                    p1 = winners_pool.pop(0)
                    p2 = winners_pool.pop(0)
                    next_matches.append(Match(match_id=str(uuid.uuid4())[:6], players=[p1, p2]))
                t.rounds.append(next_matches)
        
        await db.save_tournament_state(t_id, t.to_dict())
