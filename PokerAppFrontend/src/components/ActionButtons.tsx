import React, { useState } from 'react';
import { View, Text, TouchableOpacity, TextInput, StyleSheet } from 'react-native';

type Props = {
  currentBet: number;
  onCheck: () => void;
  onCall: () => void;
  onRaise: (amt: number) => void;
  onFold: () => void;
  canCheck: boolean; canCall: boolean; canRaise: boolean; canFold: boolean;
  disabledAll?: boolean;
  onStartHand: () => void;
  showStart?: boolean;
};

export default function ActionButtons(p: Props) {
  const [amt, setAmt] = useState('5');
  return (
    <View style={styles.row}>
      {p.showStart ? (
        <TouchableOpacity style={styles.btn} onPress={p.onStartHand}>
          <Text style={styles.txt}>Start Hand</Text>
        </TouchableOpacity>
      ) : (
        <>
          <TextInput
            style={styles.input}
            keyboardType="numeric"
            value={amt}
            onChangeText={setAmt}
            placeholder="Raise"
          />
          <TouchableOpacity style={[styles.btn, !p.canRaise||p.disabledAll && styles.disabled]} disabled={!p.canRaise||p.disabledAll} onPress={()=>p.onRaise(Number(amt)||0)}>
            <Text style={styles.txt}>Raise</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.btn, !p.canCall||p.disabledAll && styles.disabled]} disabled={!p.canCall||p.disabledAll} onPress={p.onCall}>
            <Text style={styles.txt}>Call</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.btn, !p.canCheck||p.disabledAll && styles.disabled]} disabled={!p.canCheck||p.disabledAll} onPress={p.onCheck}>
            <Text style={styles.txt}>Check</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.btn, !p.canFold||p.disabledAll && styles.disabled]} disabled={!p.canFold||p.disabledAll} onPress={p.onFold}>
            <Text style={styles.txt}>Fold</Text>
          </TouchableOpacity>
        </>
      )}
    </View>
  );
}
const styles = StyleSheet.create({
  row:{ flexDirection:'row', flexWrap:'wrap', gap:8, alignItems:'center' },
  input:{ backgroundColor:'#fff', borderRadius:8, paddingHorizontal:10, height:44, width:90 },
  btn:{ backgroundColor:'#f39c12', paddingHorizontal:14, paddingVertical:10, borderRadius:10 },
  txt:{ color:'#041022', fontWeight:'700' },
  disabled:{ opacity:0.5 }
});