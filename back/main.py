from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI()

# Правильный путь к фронтенду
frontend_path = os.path.join(os.path.dirname(__file__), "..", "front")

@app.get("/")
async def root():
    return FileResponse(os.path.join(frontend_path, "index.html"))

# Раздаем статику
app.mount("/static", StaticFiles(directory=frontend_path), name="static")