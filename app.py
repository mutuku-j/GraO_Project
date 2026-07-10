import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from dotenv import load_dotenv

# 1. Load the variables from the .env file into the system
load_dotenv()

app = Flask(__name__)

# Fetch the key from the environment; local development can override it safely
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me-in-your-env')

# 2. Mail configuration using os.environ.get
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///grao.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# 4. Initialize Extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
mail = Mail(app)

# 6. IMPORT ROUTES
from routes import *

if __name__ == "__main__":
    app.run(debug=True)