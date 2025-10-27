import io, { Socket } from 'socket.io-client';

export function createSocket(): Socket {
  // Expo reads public envs from EXPO_PUBLIC_*
  const API_URL =
    process.env.EXPO_PUBLIC_API_URL ||
    'http://10.0.2.2:5000'; // android emulator fallback

  const s = io(API_URL, {
    transports: ['websocket'],
    reconnection: true,
    reconnectionAttempts: 10,
    reconnectionDelay: 800,
    autoConnect: true,
    path: '/socket.io'
  });
  return s;
}