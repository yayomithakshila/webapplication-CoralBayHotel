from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime


app = Flask(__name__)

# Configure the database (SQLite)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookings.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'  # For flash messages

# Configure Flask-Mail for email notifications
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'coralbayhoteltest@gmail.com'
app.config['MAIL_PASSWORD'] = 'hvci pojl pllw ptgm'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

# Initialize database and mail
db = SQLAlchemy(app)
mail = Mail(app)

# Room model
class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_type = db.Column(db.String(100), nullable=False)
    room_number = db.Column(db.String(50), nullable=False, unique=True)
    availability = db.Column(db.Boolean, default=True)  

    def __repr__(self):
        return f"<Room {self.room_type}, {self.room_number}>"

# Booking model
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guest_name = db.Column(db.String(100), nullable=False)
    guest_email = db.Column(db.String(100), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    check_in_date = db.Column(db.String(20), nullable=False)
    check_out_date = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f"<Booking {self.guest_name}, {self.room_id}>"

# Initialize database and add default rooms
with app.app_context():
    db.drop_all()  # Reset tables (Remove this in production)
    db.create_all()

    if not Room.query.first():
        rooms = [
            Room(room_type='Single', room_number='101'),
            Room(room_type='Single', room_number='102'),
            Room(room_type='Family', room_number='201'),
            Room(room_type='Family', room_number='202'),
            Room(room_type='Double', room_number='301'),
            Room(room_type='Double', room_number='302'),
            Room(room_type='Double', room_number='303'),
            Room(room_type='Double', room_number='304'),
            Room(room_type='Double', room_number='305'),
            Room(room_type='Double', room_number='306'),
        ]
        db.session.add_all(rooms)
        db.session.commit()

# Function to update room availability after checkout and send cancellation emails
def update_room_availability():
    today = datetime.today().strftime('%Y-%m-%d')
    expired_bookings = Booking.query.filter(Booking.check_out_date == today).all()

    for booking in expired_bookings:
        room = Room.query.get(booking.room_id)
        if room:
            # Mark the room as available again
            room.availability = True
            db.session.delete(booking)

            # Send cancellation email to guest
            msg_guest = Message('Booking Cancellation Notice', sender='coralbayhoteltest@gmail.com', recipients=[booking.guest_email])
            msg_guest.body = f"""
            Dear {booking.guest_name},

            We regret to inform you that your reservation at Coral Bay Hotel has been automatically cancelled.

            Room Type: {room.room_type}
            Room Number: {room.room_number}
            Check-In Date: {booking.check_in_date}
            Check-Out Date: {booking.check_out_date}

            This cancellation occurred because your checkout date has passed without confirmation of arrival.

            If you still wish to book a room, please visit our website or contact us directly.

            We hope to welcome you in the future!

            - Coral Bay Hotel
            +94 234 567 890
            coralbayhoteltest@gmail.com
            123 Coral Street, Hikkaduwa, Sri Lanka
            """
            mail.send(msg_guest)

            # Send notification email to hotel staff
            msg_hotel = Message('Booking Cancellation Alert', sender='coralbayhoteltest@gmail.com', recipients=['coralbayhoteltest@gmail.com'])
            msg_hotel.body = f"""
            A booking has been automatically cancelled:

            Guest Name: {booking.guest_name}
            Guest Email: {booking.guest_email}
            Room Type: {room.room_type}
            Room Number: {room.room_number}
            Check-In Date: {booking.check_in_date}
            Check-Out Date: {booking.check_out_date}

            The room is now available for new bookings.

            - Coral Bay Hotel System
            """
            mail.send(msg_hotel)

    db.session.commit()


# Background scheduler to update availability daily
scheduler = BackgroundScheduler()
scheduler.add_job(update_room_availability, 'interval', days=1)
scheduler.start()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/book', methods=['GET', 'POST'])
def book():
    message = None
    room_types = Room.query.with_entities(Room.room_type).distinct().all()
    room_types = [r.room_type for r in room_types]
    available_rooms = []
    selected_room_type = None

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'check_availability':
            selected_room_type = request.form.get('room_type')
            available_rooms = Room.query.filter_by(room_type=selected_room_type, availability=True).all()

            if not available_rooms:
                message = "No available rooms for the selected type."

            return render_template('book.html', room_types=room_types, available_rooms=available_rooms, message=message, selected_room_type=selected_room_type)

        elif action == 'confirm_booking':
            name = request.form['name']
            email = request.form['email']
            room_id = request.form['room_id']
            check_in_date = request.form['check_in_date']
            check_out_date = request.form['check_out_date']

            selected_room = Room.query.get(room_id)
            if selected_room and selected_room.availability:
                selected_room.availability = False
                booking = Booking(guest_name=name, guest_email=email, room_id=room_id, 
                                  check_in_date=check_in_date, check_out_date=check_out_date)
                db.session.add(booking)
                db.session.commit()

                # Send confirmation email to guest
                msg_guest = Message('Booking Confirmation', sender='coralbayhoteltest@gmail.com', recipients=[email])
                msg_guest.body = f"""
                Dear {name},

                Your reservation at Coral Bay Hotel is confirmed!

                Room Type: {selected_room.room_type}
                Room Number: {selected_room.room_number}
                Check-In: {check_in_date}
                Check-Out: {check_out_date}

                If you are not coming please send an email to cancel the booking.
                See you soon!

                - Coral Bay Hotel
                +94 234 567 890
                coralbayhoteltest@gmail.com
                123 Coral Street, Hikkaduwa, Sri Lanka
                """
                mail.send(msg_guest)

                # Send notification email to hotel
                msg_hotel = Message('New Booking Alert', sender='coralbayhoteltest@gmail.com', recipients=['coralbayhoteltest@gmail.com'])
                msg_hotel.body = f"""
                New Booking Received:

                Guest Name: {name}
                Guest Email: {email}
                Room Type: {selected_room.room_type}
                Room Number: {selected_room.room_number}
                Check-In: {check_in_date}
                Check-Out: {check_out_date}

                Please prepare the room accordingly.

                - Coral Bay Hotel System
                """
                mail.send(msg_hotel)

                message = f"Booking successful! Room {selected_room.room_number} confirmed."
            else:
                message = "Room is no longer available."

    return render_template('book.html', room_types=room_types, available_rooms=available_rooms, message=message, selected_room_type=selected_room_type)

if __name__ == '__main__':
    app.run(debug=True)
