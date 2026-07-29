#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "========================================="
echo " Hamro Hospital - One Command Development Run"
echo "========================================="

if [ ! -x ".venv/bin/python" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate

echo "Installing/updating requirements..."
python -m pip install --upgrade pip
pip install -r hamro_hospital/requirements.txt

if [ ! -f "hamro_hospital/.env" ] && [ -f "hamro_hospital/.env.example" ]; then
  echo "Creating local .env from .env.example..."
  cp hamro_hospital/.env.example hamro_hospital/.env
fi

cd hamro_hospital

echo "Running migrations..."
python manage.py migrate

echo "Ensuring demo staff accounts..."
python manage.py create_demo_accounts || true

echo "Starting server at http://127.0.0.1:8000/"
echo "Login: /accounts/login/  Demo password: password"
echo "Press CTRL+C to stop."
python manage.py runserver
