from fastapi import FastAPI
from app import models, database  # Use full package path 'app'

# Create the tables in the database
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "AstraTrade API is running!"}
