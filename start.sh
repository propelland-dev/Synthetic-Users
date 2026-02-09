#!/bin/bash

source venv/bin/activate

echo "Iniciando backend..."
cd backend
uvicorn api.main:app --reload &
BACKEND_PID=$!
cd ..

echo "Iniciando frontend..."
streamlit run frontend/app.py & 
FRONTEND_PID=$!

cleanup() {
    echo "Cerrando servicios..."

    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null

    # Esperar a que realmente terminen
    wait $BACKEND_PID 2>/dev/null
    wait $FRONTEND_PID 2>/dev/null

    echo "Todo detenido."
}

trap cleanup SIGINT SIGTERM EXIT

wait
