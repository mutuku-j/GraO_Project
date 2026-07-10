from flask import render_template, url_for, flash, redirect, request, jsonify, session, Response, abort
from sqlalchemy import func
from models import db, Booking
from app import app, db, bcrypt, mail
from flask_mail import Message
from models import Pitch, Booking
from datetime import datetime, date, timedelta
from functools import wraps
import os
import csv
from io import StringIO

@app.route("/")
def index():
    return render_template('index.html')


def is_admin():
    return session.get('admin_authenticated', False)


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not is_admin():
            return redirect(url_for('admin_login', next=request.path))
        return view(*args, **kwargs)
    return wrapped_view


@app.route('/availability')
def availability_dashboard():
    pitches = Pitch.query.order_by(Pitch.id).all()
    return render_template('availability.html', pitches=pitches)


@app.route('/availability_data/<int:pitch_id>')
def availability_data(pitch_id):
    bookings = Booking.query.filter_by(pitch_id=pitch_id).order_by(Booking.booking_date, Booking.start_time).all()
    events = []

    for booking in bookings:
        start = datetime.combine(booking.booking_date, booking.start_time)
        end = datetime.combine(booking.booking_date, booking.end_time)
        events.append({
            'id': booking.id,
            'title': f"{booking.booker_name} ({booking.status})",
            'start': start.isoformat(),
            'end': end.isoformat(),
            'color': '#198754' if booking.is_verified else '#dc3545',
            'backgroundColor': '#198754' if booking.is_verified else '#dc3545',
            'borderColor': '#155724' if booking.is_verified else '#721c24',
        })

    return jsonify(events)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')

        if email == admin_email and password == admin_password:
            session['admin_authenticated'] = True
            flash('Admin login successful.', 'success')
            next_page = request.args.get('next') or url_for('admin_dashboard')
            return redirect(next_page)

        flash('Invalid admin credentials.', 'danger')

    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_authenticated', None)
    flash('Admin logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    today = date.today()
    bookings = Booking.query.order_by(Booking.booking_date, Booking.start_time).all()
    stats = {
        'total_pitches': Pitch.query.count(),
        'total_bookings': len(bookings),
        'upcoming_bookings': Booking.query.filter(Booking.booking_date >= today).count(),
        'past_bookings': Booking.query.filter(Booking.booking_date < today).count()
    }
    pitches = Pitch.query.order_by(Pitch.id).all()
    return render_template('admin_dashboard.html', bookings=bookings, pitches=pitches, stats=stats)


@app.route('/add_pitch', methods=['POST'])
@admin_required
def add_pitch():
    pitch_name = request.form.get('pitch_name')
    if not pitch_name:
        flash('Please enter a pitch name.', 'danger')
        return redirect(url_for('admin_dashboard'))

    new_pitch = Pitch(pitch_name=pitch_name)
    db.session.add(new_pitch)
    db.session.commit()
    flash(f'Pitch "{pitch_name}" added successfully.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/rename_pitch/<int:pitch_id>', methods=['POST'])
@admin_required
def rename_pitch(pitch_id):
    pitch = Pitch.query.get_or_404(pitch_id)
    new_name = request.form.get('new_name')
    if not new_name:
        flash('Pitch name cannot be empty.', 'danger')
        return redirect(url_for('admin_dashboard'))

    pitch.pitch_name = new_name
    db.session.commit()
    flash('Pitch renamed successfully.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/toggle_pitch_status/<int:pitch_id>', methods=['POST'])
@admin_required
def toggle_pitch_status(pitch_id):
    pitch = Pitch.query.get_or_404(pitch_id)
    pitch.status = 'blocked' if pitch.status == 'available' else 'available'
    db.session.commit()
    flash(f'Pitch status updated to {pitch.status}.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/delete_pitch/<int:pitch_id>', methods=['POST'])
@admin_required
def delete_pitch(pitch_id):
    pitch = Pitch.query.get_or_404(pitch_id)
    pitch_name = pitch.pitch_name
    Booking.query.filter_by(pitch_id=pitch_id).delete()
    db.session.delete(pitch)
    db.session.commit()
    flash(f'Pitch "{pitch_name}" deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/delete_booking/<int:id>', methods=['POST'])
@admin_required
def delete_booking(id):
    booking = Booking.query.get_or_404(id)
    db.session.delete(booking)
    db.session.commit()
    flash('Booking cancelled successfully.', 'success')
    return redirect(url_for('admin_dashboard'))



def send_booking_email(booking):
    try:
        pitch_name = booking.pitch_ref.pitch_name if booking.pitch_ref else 'Selected Pitch'
        start = booking.start_time.strftime('%H:%M')
        end = booking.end_time.strftime('%H:%M')
        subject = f'GraO Booking Confirmation — {pitch_name} on {booking.booking_date}'
        recipients = [booking.guest_email]

        body = (
            f"Hello {booking.booker_name},\n\n"
            f"Your booking for {pitch_name} has been confirmed.\n\n"
            f"Date: {booking.booking_date}\n"
            f"Time: {start} - {end}\n"
            f"Purpose: {booking.purpose}\n\n"
            "Thank you,\nGraO Team"
        )

        html = (
            f"<p>Hello {booking.booker_name},</p>"
            f"<p>Your booking for <strong>{pitch_name}</strong> has been <strong>confirmed</strong>.</p>"
            "<ul>"
            f"<li><strong>Date:</strong> {booking.booking_date}</li>"
            f"<li><strong>Time:</strong> {start} - {end}</li>"
            f"<li><strong>Purpose:</strong> {booking.purpose}</li>"
            "</ul>"
            "<p>Thank you,<br/>GraO Team</p>"
        )

        msg = Message(subject=subject, recipients=recipients, body=body, html=html)
        mail.send(msg)
    except Exception as e:
        app.logger.error(f'Failed to send booking email: {e}')


@app.route("/book", methods=['GET', 'POST'])
def book_pitch():
    if request.method == 'POST':
        pitch_id = int(request.form.get('pitch_id'))
        date_str = request.form.get('booking_date')
        start_str = request.form.get('start_time')
        end_str = request.form.get('end_time')
        purpose = request.form.get('purpose')
        name = request.form.get('booker_name') 
        guest_email = request.form.get('guest_email')

        # Date/Time conversion logic remains the same...
        selected_date = date.fromisoformat(date_str)
        s_time = datetime.strptime(start_str, '%H:%M').time()
        e_time = datetime.strptime(end_str, '%H:%M').time()

        pitch = Pitch.query.get_or_404(pitch_id)
        if pitch.status != 'available':
            flash('This pitch is currently blocked for new bookings.', 'danger')
            return redirect(url_for('book_pitch'))

        # Check for booking conflicts
        conflicting_bookings = Booking.query.filter(
            Booking.pitch_id == pitch_id,
            Booking.booking_date == selected_date,
            Booking.start_time < e_time,
            Booking.end_time > s_time
        ).all()

        if conflicting_bookings:
            flash("This time slot is already booked. Please choose a different time.", "danger")
            return redirect(url_for('book_pitch'))

        # Create booking for guests
        new_booking = Booking(
            pitch_id=pitch_id,
            user_id=None,
            booker_name=name,
            guest_email=guest_email,
            booking_date=selected_date,
            start_time=s_time,
            end_time=e_time,
            purpose=purpose,
            status='confirmed',
            is_verified=True
        )

        db.session.add(new_booking)
        db.session.commit()
        # Send confirmation email to guest if email provided
        if new_booking.guest_email:
            send_booking_email(new_booking)
        flash(f"Thank you {name}, your booking has been created successfully.", "success")
        return redirect(url_for('availability_dashboard'))

    pitches = Pitch.query.all()
    return render_template('book.html', pitches=pitches)


@app.route('/admin/download_reservations')
@admin_required
def download_reservations():
    bookings = Booking.query.order_by(Booking.booking_date, Booking.start_time).all()

    # Create a string buffer to write CSV data
    si = StringIO()
    cw = csv.writer(si)

    # Add CSV header
    cw.writerow([
        'Booking ID', 'Pitch Name', 'Booker Name', 'Guest Email', 'Booking Date',
        'Start Time', 'End Time', 'Purpose', 'Status', 'Verified'
    ])

    # Add booking data
    for booking in bookings:
        pitch_name = booking.pitch_ref.pitch_name if booking.pitch_ref else 'N/A'
        cw.writerow([
            booking.id, pitch_name, booking.booker_name, booking.guest_email,
            booking.booking_date.strftime('%Y-%m-%d'), booking.start_time.strftime('%H:%M'),
            booking.end_time.strftime('%H:%M'), booking.purpose, booking.status,
            'Yes' if booking.is_verified else 'No'
        ])

    output = si.getvalue()
    return Response(output, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=reservations.csv"})