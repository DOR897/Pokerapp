export type Allowed = { check: boolean; call: boolean; raise: boolean; fold: boolean };

export type PlayerPub = { sid: string; name: string; chips: number; in_hand: boolean };

export type RoomUpdate = {
  players: PlayerPub[];
  community: string[];
  pot: number;
  state: 'waiting' | 'preflop' | 'flop' | 'turn' | 'river' | 'showdown';
  dealer: string | null;
  current_to: string | null;
  current_bet: number;
  turn_deadline?: number | null; // unix seconds
};

export type PlayerUpdate = {
  your_cards: string[];
  players: PlayerPub[];
  community: string[];
  pot: number;
  state: RoomUpdate['state'];
  dealer: string | null;
  current_to: string | null;
  current_bet: number;
  turn_deadline?: number | null;
  allowed_actions: Allowed;
};

export type GameSnapshot = {
  pub: RoomUpdate | null;
  priv: PlayerUpdate | null;
  mySid: string | null;
  roomCode: string;
  playerName: string;
};