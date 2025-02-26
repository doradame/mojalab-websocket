# 🐍 WebSocket Snake Game with Flask, Socket.IO, and Nginx

This is a simple **WebSocket-based Snake game** demonstrating how to use **Flask + Socket.IO** for real-time communication, with **Nginx** serving as a reverse proxy and static file server.

This project is part of a WebSockets tutorial that will be available on [MojaLab](https://mojalab.com/introduction-to-websockets-and-socket-io/). Stay tuned for in-depth explanations on how WebSockets work, why they are useful, and how to integrate Flask-SocketIO into your own projects.

## 🛠 Tech Stack

This project uses the following technologies:

- **Flask** – A lightweight Python web framework.
- **Flask-SocketIO** – WebSockets support for Flask applications.
- **Eventlet** – A WSGI server used for async networking in Flask-SocketIO.
- **Nginx** – Serves static files and acts as a reverse proxy.
- **Docker & Docker Compose** – For containerized deployment.

**Why Eventlet?**  
We're using `eventlet` to efficiently handle multiple WebSocket connections and ensure our server remains responsive under concurrent loads.

## 🏗️ Project Structure

```
websocket-example/
├── backend/              # Flask + Socket.IO WebSocket server
│   ├── app.py
│   ├── requirements.txt
│   ├── Dockerfile
├── nginx/                # Nginx configuration + Frontend
│   ├── default.conf
│   ├── index.html
├── docker-compose.yml    # Manages backend + nginx containers
├── start.sh              # Start script
├── stop.sh               # Stop script
├── README.md             # This file
```

## 🚀 How to Run

### 1️⃣ **Start the Project**

Clone this repository into a folder of your choice:

```sh
   git clone https://github.com/doradame/mojalab-websocket.git
   cd websocket-snake
```

Then Run the following command:

```sh
./start.sh
```

This will:

- Build the Docker containers (if not built already).
- Start the **Flask WebSocket server** and **Nginx frontend**.

### 2️⃣ **Access the Game**

Once running, open a browser and go to:

```
http://localhost:8080
```

and play ! 

### 3️⃣ **Stop the Project**

Run:

```sh
./stop.sh
```

This will stop and remove all running containers.

---

## 🛠️ How It Works

- The **Flask WebSocket server** (`backend/app.py`) manages game logic and player interactions.
- **Nginx** serves the frontend (`index.html`) and proxies WebSocket traffic to Flask.
- **Docker Compose** manages both services, making deployment easy.

---

## 📌 Useful Commands

**Check running containers:**

```sh
docker ps
```

**View logs:**

```sh
docker compose logs -f
```

**Rebuild & Restart:**

```sh
./start.sh
```

---
