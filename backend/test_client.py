import socketio
import time

# Create SocketIO client
sio = socketio.Client()

# Event handlers
@sio.event
def connect():
    print('Connected to server')

@sio.event
def disconnect():
    print('Disconnected from server')

@sio.on('room_update')
def on_room_update(data):
    print('\nRoom Update:')
    print(f"Players: {data['players']}")
    print(f"Community cards: {data['community']}")
    print(f"Pot: {data['pot']}")
    print(f"State: {data['state']}")
    print(f"Current bet: {data['current_bet']}")

@sio.on('player_update')
def on_player_update(data):
    print('\nPlayer Update:')
    print(f"Your cards: {data['your_cards']}")
    print(f"Allowed actions: {data['allowed_actions']}")

@sio.on('joined')
def on_joined(data):
    print(f"\nJoined room: {data['room']}")
    print(f"Name: {data['name']}")
    print(f"Starting chips: {data['chips']}")

@sio.on('room_created')
def on_room_created(data):
    print(f"\nRoom created: {data['room']}")
    # Auto-join the created room
    sio.emit('join_room', {'room': data['room'], 'name': 'Player 1'})

@sio.on('message')
def on_message(data):
    print(f"\nMessage: {data['msg']}")

@sio.on('showdown')
def on_showdown(data):
    print('\nShowdown:')
    if 'winners' in data:
        for winner in data['winners']:
            print(f"Winner: {winner['name']}")
            if 'hand_name' in winner:
                print(f"Hand: {winner['hand_name']}")
            if 'combo' in winner:
                print(f"Combo: {winner['combo']}")
    print(f"Community cards: {data['community']}")

def main():
    # Connect to the server
    sio.connect('http://localhost:5000')
    
    try:
        # Create a room
        sio.emit('create_room', {})
        time.sleep(1)  # Wait for room creation
        
        # Keep the script running
        input("Press Enter to exit...")
    except KeyboardInterrupt:
        pass
    finally:
        sio.disconnect()

if __name__ == '__main__':
    main()
