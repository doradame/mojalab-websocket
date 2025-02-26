import eventlet
eventlet.monkey_patch()  # Patch standard library for async support
from flask import Flask, request, Blueprint
from flask_socketio import SocketIO, emit
import random
import time
import threading
from logger import logging

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

games_blueprint = Blueprint('games', __name__)

# Game settings
GRID_SIZE = 20
START_POSITION = [(5, 5)]
DIRECTIONS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}

# Store separate game states per client
games = {}  # { session_id: game_state }
game_threads = {}  # { session_id: game_loop_thread }

def new_food(game_state):
    """
    Generate a new food position that is not occupied by any snake.
    Args:
        game_state (dict): The current state of the game, containing the positions of the player and AI snakes.
    Returns:
        tuple: A tuple representing the coordinates of the new food position.
    """
    while True:
        food = (random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1))
        if food not in game_state["player_snake"] and food not in game_state["ai_snake"]:
            return food

def reset_game(session_id):
    """
    Resets the game state for a given session.
    This function initializes or resets the game state for a specific session ID.
    It sets the initial positions of the player and AI snakes, places the food,
    and sets the initial directions and running state.
    Args:
        session_id (str): The unique identifier for the game session.
    Returns:
        None
    """
    logging.info(f"🔄 Resetting Game State for {session_id}")
    games[session_id] = {
        "player_snake": START_POSITION[:],
        "ai_snake": [(10, 10)],
        "food": new_food(games[session_id]) if session_id in games else (10, 10),
        "player_direction": "right",
        "ai_direction": "left",
        "running": False
    }

def move_snake(snake, direction, game_state, session_id, is_player=False):
    """
    Move the snake in the specified direction and update the game state.
    Parameters:
    snake (list of tuple): The current positions of the snake's segments.
    direction (str): The direction in which to move the snake ('up', 'down', 'left', 'right').
    game_state (dict): The current state of the game, including positions of both snakes and the food.
    session_id (str): The session ID for the current game.
    is_player (bool): Flag indicating whether the snake belongs to the player (True) or the AI (False).
    Returns:
        None
    """
    dx, dy = DIRECTIONS[direction]
    # Calculate the new head position
    new_head = (snake[-1][0] + dx, snake[-1][1] + dy)
    # 🚨 Check wall collision
    if new_head[0] < 0 or new_head[0] >= GRID_SIZE or new_head[1] < 0 or new_head[1] >= GRID_SIZE:
        logging.info(f"🔥 Game Over! {'Player' if is_player else 'AI'} hit the wall.")
        socketio.emit("game_over", {"winner": "AI" if is_player else "Player"}, room=session_id, namespace="/snake_game")
        reset_game(session_id)
        return  

    # 🚨 Check self-collision
    if new_head in snake:
        logging.info(f"🔥 Game Over! {'Player' if is_player else 'AI'} collided with itself.")
        socketio.emit("game_over", {"winner": "AI" if is_player else "Player"}, room=session_id, namespace="/snake_game")
        reset_game(session_id)
        return  

    # 🚨 Check collision with the other snake
    opponent_snake = game_state["ai_snake"] if is_player else game_state["player_snake"]
    if new_head in opponent_snake:
        logging.info(f"🔥 Game Over! {'Player' if is_player else 'AI'} collided with the opponent.")
        socketio.emit("game_over", {"winner": "AI" if is_player else "Player"}, room=session_id, namespace="/snake_game")
        reset_game(session_id)
        return
    
    snake.append(new_head)# Add the new head position to the snake
    if new_head != game_state["food"]:
        # Remove the tail segment if the snake did not eat the food
        snake.pop(0)

def ai_choose_move(game_state):
    """
    Determines the best move for the AI (not Real AI) snake based on the shortest distance to the food.
    Args:
        game_state (dict): The current state of the game, containing:
            - "ai_snake" (list of tuples): The coordinates of the AI snake's body segments.
            - "food" (tuple): The coordinates of the food.
            - "player_snake" (list of tuples): The coordinates of the player's snake body segments.
            - "ai_direction" (str): The current direction of the AI snake.
    Returns:
        str: The direction in which the "AI" snake should move next.
    """
    head_x, head_y = game_state["ai_snake"][-1]
    food_x, food_y = game_state["food"]

    best_move = None
    options = []

    for direction, (dx, dy) in DIRECTIONS.items(): # Check all possible moves
        new_x, new_y = head_x + dx, head_y + dy

        if (0 <= new_x < GRID_SIZE and 0 <= new_y < GRID_SIZE and 
            (new_x, new_y) not in game_state["ai_snake"] and 
            (new_x, new_y) not in game_state["player_snake"]): # Check if the move is valid
            
            distance = abs(new_x - food_x) + abs(new_y - food_y) # Manhattan distance to the food
            options.append((distance, direction)) # Store the distance and direction

    if options:
        best_move = min(options)[1] # Choose the move with the shortest distance to the food
    else:
        best_move = game_state["ai_direction"] # Keep moving in the same direction if no valid moves

    game_state["ai_direction"] = best_move # Update the AI snake's direction
    return best_move # Return the chosen move

def register_socketio_events(socketio):
    @socketio.on("connect", namespace="/snake_game")
    def handle_connect():
        """
        Handle a new player connection to the websocket.
        This function is triggered when a new player connects. It logs the session ID
        of the new player and initializes the game state for the session.
        Returns:
            None
        """
        session_id = request.sid
        logging.info(f"✅ New player connected: {session_id}")
        reset_game(session_id)  # Properly initialize the game state

    @socketio.on("disconnect", namespace="/snake_game")
    def handle_disconnect(sid):
        """
        Handle player disconnection and clean up resources.
        
        Args:
            sid (str): The session ID of the disconnected client.
        """
        logging.info(f"❌ Player disconnected: {sid}")
        
        # Remove game state if it exists
        if sid in games:
            del games[sid]

        # Stop game thread safely
        if sid in game_threads:
            game_threads[sid]["running"] = False  # Stop the game loop
            thread = game_threads[sid]["thread"]
            
            # Ensure we don't join the current thread (which causes errors)
            if thread.is_alive() and threading.current_thread() != thread:
                thread.join()
            del game_threads[sid]

    @socketio.on("player_move", namespace="/snake_game")
    def handle_player_move(data):
        """
        Handles the player's move by updating the player's direction in the game session.
        Args:
            data (dict): A dictionary containing the move data. It should have a key "direction" 
                         which indicates the direction of the player's move.
        Returns:
            None
        """
        session_id = request.sid
        if session_id in games and data["direction"] in DIRECTIONS:
            games[session_id]["player_direction"] = data["direction"]

    @socketio.on("reset_game", namespace="/snake_game")
    def reset():
        """
        Resets the game state for the current session.
        This function retrieves the session ID from the request, logs the reset action,
        resets the game state for the session, and emits a game update event to the client.
        Emits:
            game_update (dict): The updated game state for the session.
        """
        
        session_id = request.sid
        logging.info(f"🔄 Resetting Game State for {session_id}")
        reset_game(session_id)
        socketio.emit("game_update", games[session_id], room=session_id, namespace="/snake_game")

    @socketio.on("start_game", namespace="/snake_game")
    def start():
        """
        Starts the game for the current session if it is not already running.
        This function retrieves the session ID from the request, checks if a game
        associated with that session ID is not already running, and if not, sets
        the game to running. It then creates and starts a new thread for the game
        loop, stores the thread in the game_threads dictionary, logs the start of
        the game, and emits a game update event to the client.
        Raises:
            KeyError: If the session ID is not found in the games dictionary.
        """       
        session_id = request.sid
        if session_id in games and not games[session_id]["running"]:
            games[session_id]["running"] = True
            
            # Store the actual thread in game_threads
            game_threads[session_id] = {
                "running": True,
                "thread": threading.Thread(target=game_loop, args=(session_id,), daemon=True)
            }
            game_threads[session_id]["thread"].start()
            
            logging.info(f"🚀 Game Started for {session_id}")
            socketio.emit("game_update", games[session_id], room=session_id, namespace="/snake_game")

    @socketio.on("update_game", namespace="/snake_game")
    def update_game(session_id=None):
        """
        Update the game state for a given session.
        This function updates the game state for a specific session by moving the player's snake and the AI snake.
        It also checks if either snake has eaten the food and updates the game state accordingly.
        Args:
            session_id (str, optional): The session ID for the game. If not provided, it defaults to the request's session ID.
        Returns:
            None
        """
        
        if session_id is None:
            session_id = request.sid

        if session_id not in games:
            return

        move_snake(games[session_id]["player_snake"], games[session_id]["player_direction"], games[session_id],session_id, is_player=True)
        move_snake(games[session_id]["ai_snake"], ai_choose_move(games[session_id]), games[session_id],session_id,is_player=False)

        if games[session_id]["player_snake"][-1] == games[session_id]["food"]:# Check if the player snake ate the food
            games[session_id]["player_snake"].append(games[session_id]["food"]) # Add a new segment to the player snake
            games[session_id]["food"] = new_food(games[session_id]) # Generate a new food position

        if games[session_id]["ai_snake"][-1] == games[session_id]["food"]: # Check if the AI snake ate the food
            games[session_id]["ai_snake"].append(games[session_id]["food"]) # Add a new segment to the AI snake
            games[session_id]["food"] = new_food(games[session_id]) # Generate a new food position

        socketio.emit("game_update", games[session_id], room=session_id, namespace="/snake_game")

    def game_loop(session_id):
        """
        Continuously updates the game state for a given session.
        Args:
            session_id (str): The unique identifier for the game session.
        The loop runs as long as the session_id is present in the 'games' dictionary
        and the 'running' flag in the 'game_threads' dictionary for the session_id is True.
        It calls the 'update_game' function to update the game state and then sleeps for 1 second
        before the next update.
        """
        
        while session_id in games and game_threads.get(session_id, {}).get("running", False):
            update_game(session_id)
            eventlet.sleep(1) # Update the game state every second

# Register socket events
register_socketio_events(socketio) # Register the socket events

if __name__ == "__main__":
    logging.info("🔥 Starting Flask WebSocket Server on port 5050...")
    socketio.run(app, host="0.0.0.0", port=5050, debug=False)