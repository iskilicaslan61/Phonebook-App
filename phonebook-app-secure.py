# Import Flask modules
from flask import Flask, request, render_template, flash, redirect, url_for
from flaskext.mysql import MySQL
import boto3
import logging
import os
from werkzeug.security import safe_str_cmp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_ssm_parameters():
    """Safely retrieve SSM parameters with error handling"""
    try:
        ssm = boto3.client('ssm', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        
        # AWS SSM Parameters
        username_param = ssm.get_parameter(Name='/ismail/phonebook/username')
        password_param = ssm.get_parameter(Name="/ismail/phonebook/password", WithDecryption=True)
        
        # Get parameter values
        username = username_param['Parameter']['Value']
        password = password_param['Parameter']['Value']
        
        return username, password
    except Exception as e:
        logger.error(f"Failed to retrieve SSM parameters: {e}")
        raise

# Flask application
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-in-production')

# Get database credentials from SSM
try:
    db_username, db_password = get_ssm_parameters()
except Exception as e:
    logger.error(f"Failed to initialize database credentials: {e}")
    db_username, db_password = None, None

# Database configuration
app.config['MYSQL_DATABASE_HOST'] = os.getenv('DB_HOST', 'localhost')
app.config['MYSQL_DATABASE_USER'] = db_username
app.config['MYSQL_DATABASE_PASSWORD'] = db_password
app.config['MYSQL_DATABASE_DB'] = 'ismail_phonebook'
app.config['MYSQL_DATABASE_PORT'] = 3306

# Initialize MySQL
mysql = MySQL()
mysql.init_app(app)

def get_db_connection():
    """Get database connection with error handling"""
    try:
        connection = mysql.connect()
        connection.autocommit(True)
        return connection
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None

def init_phonebook_db():
    """Initialize phonebook table"""
    try:
        connection = get_db_connection()
        if not connection:
            return False
            
        cursor = connection.cursor()
        phonebook_table = """
        CREATE TABLE IF NOT EXISTS ismail_phonebook.phonebook(
        id INT NOT NULL AUTO_INCREMENT,
        name VARCHAR(100) NOT NULL,
        number VARCHAR(100) NOT NULL,
        PRIMARY KEY (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        cursor.execute(phonebook_table)
        cursor.close()
        connection.close()
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def find_persons(keyword):
    """Find persons by keyword using parameterized queries"""
    try:
        connection = get_db_connection()
        if not connection:
            return [{'name': 'Database Error', 'number': 'Connection failed'}]
            
        cursor = connection.cursor()
        
        # Use parameterized query to prevent SQL injection
        query = "SELECT * FROM phonebook WHERE LOWER(name) LIKE %s"
        search_term = f"%{keyword.strip().lower()}%"
        cursor.execute(query, (search_term,))
        
        result = cursor.fetchall()
        persons = [{'id': row[0], 'name': row[1].strip().title(), 'number': row[2]} for row in result]
        
        cursor.close()
        connection.close()
        
        if len(persons) == 0:
            persons = [{'name': 'No Result', 'number': 'No Result'}]
        return persons
    except Exception as e:
        logger.error(f"Error in find_persons: {e}")
        return [{'name': 'Error', 'number': 'Database operation failed'}]

def insert_person(name, number):
    """Insert person using parameterized queries"""
    try:
        connection = get_db_connection()
        if not connection:
            return 'Database connection failed'
            
        cursor = connection.cursor()
        
        # Check if person exists
        check_query = "SELECT * FROM phonebook WHERE LOWER(name) = %s"
        cursor.execute(check_query, (name.strip().lower(),))
        row = cursor.fetchone()
        
        if row is not None:
            cursor.close()
            connection.close()
            return f'Person with name {row[1].title()} already exists.'
        
        # Insert new person
        insert_query = "INSERT INTO phonebook (name, number) VALUES (%s, %s)"
        cursor.execute(insert_query, (name.strip().lower(), number))
        
        cursor.close()
        connection.close()
        return f'Person {name.strip().title()} added to Phonebook successfully'
    except Exception as e:
        logger.error(f"Error in insert_person: {e}")
        return 'Failed to add person to database'

def update_person(name, number):
    """Update person using parameterized queries"""
    try:
        connection = get_db_connection()
        if not connection:
            return 'Database connection failed'
            
        cursor = connection.cursor()
        
        # Check if person exists
        check_query = "SELECT * FROM phonebook WHERE LOWER(name) = %s"
        cursor.execute(check_query, (name.strip().lower(),))
        row = cursor.fetchone()
        
        if row is None:
            cursor.close()
            connection.close()
            return f'Person with name {name.strip().title()} does not exist.'
        
        # Update person
        update_query = "UPDATE phonebook SET name = %s, number = %s WHERE id = %s"
        cursor.execute(update_query, (row[1], number, row[0]))
        
        cursor.close()
        connection.close()
        return f'Phone record of {name.strip().title()} is updated successfully'
    except Exception as e:
        logger.error(f"Error in update_person: {e}")
        return 'Failed to update person in database'

def delete_person(name):
    """Delete person using parameterized queries"""
    try:
        connection = get_db_connection()
        if not connection:
            return 'Database connection failed'
            
        cursor = connection.cursor()
        
        # Check if person exists
        check_query = "SELECT * FROM phonebook WHERE LOWER(name) = %s"
        cursor.execute(check_query, (name.strip().lower(),))
        row = cursor.fetchone()
        
        if row is None:
            cursor.close()
            connection.close()
            return f'Person with name {name.strip().title()} does not exist, no need to delete.'
        
        # Delete person
        delete_query = "DELETE FROM phonebook WHERE id = %s"
        cursor.execute(delete_query, (row[0],))
        
        cursor.close()
        connection.close()
        return f'Phone record of {name.strip().title()} is deleted from the phonebook successfully'
    except Exception as e:
        logger.error(f"Error in delete_person: {e}")
        return 'Failed to delete person from database'

def validate_input(name, phone_number=None):
    """Validate input data"""
    if not name or not name.strip():
        return False, "Name cannot be empty"
    
    if name.strip().isdigit():
        return False, "Name should be text, not numbers"
    
    if phone_number is not None:
        if not phone_number or not phone_number.strip():
            return False, "Phone number cannot be empty"
        if not phone_number.strip().isdigit():
            return False, "Phone number should contain only digits"
        if len(phone_number.strip()) < 10:
            return False, "Phone number should be at least 10 digits"
    
    return True, "Valid input"

@app.route('/', methods=['GET', 'POST'])
def find_records():
    """Find records by keyword"""
    if request.method == 'POST':
        keyword = request.form.get('username', '').strip()
        if not keyword:
            flash('Please enter a search term', 'error')
            return render_template('index.html', show_result=False, developer_name='Ismail')
        
        persons_app = find_persons(keyword)
        return render_template('index.html', persons_html=persons_app, keyword=keyword, show_result=True, developer_name='Ismail')
    else:
        return render_template('index.html', show_result=False, developer_name='Ismail')

@app.route('/add', methods=['GET', 'POST'])
def add_record():
    """Add new record"""
    if request.method == 'POST':
        name = request.form.get('username', '').strip()
        phone_number = request.form.get('phonenumber', '').strip()
        
        # Validate input
        is_valid, message = validate_input(name, phone_number)
        if not is_valid:
            return render_template('add-update.html', 
                                not_valid=True, 
                                message=message, 
                                show_result=False, 
                                action_name='save', 
                                developer_name='Ismail')
        
        result_app = insert_person(name, phone_number)
        return render_template('add-update.html', 
                            show_result=True, 
                            result_html=result_app, 
                            not_valid=False, 
                            action_name='save', 
                            developer_name='Ismail')
    else:
        return render_template('add-update.html', 
                            show_result=False, 
                            not_valid=False, 
                            action_name='save', 
                            developer_name='Ismail')

@app.route('/update', methods=['GET', 'POST'])
def update_record():
    """Update existing record"""
    if request.method == 'POST':
        name = request.form.get('username', '').strip()
        phone_number = request.form.get('phonenumber', '').strip()
        
        # Validate input
        is_valid, message = validate_input(name, phone_number)
        if not is_valid:
            return render_template('add-update.html', 
                                not_valid=True, 
                                message=message, 
                                show_result=False, 
                                action_name='update', 
                                developer_name='Ismail')
        
        result_app = update_person(name, phone_number)
        return render_template('add-update.html', 
                            show_result=True, 
                            result_html=result_app, 
                            not_valid=False, 
                            action_name='update', 
                            developer_name='Ismail')
    else:
        return render_template('add-update.html', 
                            show_result=False, 
                            not_valid=False, 
                            action_name='update', 
                            developer_name='Ismail')

@app.route('/delete', methods=['GET', 'POST'])
def delete_record():
    """Delete record"""
    if request.method == 'POST':
        name = request.form.get('username', '').strip()
        
        # Validate input
        is_valid, message = validate_input(name)
        if not is_valid:
            return render_template('delete.html', 
                                not_valid=True, 
                                message=message, 
                                show_result=False, 
                                developer_name='Ismail')
        
        result_app = delete_person(name)
        return render_template('delete.html', 
                            show_result=True, 
                            result_html=result_app, 
                            not_valid=False, 
                            developer_name='Ismail')
    else:
        return render_template('delete.html', 
                            show_result=False, 
                            not_valid=False, 
                            developer_name='Ismail')

@app.errorhandler(404)
def not_found(error):
    return render_template('index.html', show_result=False, developer_name='Ismail'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('index.html', show_result=False, developer_name='Ismail'), 500

if __name__ == '__main__':
    # Initialize database
    if init_phonebook_db():
        logger.info("Database initialized successfully")
    else:
        logger.error("Failed to initialize database")
    
    # Run application
    app.run(host='0.0.0.0', port=80, debug=False) 