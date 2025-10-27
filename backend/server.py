# server.py
from flask import Flask, request
from flask_socketio import SocketIO, join_room, leave_room, emit
import random, uuid, itertools, time

# ------------------------------------------------------------
# App / Socket.IO (no eventlet, no gevent)
# ------------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ------------------------------------------------------------
# Game state
# ------------------------------------------------------------
rooms = {}

STARTING_CHIPS = 50
SMALL_BLIND    = 1
BIG_BLIND      = 2
TURN_TIMEOUT   = 20  # seconds

RANKS = '23456789TJQKA'
SUITS = ['♠','♥','♦','♣']
RANK_TO_VAL = {r:i for i,r in enumerate(RANKS, start=2)}

def new_deck():
    deck = [r+s for r in RANKS for s in SUITS]
    random.shuffle(deck)
    return deck

# --------- quick hand evaluator (5-card) ----------
def rankv(c): return RANK_TO_VAL[c[0]]
def suit(c):  return c[1]

def is_straight(vals):
    vals = sorted(set(vals))
    # wheel
    if set([14,2,3,4,5]).issubset(set(vals)): return True, 5
    for i in range(len(vals)-4):
        if vals[i+4]-vals[i] == 4:
            return True, vals[i+4]
    return False, None

def eval5(cards5):
    vals = sorted([rankv(c) for c in cards5], reverse=True)
    suits = [suit(c) for c in cards5]
    flush = any(suits.count(s)==5 for s in SUITS)
    st, top = is_straight(sorted(vals))
    cnt = {}
    for v in vals: cnt[v] = cnt.get(v,0)+1
    freq = sorted(((c,v) for v,c in cnt.items()), reverse=True)  # by count then val
    if st and flush:               return (8, (top,))
    if freq[0][0]==4:              # four + kicker
        four = freq[0][1]; kick = max(v for v in vals if v!=four)
        return (7, (four, kick))
    if freq[0][0]==3 and len(freq)>1 and freq[1][0]==2:
        return (6, (freq[0][1], freq[1][1]))   # full house
    if flush:                       return (5, tuple(vals))
    if st:                          return (4, (top,))
    if freq[0][0]==3:
        tri=freq[0][1]; kicks=tuple(v for v in vals if v!=tri)
        return (3, (tri,)+kicks)
    if len(freq)>1 and freq[0][0]==2 and freq[1][0]==2:
        p1,p2 = sorted([freq[0][1],freq[1][1]], reverse=True)
        kick = max(v for v in vals if v not in (p1,p2))
        return (2,(p1,p2,kick))
    if freq[0][0]==2:
        p=freq[0][1]; kicks=tuple(v for v in vals if v!=p)
        return (1,(p,)+kicks)
    return (0, tuple(vals))

def best7(cards7):
    best=None; best5=None
    for comb in itertools.combinations(cards7,5):
        score = eval5(list(comb))
        if best is None or score>best:
            best=score; best5=list(comb)
    return best, best5

def hand_name(score):
    names = ["High Card","Pair","Two Pair","Three of a Kind","Straight",
             "Flush","Full House","Four of a Kind","Straight Flush"]
    return names[score[0]]

# ------------------------------------------------------------
# Room helpers
# ------------------------------------------------------------
def make_room():
    code = str(uuid.uuid4())[:8]
    rooms[code] = {
        'players': {},        # sid -> {name,chips,cards,in_hand,contribution,has_acted}
        'deck': [],
        'community': [],
        'pot': 0,
        'turn_order': [],     # list of sids (seating)
        'dealer_idx': 0,
        'current_to_idx': 0,
        'current_bet': 0,
        'state': 'waiting',
        'turn_deadline': None,
        'turn_timer_cancel': False
    }
    return code

def active_players_in_hand(r):
    return [sid for sid,p in r['players'].items() if p.get('in_hand', True)]

def compute_allowed_actions(r, sid):
    res = {'check': False, 'call': False, 'raise': False, 'fold': False}
    if r['state'] in ('waiting','showdown'): return res
    if not r['turn_order']: return res
    cur = r.get('current_to_idx',0)
    if cur<0 or cur>=len(r['turn_order']) or r['turn_order'][cur]!=sid: return res
    p = r['players'].get(sid);
    if not p or not p.get('in_hand',True): return res

    chips = p.get('chips',0)
    need  = max(0, r['current_bet'] - p.get('contribution',0))
    res['fold'] = True
    if need==0:
        res['check'] = True
        res['raise'] = chips>0
    else:
        res['call']  = chips>0
        res['raise'] = chips>need
    return res

def private_payload_for(r, sid):
    p = r['players'].get(sid, {})
    return {
        'players': [{'sid':s,'name':pp['name'],'chips':pp['chips'],'in_hand':pp.get('in_hand',True)}
                    for s,pp in r['players'].items()],
        'community': r['community'],
        'pot': r['pot'],
        'state': r['state'],
        'dealer': r['turn_order'][r['dealer_idx']] if r['turn_order'] else None,
        'current_to': r['turn_order'][r['current_to_idx']] if r['turn_order'] else None,
        'current_bet': r['current_bet'],
        'turn_deadline': r.get('turn_deadline'),
        'your_cards': p.get('cards', []),
        'allowed_actions': compute_allowed_actions(r, sid)
    }

def broadcast_room(room):
    if room not in rooms: return
    r = rooms[room]
    pub = {
        'players': [{'sid':s,'name':p['name'],'chips':p['chips'],'in_hand':p.get('in_hand',True)}
                    for s,p in r['players'].items()],
        'community': r['community'],
        'pot': r['pot'],
        'state': r['state'],
        'dealer': r['turn_order'][r['dealer_idx']] if r['turn_order'] else None,
        'current_to': r['turn_order'][r['current_to_idx']] if r['turn_order'] else None,
        'current_bet': r['current_bet'],
        'turn_deadline': r.get('turn_deadline')
    }
    # private
    for sid in list(r['players'].keys()):
        socketio.emit('player_update', private_payload_for(r, sid), room=sid)
    socketio.emit('room_update', pub, room=room)

# ------------------------------------------------------------
# Turn timer (server authoritative)
# ------------------------------------------------------------
def cancel_turn_timer(room):
    r = rooms.get(room)
    if not r: return
    r['turn_timer_cancel'] = True
    r['turn_deadline'] = None

def start_turn_timer_for_current(room):
    r = rooms.get(room);                        
    if not r: return
    r['turn_timer_cancel'] = False
    deadline = time.time() + TURN_TIMEOUT
    r['turn_deadline'] = deadline
    if not r['turn_order']: broadcast_room(room); return
    idx = r.get('current_to_idx',0)
    if idx<0 or idx>=len(r['turn_order']): broadcast_room(room); return
    target_sid = r['turn_order'][idx]
    broadcast_room(room)
    socketio.start_background_task(turn_timeout_worker, room, target_sid, deadline)

def turn_timeout_worker(room, target_sid, deadline):
    r = rooms.get(room); 
    if not r: return
    waited = 0.0
    while waited < TURN_TIMEOUT:
        if r.get('turn_timer_cancel'): return
        if r.get('turn_deadline') != deadline: return
        socketio.sleep(0.5); waited += 0.5
    # still the same player's turn?
    if r.get('turn_timer_cancel'): return
    if not r['turn_order']: return
    if r['turn_order'][r['current_to_idx']] != target_sid: return

    p = r['players'].get(target_sid)
    if not p: return
    p['in_hand'] = False
    p['has_acted'] = True
    socketio.emit('message', {'msg': f"{p['name']} auto-folded (timeout)"}, room=room)

    active = active_players_in_hand(r)
    if len(active) == 1:
        distribute_pot_and_emit(room, [active[0]])
        return

    # advance seat
    nb = len(r['turn_order'])
    for i in range(1, nb+1):
        idx = (r['current_to_idx'] + i) % nb
        s = r['turn_order'][idx]
        if r['players'][s].get('in_hand', True):
            r['current_to_idx'] = idx
            break
    start_turn_timer_for_current(room)
    broadcast_room(room)

# ------------------------------------------------------------
# Socket events
# ------------------------------------------------------------
@app.route('/')
def health():
    return 'OK', 200

@socketio.on('create_room')
def on_create(_=None):
    room = make_room()
    emit('room_created', {'room': room}, room=request.sid)

@socketio.on('join_room')
def on_join(data):
    room = data.get('room')
    name = data.get('name') or 'Player'
    sid = request.sid
    if room not in rooms:
        emit('error', {'message': 'Room not found'}, room=sid); return
    r = rooms[room]
    r['players'][sid] = {'name':name,'chips':STARTING_CHIPS,'cards':[],
                         'in_hand':True,'contribution':0,'has_acted':False}
    if sid not in r['turn_order']: r['turn_order'].append(sid)
    join_room(room)
    emit('joined', {'room':room, 'name':name, 'chips':STARTING_CHIPS}, room=sid)
    broadcast_room(room)

@socketio.on('leave_room')
def on_leave(data):
    room = data.get('room'); sid = request.sid
    if room in rooms:
        r = rooms[room]
        r['players'].pop(sid, None)
        if sid in r['turn_order']: r['turn_order'].remove(sid)
        leave_room(room)
        broadcast_room(room)

@socketio.on('start_hand')
def on_start(data):
    room = data.get('room'); 
    if room not in rooms: return
    r = rooms[room]
    if len(r['players']) < 2:
        emit('error', {'message':'Need at least 2 players'}, room=request.sid); return

    # rotate dealer (keep existing order)
    if not r['turn_order']:
        r['turn_order'] = list(r['players'].keys())
    r['dealer_idx'] = (r['dealer_idx'] + 1) % len(r['turn_order'])

    # reset hand
    r['deck'] = new_deck()
    r['community'] = []
    r['pot'] = 0
    r['current_bet'] = 0
    r['state'] = 'preflop'
    for sid,p in r['players'].items():
        p['cards'] = [r['deck'].pop(), r['deck'].pop()]
        p['in_hand'] = True
        p['contribution'] = 0
        p['has_acted'] = False
        p['chips_before_hand'] = p['chips']

    # blinds
    nb = len(r['turn_order'])
    sb_idx = (r['dealer_idx'] + 1) % nb
    bb_idx = (r['dealer_idx'] + 2) % nb
    sb_sid = r['turn_order'][sb_idx]
    bb_sid = r['turn_order'][bb_idx]
    sb_pay = min(SMALL_BLIND, r['players'][sb_sid]['chips'])
    bb_pay = min(BIG_BLIND,  r['players'][bb_sid]['chips'])
    r['players'][sb_sid]['chips'] -= sb_pay
    r['players'][bb_sid]['chips'] -= bb_pay
    r['players'][sb_sid]['contribution'] = sb_pay
    r['players'][bb_sid]['contribution'] = bb_pay
    r['pot'] += sb_pay + bb_pay
    r['current_bet'] = bb_pay
    r['players'][sb_sid]['has_acted'] = True
    r['players'][bb_sid]['has_acted'] = True

    # first to act is after big blind
    r['current_to_idx'] = (bb_idx + 1) % nb
    start_turn_timer_for_current(room)  # also broadcasts
    emit('hand_started', {}, room=room)

def betting_round_complete(r):
    active = active_players_in_hand(r)
    if len(active) <= 1: return True
    for sid in active:
        p = r['players'][sid]
        if not p.get('has_acted', False): return False
        if p.get('contribution',0) < r['current_bet'] and p.get('chips',0)>0:
            return False
    return True

def distribute_pot_and_emit(room, winners):
    r = rooms[room]
    if not winners: return
    share = r['pot'] // len(winners)
    for sid in winners:
        r['players'][sid]['chips'] += share
    r['pot'] = 0
    results = []
    for sid,p in r['players'].items():
        delta = p['chips'] - p.get('chips_before_hand', p['chips'])
        results.append({'sid':sid,'name':p['name'],'final_chips':p['chips'],'delta':delta})
    cancel_turn_timer(room)
    socketio.emit('showdown', {'results':results, 'community':r['community']}, room=room)
    r['state'] = 'waiting'
    for p in r['players'].values():
        p.pop('chips_before_hand', None)
    broadcast_room(room)

def move_to_next_street_or_showdown(room):
    r = rooms[room]
    if r['state']=='preflop':
        r['community'] += [r['deck'].pop(), r['deck'].pop(), r['deck'].pop()]
        r['state'] = 'flop'
    elif r['state']=='flop':
        r['community'] += [r['deck'].pop()]
        r['state'] = 'turn'
    elif r['state']=='turn':
        r['community'] += [r['deck'].pop()]
        r['state'] = 'river'
    elif r['state']=='river':
        # showdown
        contenders = []
        for sid,p in r['players'].items():
            if p.get('in_hand', False):
                score, combo = best7(p['cards'] + r['community'])
                contenders.append((sid,score,combo))
        if not contenders: return
        bestscore = max(s for _,s,_ in contenders)
        winners = [sid for sid,s,_ in contenders if s==bestscore]
        socketio.emit('showdown',
                      {'winners':[{'sid':sid,'name':r['players'][sid]['name'],
                                   'hand_name':hand_name(bestscore),
                                   'combo':' '.join(combo)} for sid, s, combo in contenders if s==bestscore],
                       'community':r['community']}, room=room)
        distribute_pot_and_emit(room, winners)
        return

    # reset contributions/acted for new street and set first to act after dealer
    r['current_bet'] = 0
    for _sid,_p in r['players'].items():
        if _p.get('in_hand',True) and _p.get('chips',0)>0:
            _p['contribution'] = 0
            _p['has_acted'] = False
        else:
            _p['has_acted'] = True

    nb = len(r['turn_order'])
    start_idx = (r['dealer_idx'] + 1) % nb
    for i in range(nb):
        idx = (start_idx + i) % nb
        sid_candidate = r['turn_order'][idx]
        if r['players'][sid_candidate].get('in_hand',True):
            r['current_to_idx'] = idx
            break
    start_turn_timer_for_current(room)  # also broadcasts

@socketio.on('player_action')
def on_action(data):
    room = data.get('room'); sid = request.sid
    if room not in rooms: return
    r = rooms[room]
    if not r['turn_order']: return
    if r['turn_order'][r['current_to_idx']] != sid:
        emit('error', {'message':'Not your turn'}, room=sid); return

    cancel_turn_timer(room)  # player is acting
    action = data.get('action')
    amount = int(data.get('amount', 0))
    p = r['players'][sid]

    if action == 'fold':
        p['in_hand'] = False
        p['has_acted'] = True
        socketio.emit('message', {'msg': f"{p['name']} folded"}, room=room)

    elif action == 'check':
        need = r['current_bet'] - p.get('contribution',0)
        if need == 0:
            p['has_acted'] = True
            socketio.emit('message', {'msg': f"{p['name']} checked"}, room=room)
        else:
            emit('error', {'message':'Cannot check, must call/raise'}, room=sid)
            start_turn_timer_for_current(room); return

    elif action == 'call':
        need = r['current_bet'] - p.get('contribution',0)
        pay  = min(need, p['chips'])
        p['chips'] -= pay
        p['contribution'] = p.get('contribution',0) + pay
        p['has_acted'] = True
        r['pot'] += pay
        socketio.emit('message', {'msg': f"{p['name']} called {pay}"}, room=room)

    elif action == 'raise':
        need = r['current_bet'] - p.get('contribution',0)
        if amount <= 0:
            emit('error', {'message':'Raise amount must be > 0'}, room=sid)
            start_turn_timer_for_current(room); return
        total = need + amount
        pay = min(total, p['chips'])
        p['chips'] -= pay
        p['contribution'] = p.get('contribution',0) + pay
        r['pot'] += pay
        if p['contribution'] > r['current_bet']:
            r['current_bet'] = p['contribution']
            # others must act again
            for osid, op in r['players'].items():
                if osid != sid and op.get('in_hand',True) and op.get('chips',0)>0:
                    op['has_acted'] = False
        p['has_acted'] = True
        socketio.emit('message', {'msg': f"{p['name']} raised, bet is {r['current_bet']}"}, room=room)

    else:
        emit('error', {'message':'Unknown action'}, room=sid)
        start_turn_timer_for_current(room); return

    # early win by folds
    active = active_players_in_hand(r)
    if len(active) == 1:
        distribute_pot_and_emit(room, [active[0]])
        return

    # end of round?
    if betting_round_complete(r):
        move_to_next_street_or_showdown(room)
        return

    # otherwise go to next active player (same street)
    nb = len(r['turn_order'])
    for i in range(1, nb+1):
        idx = (r['current_to_idx'] + i) % nb
        s2 = r['turn_order'][idx]
        if r['players'][s2].get('in_hand', True):
            r['current_to_idx'] = idx
            break

    start_turn_timer_for_current(room)  # will also broadcast

if __name__ == '__main__':
    print('>>> POKER SERVER (threading, turns, timer) <<<')
    socketio.run(app, host='0.0.0.0', port=5000)
