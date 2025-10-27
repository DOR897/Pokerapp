import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import React from 'react';
import { SafeAreaView } from 'react-native';

export default function RootLayout() {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#1b263b' }}>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: '#1b263b' },
          headerTintColor: 'white',
          contentStyle: { backgroundColor: '#0d1b2a' }
        }}
      />
    </SafeAreaView>
  );
}
