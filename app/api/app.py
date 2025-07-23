from flask import Flask, request, redirect, url_for, jsonify
from app.models.db import db
from app.config import get_config 
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config.from_object(get_config()) 

# Initialisation de la base de données (SQLAlchemy)
db.init_app(app)



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
