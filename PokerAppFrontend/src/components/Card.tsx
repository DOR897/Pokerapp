import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function Card({ card }: { card: string }) {
  return (
    <View style={s.card}><Text style={s.t}>{card}</Text></View>
  );
}
const s = StyleSheet.create({
  card:{ backgroundColor:'#fff', paddingHorizontal:10, paddingVertical:8, borderRadius:8, minWidth:40, alignItems:'center' },
  t:{ color:'#111', fontWeight:'700' }
});