#---------------Imports---------------
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
from flask_mail import Mail, Message
#---------------Database Connection and Other Functions----------------
app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
FILE_FOLDER = 'static/files'
app.config['FILE_FOLDER'] = FILE_FOLDER
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
FOR_EBOOK = {'pdf'}
app.config['SECRET_KEY'] = '12e4'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Armaan.123@localhost/library'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'armaan.nchougle@gmail.com'
app.config['MAIL_PASSWORD'] = 'gszd fsgs hahc wdrz'
mail = Mail(app)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

def send_email(subject, recipient, body):
    msg = Message(subject, sender='armaan.nchougle@gmail.com', recipients=[recipient])
    msg.body = body
    mail.send(msg)
#---------------Database Models---------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    borrow_requests = db.relationship('BorrowRequest', backref='user', lazy=True)
    is_banned = db.Column(db.Boolean, default=False)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    available_copies = db.Column(db.Integer, default=1)
    total_copies = db.Column(db.Integer, default=1)
    image_filename = db.Column(db.String(255), nullable=True)  
    borrow_requests = db.relationship('BorrowRequest', backref='book', lazy=True)


class BorrowRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  
    due_date = db.Column(db.DateTime)
class Ebook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    course = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    img_filename = db.Column(db.String(255), nullable=True)  
    pdf_file = db.Column(db.String(255), nullable=True) 
#---------------Login manager and file managing---------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
def all_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in FOR_EBOOK
# ---------------Routes---------------
@app.route('/')
def home():
    recent = Book.query.order_by(Book.id.desc()).limit(3).all()
    genres = db.session.query(Book.genre).distinct().all()
    return render_template('home.html', recent=recent, genres=genres)
#---------------Login---------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid email or password')
    return render_template('login.html')
#---------------Logout---------------
@app.route('/logout')
def logout():
    logout_user() 
    return redirect(url_for('login'))  
#---------------Register---------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
            
        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            name=name
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')
#---------------User Dashboard---------------
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    borrow_requests = BorrowRequest.query.filter_by(user_id=current_user.id).all()
    return render_template('user_dashboard.html', borrow_requests=borrow_requests)
#---------------Books---------------
@app.route('/books')
def books():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of books per page
    genre = request.args.get('genre')
    search = request.args.get('search')
    query = Book.query
    
    # Fetch distinct genres from the database
    genres = db.session.query(Book.genre).distinct().all()
    genres = [g[0] for g in genres]  # Extract genre strings from the query result
    
    if genre:
        query = query.filter_by(genre=genre)
    if search:
        query = query.filter(Book.title.contains(search) | Book.author.contains(search))
        
    books = query.paginate(page=page, per_page=per_page)
    return render_template('books.html', books=books, genres=genres)
#---------------Book Details---------------
@app.route('/book/<int:book_id>')
def book_details(book_id):
    book = Book.query.get_or_404(book_id)
    if current_user.is_authenticated and not current_user.is_admin:
        if current_user.is_banned:
            flash('Your account is banned from accessing books', 'danger')
            return redirect(url_for('books'))
    return render_template('book_details.html', book=book)
#---------------Ebooks---------------
@app.route('/ebooks')
def ebooks():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of ebooks per page
    course = request.args.get('course')
    search = request.args.get('search')
    query = Ebook.query

    # Fetch distinct courses from the database
    courses = db.session.query(Ebook.course).distinct().all()
    courses = [c[0] for c in courses]  # Extract course strings from the query result

    if course:
        query = query.filter_by(course=course)
    if search:
        query = query.filter(Ebook.name.contains(search) | Ebook.author.contains(search))

    book = query.paginate(page=page, per_page=per_page)
    return render_template('ebooks.html', book=book, courses=courses)
#---------------Ebook Details---------------
@app.route('/ebook/<int:book_id>')
def ebook_details(book_id):
    ebook = Ebook.query.get_or_404(book_id)
    if current_user.is_authenticated and not current_user.is_admin:
        if current_user.is_banned:
            flash('Your account is banned from accessing ebooks', 'danger')
            return redirect(url_for('ebooks'))
    return render_template('ebook_details.html', book=ebook)
#---------------Sending Borrow Request---------------
@app.route('/borrow/<int:book_id>', methods=['POST'])
@login_required
def borrow_book(book_id):
    if current_user.is_banned:
        flash('Your account is banned from borrowing books', 'danger')
        return redirect(url_for('books'))
    book = Book.query.get_or_404(book_id)
    if book.available_copies > 0:
        borrow_request = BorrowRequest(user_id=current_user.id, book_id=book_id)
        db.session.add(borrow_request)
        db.session.commit()
        flash('Borrow request submitted successfully')
    else:
        flash('No copies available')
    return redirect(url_for('books'))
#---------------Admin---------------
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    pending_requests = BorrowRequest.query.filter_by(status='pending').all()
    borrowed_books = BorrowRequest.query.filter_by(status='approved').all()
    users = User.query.all()
    books = Book.query.all()
    ebooks = Ebook.query.all()
    
    return render_template('admin_dashboard.html',
                         pending_requests=pending_requests,
                         borrowed_books=borrowed_books,
                         users=users,
                         books=books,
                         ebooks=ebooks)
#---------------Admin Borrow Request Handling---------------
@app.route('/admin/request/<int:request_id>/<action>')
@login_required
def handle_request(request_id, action):
    borrow_request = BorrowRequest.query.get_or_404(request_id)
    if action == 'approve' and borrow_request.book.available_copies > 0:
        borrow_request.status = 'approved'
        borrow_request.book.available_copies -= 1
        borrow_request.due_date = datetime.utcnow() + timedelta(days=14)
        send_email(
            'Borrow Request Approved',
            borrow_request.user.email,
            f'Your borrow request for "{borrow_request.book.title}" has been approved. Due date: {borrow_request.due_date.strftime("%Y-%m-%d")}'
        )
    elif action == 'reject':
        borrow_request.status = 'rejected'
        send_email(
            'Borrow Request Rejected',
            borrow_request.user.email,
            f'Your borrow request for "{borrow_request.book.title}" has been rejected.'
        )
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

#---------------Admin Book Editing---------------
@app.route('/admin/book/<int:book_id>', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
        
    book = Book.query.get_or_404(book_id)
    if request.method == 'POST':
        book.title = request.form.get('title')
        book.author = request.form.get('author')
        book.genre = request.form.get('genre')
        book.description = request.form.get('description')
        book.total_copies = int(request.form.get('total_copies'))
        book.available_copies = int(request.form.get('available_copies'))
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_book.html', book=book)
#---------------Admin Ebook Editing---------------
@app.route('/admin/ebook/<int:book_id>', methods=['GET', 'POST'])
@login_required
def edit_ebook(book_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
        
    ebooks = Ebook.query.get_or_404(book_id)  
    
    if request.method == 'POST':
        ebooks.name = request.form.get('name')
        ebooks.author = request.form.get('author')
        ebooks.course = request.form.get('course')
        ebooks.description = request.form.get('description')
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    
    return render_template('edit_ebook.html',book=ebooks) 

#---------------Ebook Deleting---------------
@app.route('/admin/ebook/delete/<int:book_id>', methods=['POST'])
@login_required
def delete_ebook(book_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
        
    ebooks = Ebook.query.get_or_404(book_id)
    BorrowRequest.query.filter_by(book_id=book_id).delete()
    db.session.delete(ebooks)
    db.session.commit()
    
    flash('Book deleted successfully')
    return redirect(url_for('admin_dashboard'))
#---------------Book Deleting---------------
@app.route('/admin/book/delete/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
        
    book = Book.query.get_or_404(book_id)
    BorrowRequest.query.filter_by(book_id=book_id).delete()
    db.session.delete(book)
    db.session.commit()
    
    flash('Book deleted successfully')
    return redirect(url_for('admin_dashboard'))
#---------------Book Adding---------------
@app.route('/admin/book/add', methods=['GET', 'POST'])
@login_required
def add_book():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        genre = request.form.get('genre')
        description = request.form.get('description')
        total_copies = int(request.form.get('total_copies'))
        available_copies = int(request.form.get('available_copies'))
        #Image Upload
        image_file = request.files.get('image')
        image_filename = None

        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            image_filename = filename
        #Create New Entry
        new_book = Book(
            title=title,
            author=author,
            genre=genre,
            description=description,
            total_copies=total_copies,
            available_copies=available_copies,
            image_filename=image_filename
        )
        db.session.add(new_book)
        db.session.commit()

        flash('Book added successfully!')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_book.html')
#---------------Ebook Adding---------------
@app.route('/admin/ebook/add', methods=['GET', 'POST'])
@login_required
def add_ebook():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        author = request.form.get('author')
        course = request.form.get('course')
        description = request.form.get('description')
        
        # Handling Image Upload
        image_file = request.files.get('image')
        image_filename = None
        if image_file and allowed_file(image_file.filename):
            image_filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image_file.save(image_path)
        
        # Handling PDF Upload
        pdf_file = request.files.get('pdf')
        pdf_filename = None
        if pdf_file and all_file(pdf_file.filename):
            pdf_filename = secure_filename(pdf_file.filename)
            pdf_path = os.path.join(app.config['FILE_FOLDER'], pdf_filename)
            pdf_file.save(pdf_path)
        
        # Create new Ebook entry
        new_ebook = Ebook(
            name=name,
            author=author,
            course=course,
            description=description,
            img_filename=image_filename,
            pdf_file=pdf_filename
        )
        db.session.add(new_ebook)
        db.session.commit()

        flash('Ebook added successfully!')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_ebook.html')
#---------------Adding User---------------
@app.route('/admin/user/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('add_user'))

   
        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            name=name,
            is_admin=True if role == 'admin' else False
        )
        db.session.add(user)
        db.session.commit()

        flash('User added successfully', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('add_user.html')
#---------------User Deleting---------------
@app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # Delete all borrow requests associated with the user
    BorrowRequest.query.filter_by(user_id=user_id).delete()
    
    # Delete the user
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully', 'success')
    return redirect(url_for('admin_dashboard'))
#---------------Admin Book Return---------------
@app.route('/admin/return_book/<int:request_id>', methods=['POST'])
@login_required
def admin_return_book(request_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    borrow_request = BorrowRequest.query.get_or_404(request_id)
    borrow_request.status = 'returned'
    borrow_request.book.available_copies += 1
    db.session.commit()
    
    flash('Book marked as returned successfully', 'success')
    return redirect(url_for('admin_dashboard'))
#---------------Admin Ban User---------------
@app.route('/admin/ban_user/<int:user_id>', methods=['POST'])
@login_required
def ban_user(user_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    user.is_banned = True
    db.session.commit()
    
    flash(f'User {user.name} has been banned', 'success')
    return redirect(url_for('admin_dashboard'))
#---------------Admin Unban User---------------
@app.route('/admin/unban_user/<int:user_id>', methods=['POST'])
@login_required
def unban_user(user_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    user.is_banned = False
    db.session.commit()
    
    flash(f'User {user.name} has been unbanned', 'success')
    return redirect(url_for('admin_dashboard'))
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        #---------------Create admin user if not exists---------------
        admin = User.query.filter_by(email='admin@library.com').first()
        if not admin:
            admin = User(
                email='admin@library.com',
                password_hash=generate_password_hash('admin123'),
                name='Admin',
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)
    