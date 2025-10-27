import React, { useEffect, useMemo, useRef, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Alert } from 'react-native';
import { useLocalSearchParams } from './expo-router';
import type { Allowed, PlayerUpdate, RoomUpdate } from '../lib/types';
import { createSocket } from '../lib/socket';
import Card from '../components/Card';
import GameStatus from '../components/GameStatus';
import ActionButtons from '../components/ActionButtons';
import type { Socket } from 'socket.io-client';

export default function GameScreen() {
  const { name, room } = useLocalSearchParams<{ name: string; room?: string }>();

  const socketRef = useRef<Socket | null>(null);

  const [pub, setPub] = useState<RoomUpdate | null>(null);
  const [priv, setPriv] = useState<PlayerUpdate | null>(null);
  const [mySid, setMySid] = useState<string | null>(null);
  const [roomCode, setRoomCode] = useState<string>(room || '');
  const [inFlight, setInFlight] = useState(false);

  const allowed: Allowed =
    priv?.allowed_actions ?? { check: false, call: false, raise: false, fold: false };

  const isMyTurn = useMemo(
    () => !!(pub?.current_to && mySid && pub.current_to === mySid),
    [pub?.current_to, mySid]
  );

  const timer = useMemo(
    () => (pub?.turn_deadline ? Math.max(0, Math.ceil(pub.turn_deadline - Date.now() / 1000)) : undefined),
    [pub?.turn_deadline, pub?.current_to] // recompute on turn change
  );

  // ----- socket setup -----
  useEffect(() => {
    const s = createSocket();
    socketRef.current = s;

    const onConnect = () => setMySid(s.id);
    const onRoomCreated = (d: any) => {
      setRoomCode(d.room);
      s.emit('join_room', { room: d.room, name: name || 'Player' });
    };
    const onJoined = (_: any) => {};
    const onRoomUpdate = (state: RoomUpdate) => { setPub(state); setInFlight(false); };
    const onPlayerUpdate = (state: PlayerUpdate) => {
      setPriv(state);
      // keep pub in sync for shared fields
      setPub(p => ({
        players: state.players,
        community: state.community,
        pot: state.pot,
        state: state.state,
        dealer: state.dealer,
        current_to: state.current_to,
        current_bet: state.current_bet,
        turn_deadline: state.turn_deadline ?? null
      }));
      setInFlight(false);
    };
    const onError = (e: any) => { console.warn('socket error', e?.message || e); setInFlight(false); };

    s.on('connect', onConnect);
    s.on('room_created', onRoomCreated);
    s.on('joined', onJoined);
    s.on('room_update', onRoomUpdate);
    s.on('player_update', onPlayerUpdate);
    s.on('error', onError);
    s.on('connect_error', onError);

    // create or join
    if (!room || room.length === 0) {
      s.emit('create_room');
    } else {
      s.emit('join_room', { room, name: name || 'Player' });
    }

    return () => {
      s.off('connect', onConnect);
      s.off('room_created', onRoomCreated);
      s.off('joined', onJoined);
      s.off('room_update', onRoomUpdate);
      s.off('player_update', onPlayerUpdate);
      s.off('error', onError);
      s.off('connect_error', onError);
      s.disconnect();
      socketRef.current = null;
    };
  }, [name, room]);

  // actions
  const emit = (event: string, payload: any = {}) => {
    const s = socketRef.current;
    if (!s || !s.connected) {
      Alert.alert('Not connected to server');
      return;
    }
    if (!roomCode) {
      Alert.alert('No room code');
      return;
    }
    setInFlight(true);
    s.emit(event, { room: roomCode, ...payload });
  };

  const onAct = (action: 'check' | 'call' | 'raise' | 'fold', amount?: number) => {
    if (!isMyTurn) { Alert.alert('Not your turn'); return; }
    if (action === 'raise') {
      const amt = Number(amount) || 0;
      if (amt <= 0) { Alert.alert('Enter raise amount'); return; }
    }
    emit('player_action', { action, amount });
  };

  const startHand = () => emit('start_hand');

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 16 }}>
      <Text style={styles.small}>Room: {roomCode || '—'}</Text>

      <GameStatus
        phase={pub?.state || 'waiting'}
        pot={pub?.pot || 0}
        currentBet={pub?.current_bet || 0}
        players={(pub?.players || []).map(p => ({
          name: p.name || 'Anonymous',
          chips: p.chips || 0,
          isDealer: pub?.dealer === p.sid,
          isTurn: pub?.current_to === p.sid
        }))}
        /* ✅ JSX braces fix */
        timer={timer ?? undefined}
      />

      <View style={styles.cardsRow}>
        {(pub?.community || []).map((c, i) => <Card key={i} card={c} />)}
      </View>

      <Text style={styles.small}>Your chips: {priv?.players.find(x => x.sid === mySid)?.chips ?? 0}</Text>
      <View style={styles.cardsRow}>
        {(priv?.your_cards || []).map((c, i) => <Card key={i} card={c} />)}
      </View>

      <View style={{ height: 8 }} />
      <ActionButtons
        currentBet={pub?.current_bet || 0}
        onCheck={() => onAct('check')}
        onCall={() => onAct('call')}
        onRaise={(amt: number) => onAct('raise', amt)}
        onFold={() => onAct('fold')}
        canCheck={allowed.check && isMyTurn}
        canCall={allowed.call && isMyTurn}
        canRaise={allowed.raise && isMyTurn}
        canFold={allowed.fold && isMyTurn}
        disabledAll={!isMyTurn || !(allowed.check || allowed.call || allowed.raise || allowed.fold) || inFlight}
        onStartHand={startHand}
        showStart={pub?.state === 'waiting'}
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor:'#0d1b2a' },
  small:{ color:'#cbd5e1', marginBottom:8 },
  cardsRow:{ flexDirection:'row', flexWrap:'wrap', gap:8, marginVertical:8 }
});