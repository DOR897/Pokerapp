import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

type P = {
  phase: string; pot: number; currentBet: number;
  players: { name: string; chips: number; isDealer: boolean; isTurn: boolean }[];
  timer?: number;
};

export default function GameStatus(p: P) {
  return (
    <View style={s.box}>
      <Text style={s.title}>Phase: {p.phase}   •   Pot: {p.pot}   •   Bet: {p.currentBet}</Text>
      {typeof p.timer === 'number' && <Text style={s.timer}>⏱ {p.timer}s</Text>}
      <View style={{ gap:6, marginTop:8 }}>
        {p.players.map((pl, i) => (
          <Text key={i} style={s.line}>
            {pl.isDealer ? '● ' : '  '}
            {pl.isTurn ? '➡ ' : '  '}
            {pl.name} — chips {pl.chips}
          </Text>
        ))}
      </View>
    </View>
  );
}
const s = StyleSheet.create({
  box:{ backgroundColor:'#14213d', padding:12, borderRadius:10 },
  title:{ color:'#fff', fontWeight:'700' },
  timer:{ color:'#f39c12', marginTop:4 },
  line:{ color:'#e5e7eb' }
});