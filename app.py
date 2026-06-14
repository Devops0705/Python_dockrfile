from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cinema.db'
db = SQLAlchemy(app)

# ---------- Models ----------
class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    price = db.Column(db.Float)
    seats = db.Column(db.JSON, default=dict)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ref = db.Column(db.String(20), unique=True)
    movie_id = db.Column(db.Integer)
    movie_title = db.Column(db.String(100))
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    seats = db.Column(db.String(200))
    total = db.Column(db.Float)
    date = db.Column(db.DateTime, default=datetime.utcnow)

# ---------- Init database ----------
with app.app_context():
    db.create_all()
    if Movie.query.count() == 0:
        for title, price in [("Inception", 12.5), ("The Dark Knight", 13.0), ("Interstellar", 14.0)]:
            seats = {f"{r}{c}": True for r in "ABCDE" for c in range(1,6)}
            db.session.add(Movie(title=title, price=price, seats=seats))
        db.session.commit()

# ---------- Routes ----------
@app.route('/')
def index():
    return render_template('index.html', movies=Movie.query.all())

@app.route('/movie/<int:id>')
def movie(id):
    return render_template('book.html', movie=Movie.query.get_or_404(id))

@app.route('/book/<int:id>', methods=['POST'])
def book(id):
    movie = Movie.query.get_or_404(id)
    selected = request.form.getlist('seats')
    if not selected:
        flash('Select at least one seat', 'danger')
        return redirect(url_for('movie', id=id))
    for s in selected:
        if not movie.seats.get(s, False):
            flash(f'Seat {s} already booked', 'danger')
            return redirect(url_for('movie', id=id))
    session['booking'] = {'movie_id': id, 'seats': selected}
    return render_template('form.html', movie=movie, seats=selected)

@app.route('/confirm', methods=['POST'])
def confirm():
    data = session.pop('booking', None)
    if not data:
        return redirect(url_for('index'))
    movie = Movie.query.get(data['movie_id'])
    seats = data['seats']
    for s in seats:
        movie.seats[s] = False
    ref = secrets.token_hex(4).upper()
    total = len(seats) * movie.price
    booking = Booking(ref=ref, movie_id=movie.id, movie_title=movie.title,
                     name=request.form['name'], email=request.form['email'],
                     seats=','.join(seats), total=total)
    db.session.add(booking)
    db.session.commit()
    return render_template('confirm.html', booking=booking, seats=seats)

@app.route('/mybookings')
def mybookings():
    return render_template('list.html', bookings=Booking.query.all())

@app.route('/cancel/<ref>')
def cancel(ref):
    booking = Booking.query.filter_by(ref=ref).first_or_404()
    return render_template('cancel.html', booking=booking)

@app.route('/cancel/<ref>/do', methods=['POST'])
def do_cancel(ref):
    booking = Booking.query.filter_by(ref=ref).first_or_404()
    movie = Movie.query.get(booking.movie_id)
    for s in booking.seats.split(','):
        movie.seats[s] = True
    db.session.delete(booking)
    db.session.commit()
    flash('Booking cancelled', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
