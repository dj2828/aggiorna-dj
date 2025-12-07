@echo off
py zip.py
git add .
git commit -m "Aggiornamento file zip"
git push origin main