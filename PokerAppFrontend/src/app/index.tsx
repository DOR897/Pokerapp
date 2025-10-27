import React, { useRef, useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import { useRouter } from 'expo-router';

export default function Home() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [room, setRoom] = useState('');

  const goGame = (autoCreate: boolean) => {
    if (!name.trim()) {
      Alert.alert('Name is required');
      return;
    }
    router.push({
      pathname: '/game',
      params: {
        name: name.trim(),
        room: autoCreate ? '' : room.trim()
      }
    });
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Poker — Expo Router</Text>
      <TextInput
        style={styles.input}
        placeholder="Your name"
        value={name}
        onChangeText={setName}
      />
      <TextInput
        style={styles.input}
        placeholder="Room code (leave empty to create)"
        value={room}
        onChangeText={setRoom}
      />
      <View style={styles.row}>
        <TouchableOpacity style={styles.btn} onPress={() => goGame(true)}>
          <Text style={styles.btnText}>Create Room</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.btn} onPress={() => goGame(false)}>
          <Text style={styles.btnText}>Join Room</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container:{ flex:1, padding:20, justifyContent:'center', gap:16 },
  title:{ color:'#fff', fontSize:24, textAlign:'center', marginBottom:8 },
  input:{ backgroundColor:'#fff', borderRadius:8, paddingHorizontal:12, height:48 },
  row:{ flexDirection:'row', gap:12, justifyContent:'center' },
  btn:{ backgroundColor:'#2a9d8f', paddingHorizontal:16, paddingVertical:12, borderRadius:10 },
  btnText:{ color:'#fff', fontWeight:'700' }
});