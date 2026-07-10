from app import db
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='team_manager')
    bookings = db.relationship('Booking', backref='author', lazy=True)

class Pitch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pitch_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='available')
    bookings = db.relationship('Booking', backref='pitch_ref', lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pitch_id = db.Column(db.Integer, db.ForeignKey('pitch.id'), nullable=False)
    # Changed: nullable=True because we aren't forcing login anymore
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) 
    
    # Store the name and email of the person booking
    booker_name = db.Column(db.String(100), nullable=False)
    guest_email = db.Column(db.String(100), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    
    booking_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    purpose = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='pending')


    