import random, itertools

RANKS = "23456789TJQKA"
SUITS = ["♠","♥","♦","♣"]
R2V = {r:i for i,r in enumerate(RANKS, start=2)}

def new_deck():
    d = [r+s for r in RANKS for s in SUITS]
    random.shuffle(d)
    return d

def eval5(cards):
    vals = sorted([R2V[c[0]] for c in cards], reverse=True)
    suits = [c[1] for c in cards]
    sc={}
    for s in suits: sc[s]=sc.get(s,0)+1
    flush = max(sc.values())==5 if sc else False
    u = sorted(set(vals), reverse=True)
    straight=None
    for i in range(len(u)-4):
        w=u[i:i+5]
        if w[0]-w[4]==4 and len(w)==5: straight=w[0]; break
    if not straight and {14,5,4,3,2}.issubset(u): straight=5
    cnt={}
    for v in vals: cnt[v]=cnt.get(v,0)+1
    freq = sorted(((c,v) for v,c in cnt.items()), key=lambda x:(x[0],x[1]), reverse=True)
    if straight and flush: return (8,(straight,))
    if freq[0][0]==4:
        four=freq[0][1]; kick=max(v for v in vals if v!=four); return (7,(four,kick))
    if freq[0][0]==3 and len(freq)>1 and freq[1][0]==2: return (6,(freq[0][1],freq[1][1]))
    if flush: return (5,tuple(vals))
    if straight: return (4,(straight,))
    if freq[0][0]==3:
        t=freq[0][1]; kicks=tuple([v for v in vals if v!=t]); return (3,(t,)+kicks)
    if len(freq)>1 and freq[0][0]==2 and freq[1][0]==2:
        pairs=sorted([freq[0][1],freq[1][1]], reverse=True)
        kick=max(v for v in vals if v not in pairs); return (2,(pairs[0],pairs[1],kick))
    if freq[0][0]==2:
        p=freq[0][1]; kicks=tuple([v for v in vals if v!=p]); return (1,(p,)+kicks)
    return (0,tuple(vals))

def best7(seven):
    best=None; combo=None
    for comb in itertools.combinations(seven,5):
        s=eval5(comb)
        if best is None or s>best:
            best=s; combo=comb
    return best, combo

def hand_name(s0:int):
    return {8:'Straight Flush',7:'Four of a Kind',6:'Full House',5:'Flush',
            4:'Straight',3:'Three of a Kind',2:'Two Pair',1:'One Pair',0:'High Card'}[s0]

def allowed_actions(state, sid):
    a = {'check':False,'call':False,'raise':False,'fold':False}
    if not state['turn_order']: return a
    if state['turn_order'][state['current_to_idx']] != sid: return a
    p = state['players'][sid]
    if not p.get('in_hand', True): return a
    contrib = p.get('contribution',0)
    chips = p.get('chips',0)
    curr = state['current_bet']
    a['fold']  = True
    a['check'] = (contrib == curr)
    a['call']  = (contrib < curr and chips > 0)
    a['raise'] = (chips > 0)
    return a
