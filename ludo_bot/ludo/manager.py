import json
import uuid
import random
from typing import Dict, List, Optional
from .state import GameState, Player, Token, Tournament, Match
from .rules import get_valid_moves, move_token, is_game_over

class LudoManager:
    def __init__(self):
        self.games: Dict[str, GameState] = {} # Use string key to support match_id

    def _get_key(self, chat_id: int, match_id: Optional[str] = None) -> str:
        if match_id: return f"m_{match_id}"
        return f"c_{chat_id}"

    def create_lobby(self, chat_id: int, creator_id: int, creator_name: str, match_id: Optional[str] = None, players: List[int] = None) -> Optional[str]:
        key = self._get_key(chat_id, match_id)
        if key in self.games:
            return "A game is already active here!"
        
        if players:
            # Pre-filled lobby for tournament matches
            p_objs = [Player(user_id=uid, first_name=f"Player {i+1}", color_index=i) for i, uid in enumerate(players)]
            state = GameState(chat_id=chat_id, players=p_objs, is_lobby=True, match_id=match_id)
        else:
            creator = Player(user_id=creator_id, first_name=creator_name, color_index=0)
            state = GameState(chat_id=chat_id, players=[creator], is_lobby=True)
            
        self.games[key] = state
        return None

    def join_lobby(self, chat_id: int, user_id: int, user_name: str, match_id: Optional[str] = None) -> str:
        key = self._get_key(chat_id, match_id)
        state = self.games.get(key)
        if not state: return "No active lobby!"
        if not state.is_lobby: return "Game already started!"
        if any(p.user_id == user_id for p in state.players): return "You already joined!"
        if len(state.players) >= 4: return "Lobby is full!"
        
        color_idx = len(state.players)
        state.players.append(Player(user_id=user_id, first_name=user_name, color_index=color_idx))
        return f"{user_name} joined the game!"

    def leave_lobby(self, chat_id: int, user_id: int, match_id: Optional[str] = None) -> str:
        key = self._get_key(chat_id, match_id)
        state = self.games.get(key)
        if not state or not state.is_lobby: return "No active lobby!"
        
        original_count = len(state.players)
        state.players = [p for p in state.players if p.user_id != user_id]
        
        if len(state.players) == 0:
            del self.games[key]
            return "Lobby closed (no players)."
        
        if len(state.players) < original_count:
            # Re-assign colors
            for i, p in enumerate(state.players):
                p.color_index = i
            return "You left the lobby."
        return "You were not in the lobby."

    def start_game(self, chat_id: int, user_id: int, match_id: Optional[str] = None) -> str:
        key = self._get_key(chat_id, match_id)
        state = self.games.get(key)
        if not state or not state.is_lobby: return "No lobby found!"
        
        if len(state.players) < 2: return "Need at least 2 players to start!"
        
        state.is_lobby = False
        random.shuffle(state.players)
        for i, p in enumerate(state.players):
             p.color_index = i # Turn order colors
        
        state.current_turn_index = 0
        state.last_roll_time = 0
        return "Game started! 🎲"

    def roll_dice(self, chat_id: int, user_id: int, match_id: Optional[str] = None) -> tuple[Optional[int], str]:
        key = self._get_key(chat_id, match_id)
        state = self.games.get(key)
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
            return val, msg
            
        return val, f"Rolled {val}! Choose a token to move."

    async def move_token(self, chat_id: int, user_id: int, token_idx: int, match_id: Optional[str] = None) -> str:
        key = self._get_key(chat_id, match_id)
        state = self.games.get(key)
        if not state or state.is_lobby or state.dice_value is None: return "Action not allowed."
        
        current_player_idx = state.current_turn_index
        current_player = state.players[current_player_idx]
        if current_player.user_id != user_id: return "It's not your turn!"
        
        dice = state.dice_value
        killed = move_token(state, current_player_idx, token_idx, dice)
        
        # Check win
        if is_game_over(current_player):
            state.winner = user_id
            
            # Award rewards
            # 1st place: winner
            # For simplicity, 2nd place and others are not tracked mid-game.
            # We'll give winner 25 and others 2 for now as it's a "winner takes all" end.
            for p in state.players:
                rank = 1 if p.user_id == user_id else 3 # 1st or "others"
                await db.update_player_game_end(p.user_id, p.first_name, rank)
            
            winner_name = current_player.first_name
            del self.games[key]
            await db.delete_game_state(chat_id) # Note: DB persistence is still chat-scoped for simplicity
            return f"🎉 {winner_name} won the game!"

        # Persistence
        await db.save_game_state(chat_id, state.to_json())

        # Extra turn on 6 or kill
        if dice == 6 or killed:
            msg = f"Moved token. Extra turn for {current_player.first_name}!"
        else:
            state.current_turn_index = (state.current_turn_index + 1) % len(state.players)
            msg = f"Moved token. It's {state.players[state.current_turn_index].first_name}'s turn."
        
        state.dice_value = None
        return msg

    async def get_game_state(self, chat_id: int, match_id: Optional[str] = None) -> Optional[GameState]:
        key = self._get_key(chat_id, match_id)
        if key in self.games:
            return self.games[key]
        
        # Try loading from DB
        # Note: DB only stores by chat_id for now, so match_id support is limited in DB persistence
        # We'll stick to chat_id for normal games.
        if match_id is None:
            db_json = await db.get_game_state(chat_id)
            if db_json:
                state = GameState.from_json(chat_id, db_json)
                self.games[key] = state
                return state
        return None

    def delete_game(self, chat_id: int, match_id: Optional[str] = None) -> bool:
        key = self._get_key(chat_id, match_id)
        if key in self.games:
            del self.games[key]
            return True
        return False

class TournamentManager:
    def __init__(self):
        self.tournaments: Dict[str, Tournament] = {}

    def create_tournament(self, creator_id: int) -> str:
        t_id = str(uuid.uuid4())[:8]
        tournament = Tournament(
            tournament_id=t_id,
            players=[creator_id],
            rounds=[],
            status="waiting"
        )
        self.tournaments[t_id] = tournament
        return t_id

    def join_tournament(self, t_id: str, user_id: int) -> str:
        t = self.tournaments.get(t_id)
        if not t: return "Tournament not found."
        if t.status != "waiting": return "Tournament already started."
        if user_id in t.players: return "You already joined."
        if len(t.players) >= 16: return "Tournament is full (max 16)."
        
        t.players.append(user_id)
        return "Joined successfully!"

    def start_tournament(self, t_id: str) -> Optional[str]:
        t = self.tournaments.get(t_id)
        if not t: return "Tournament not found."
        num_players = len(t.players)
        
        if num_players < 4: return "Need at least 4 players."
        
        t.status = "active"
        random.shuffle(t.players)
        
        # Generate Round 1 (Standard 1v1 eliminination using 2-player Ludo)
        matches = []
        pair_list = t.players[:]
        while len(pair_list) >= 2:
            p1 = pair_list.pop(0)
            p2 = pair_list.pop(0)
            match = Match(match_id=str(uuid.uuid4())[:6], players=[p1, p2])
            matches.append(match)
            
        t.rounds.append(matches)
        return None

    def get_match_by_id(self, match_id: str) -> Optional[Match]:
        for t in self.tournaments.values():
            for r in t.rounds:
                for m in r:
                    if m.match_id == match_id:
                        return m
        return None

    def set_match_winner(self, t_id: str, match_id: str, winner_id: int):
        t = self.tournaments.get(t_id)
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
