#!/usr/bin/env bash
# Starts Qdrant (Docker), the backend and the frontend, each in its own terminal window.
# Usage:  ./run.sh          start everything
#         ./run.sh stop     stop the Qdrant container (close the other terminals yourself)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---- adjust these if your folders are named differently ----
SERVER_DIR="$ROOT_DIR/server"
CLIENT_DIR="$ROOT_DIR/client"            # <- your React project folder
VENV_ACTIVATE="$SERVER_DIR/venv/bin/activate"
QDRANT_CONTAINER="qdrant"
QDRANT_STORAGE="$ROOT_DIR/qdrant_storage"
QDRANT_PORT=6333
# ------------------------------------------------------------

if [ "$1" = "stop" ]; then
  docker stop "$QDRANT_CONTAINER" && echo "Qdrant stopped."
  exit 0
fi

# ---- sanity checks ----
for dir in "$SERVER_DIR" "$CLIENT_DIR"; do
  if [ ! -d "$dir" ]; then
    echo "Folder not found: $dir  (edit the paths at the top of run.sh)"
    exit 1
  fi
done

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed or not on PATH."
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Cannot talk to Docker. Is the Docker service running, and is your user in the 'docker' group?"
  exit 1
fi

# ---- open a command in a new terminal window ----
open_terminal() {
  local title="$1" cmd="$2"
  local full="$cmd; echo; echo '[process exited - press Enter to close]'; read"

  if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal --title="$title" -- bash -c "$full"
  elif command -v konsole >/dev/null 2>&1; then
    konsole --title "$title" -e bash -c "$full" &
  elif command -v xfce4-terminal >/dev/null 2>&1; then
    xfce4-terminal --title="$title" -e "bash -c $(printf '%q' "$full")" &
  elif command -v x-terminal-emulator >/dev/null 2>&1; then
    x-terminal-emulator -e bash -c "$full" &
  elif command -v xterm >/dev/null 2>&1; then
    xterm -T "$title" -e bash -c "$full" &
  else
    echo "No supported terminal found (gnome-terminal, konsole, xfce4-terminal, xterm)."
    exit 1
  fi
}

# ---- 1. Qdrant ----
mkdir -p "$QDRANT_STORAGE"
if docker ps -a --format '{{.Names}}' | grep -qx "$QDRANT_CONTAINER"; then
  echo "Starting existing Qdrant container..."
  docker start "$QDRANT_CONTAINER" >/dev/null || exit 1
else
  echo "Creating Qdrant container..."
  docker run -d --name "$QDRANT_CONTAINER" \
    -p "$QDRANT_PORT:6333" -p 6334:6334 \
    -v "$QDRANT_STORAGE:/qdrant/storage" \
    qdrant/qdrant >/dev/null || exit 1
fi

echo -n "Waiting for Qdrant on port $QDRANT_PORT"
for _ in $(seq 1 30); do
  if (echo > "/dev/tcp/localhost/$QDRANT_PORT") 2>/dev/null; then
    echo " - ready."
    break
  fi
  echo -n "."
  sleep 1
done
if ! (echo > "/dev/tcp/localhost/$QDRANT_PORT") 2>/dev/null; then
  echo
  echo "Qdrant did not become ready. Check: docker logs $QDRANT_CONTAINER"
  exit 1
fi

# ---- 2. Backend ----
BACKEND_CMD="cd $(printf '%q' "$SERVER_DIR")"
if [ -f "$VENV_ACTIVATE" ]; then
  BACKEND_CMD="$BACKEND_CMD && source $(printf '%q' "$VENV_ACTIVATE")"
fi
BACKEND_CMD="$BACKEND_CMD && python3 main.py"
open_terminal "Backend" "$BACKEND_CMD"

# ---- 3. Frontend ----
FRONTEND_CMD="cd $(printf '%q' "$CLIENT_DIR") && { [ -d node_modules ] || npm install; } && npm run dev"
open_terminal "Frontend" "$FRONTEND_CMD"

echo "Started. Qdrant runs in Docker; backend and frontend are in their own terminal windows."
echo "Stop Qdrant later with: ./run.sh stop"