#!/bin/bash

# Kill any existing tmux sessions and clean up processes
echo "Cleaning up existing sessions..."
tmux kill-server 2>/dev/null || true
pkill -f "python main.py" 2>/dev/null || true
pkill -f "code ." 2>/dev/null || true

# Create a new tmux session named "ra-dev"
tmux new-session -d -s ra-dev

# Split the window into two panes
tmux split-window -h

# Set up the RAG server (left pane)
tmux send-keys -t ra-dev:0.0 "cd rag && echo 'Starting RAG server...' && source venv/bin/activate && pip install -r requirements.txt && python run.py" C-m

# Set up VS Code with the extension (right pane)
tmux send-keys -t ra-dev:0.1 "cd laitex-extension && echo 'Opening VS Code with extension...' && code . --extensionDevelopmentPath=$(pwd)" C-m

# Attach to the session
echo "Starting development session..."
echo "Use 'tmux attach-session -t ra-dev' to attach to the session"
echo "Use 'tmux kill-session -t ra-dev' to stop the session"
echo ""
echo "Pane layout:"
echo "┌─────────────┬─────────────┐"
echo "│             │             │"
echo "│   RAG       │   VS Code   │"
echo "│  Server     │  Extension  │"
echo "│             │             │"
echo "└─────────────┴─────────────┘"
echo ""
echo "Attaching to session now..."
tmux attach-session -t ra-dev 