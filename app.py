from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import sqlite3
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['DATABASE'] = os.path.join(app.instance_path, 'discipline.db')

# Ensure instance folder exists
os.makedirs(app.instance_path, exist_ok=True)


# Database helper functions
def get_db():
    """Connect to the SQLite database"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn


def init_db():
    """Initialize the database with tables"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Habits table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            current_streak INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Tracking table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL,
            date DATE NOT NULL,
            completed BOOLEAN NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (habit_id) REFERENCES habits (id),
            UNIQUE(habit_id, date)
        )
    ''')
    
    conn.commit()
    conn.close()


# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# AI Insights Engine
class DisciplineAI:
    """AI system to analyze habits and provide personalized insights"""
    
    @staticmethod
    def get_completion_rate(habit_id, days=7):
        """Calculate completion rate for last N days"""
        conn = get_db()
        cursor = conn.cursor()
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        cursor.execute('''
            SELECT COUNT(*) as total,
            SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed
            FROM tracking
            WHERE habit_id = ? AND date BETWEEN ? AND ?
        ''', (habit_id, start_date, end_date))
        
        result = cursor.fetchone()
        conn.close()
        
        total = result['total'] if result['total'] > 0 else 1
        completed = result['completed'] if result['completed'] else 0
        
        return (completed / total) * 100 if total > 0 else 0
    
    @staticmethod
    def detect_patterns(habit_id):
        """Detect behavioral patterns in habit completion"""
        conn = get_db()
        cursor = conn.cursor()
        
        # Get last 14 days of data
        cursor.execute('''
            SELECT date, completed
            FROM tracking
            WHERE habit_id = ?
            ORDER BY date DESC
            LIMIT 14
        ''', (habit_id,))
        
        records = cursor.fetchall()
        conn.close()
        
        if not records:
            return []
        
        patterns = []
        
        # Check weekend pattern
        weekend_misses = 0
        weekend_total = 0
        weekday_completion = 0
        weekday_total = 0
        
        for record in records:
            date = datetime.strptime(record['date'], '%Y-%m-%d')
            is_weekend = date.weekday() >= 5
            
            if is_weekend:
                weekend_total += 1
                if not record['completed']:
                    weekend_misses += 1
            else:
                weekday_total += 1
                if record['completed']:
                    weekday_completion += 1
        
        # Weekend slacking pattern
        if weekend_total > 0 and (weekend_misses / weekend_total) > 0.6:
            patterns.append({
                'type': 'weekend_slacker',
                'severity': 'high',
                'message': 'You skip this habit on weekends. Discipline doesn\'t take breaks!'
            })
        
        # Inconsistency pattern
        completion_rate = DisciplineAI.get_completion_rate(habit_id, 7)
        if 30 <= completion_rate < 60:
            patterns.append({
                'type': 'inconsistent',
                'severity': 'medium',
                'message': 'You\'re inconsistent. Success demands daily commitment, not occasional effort.'
            })
        elif completion_rate < 30:
            patterns.append({
                'type': 'failing',
                'severity': 'critical',
                'message': 'You\'re failing this habit. Either commit fully or remove it. No excuses.'
            })
        
        # Check for recent decline
        if len(records) >= 7:
            recent_completion = sum(1 for r in records[:3] if r['completed']) / 3
            older_completion = sum(1 for r in records[3:7] if r['completed']) / 4
            
            if recent_completion < older_completion - 0.3:
                patterns.append({
                    'type': 'declining',
                    'severity': 'high',
                    'message': 'Your performance is declining. Get back on track NOW.'
                })
        
        return patterns
    
    @staticmethod
    def generate_insights(user_id):
        """Generate personalized AI insights for all user habits"""
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM habits WHERE user_id = ?', (user_id,))
        habits = cursor.fetchall()
        conn.close()
        
        insights = []
        
        for habit in habits:
            habit_insights = DisciplineAI.detect_patterns(habit['id'])
            completion_rate = DisciplineAI.get_completion_rate(habit['id'], 7)
            
            # Add positive reinforcement for high performers
            if completion_rate >= 90:
                insights.append({
                    'habit_name': habit['name'],
                    'type': 'excellence',
                    'severity': 'positive',
                    'message': f'Outstanding! {completion_rate:.0f}% completion. Keep this momentum!'
                })
            
            # Add pattern-based insights
            for pattern in habit_insights:
                insights.append({
                    'habit_name': habit['name'],
                    **pattern
                })
        
        return insights


# Routes
@app.route('/')
def index():
    """Home page"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not username or not email or not password:
            flash('All fields are required!', 'danger')
            return redirect(url_for('signup'))
        
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            hashed_password = generate_password_hash(password)
            cursor.execute(
                'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                (username, email, hashed_password)
            )
            conn.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists!', 'danger')
        finally:
            conn.close()
    
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'danger')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard showing all habits and stats"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get all user habits
    cursor.execute('SELECT * FROM habits WHERE user_id = ? ORDER BY created_at DESC', 
                   (session['user_id'],))
    habits = cursor.fetchall()
    
    # Get today's tracking status for each habit
    today = datetime.now().date()
    habit_data = []
    
    for habit in habits:
        cursor.execute('''
            SELECT completed FROM tracking 
            WHERE habit_id = ? AND date = ?
        ''', (habit['id'], today))
        
        tracking = cursor.fetchone()
        completion_rate = DisciplineAI.get_completion_rate(habit['id'], 7)
        
        habit_data.append({
            'id': habit['id'],
            'name': habit['name'],
            'description': habit['description'],
            'category': habit['category'],
            'current_streak': habit['current_streak'],
            'best_streak': habit['best_streak'],
            'completion_rate': completion_rate,
            'completed_today': tracking['completed'] if tracking else False
        })
    
    # Get AI insights
    insights = DisciplineAI.generate_insights(session['user_id'])
    
    conn.close()
    
    return render_template('dashboard.html',  habits=habit_data,insights=insights, today=today)


@app.route('/habits/add', methods=['GET', 'POST'])
@login_required
def add_habit():
    """Add a new habit"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        category = request.form.get('category')
        
        if not name:
            flash('Habit name is required!', 'danger')
            return redirect(url_for('add_habit'))
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO habits (user_id, name, description, category) VALUES (?, ?, ?, ?)',
            (session['user_id'], name, description, category)
        )
        conn.commit()
        conn.close()
        
        flash(f'Habit "{name}" added successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('add_habit.html')


@app.route('/habits/<int:habit_id>/track', methods=['POST'])
@login_required
def track_habit(habit_id):
    """Mark habit as completed or missed for today"""
    completed = request.form.get('completed') == '1'
    today = datetime.now().date()
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Verify habit belongs to user
    cursor.execute('SELECT * FROM habits WHERE id = ? AND user_id = ?', (habit_id, session['user_id']))
    habit = cursor.fetchone()
    
    if not habit:
        flash('Habit not found!', 'danger')
        conn.close()
        return redirect(url_for('dashboard'))
    
    # Insert or update tracking
    try:
        cursor.execute('''
            INSERT INTO tracking (habit_id, date, completed)
            VALUES (?, ?, ?)
            ON CONFLICT(habit_id, date) DO UPDATE SET completed = ?
        ''', (habit_id, today, completed, completed))
        
        # Update streak
        if completed:
            # Check if yesterday was completed
            yesterday = today - timedelta(days=1)
            cursor.execute('''
                SELECT completed FROM tracking 
                WHERE habit_id = ? AND date = ?
            ''', (habit_id, yesterday))
            
            yesterday_record = cursor.fetchone()
            
            if yesterday_record and yesterday_record['completed']:
                # Continue streak
                new_streak = habit['current_streak'] + 1
            else:
                # Start new streak
                new_streak = 1
            
            # Update best streak if needed
            best_streak = max(habit['best_streak'], new_streak)
            
            cursor.execute('''
                UPDATE habits 
                SET current_streak = ?, best_streak = ?
                WHERE id = ?
            ''', (new_streak, best_streak, habit_id))
        else:
            # Reset streak on miss
            cursor.execute('''
                UPDATE habits SET current_streak = 0 WHERE id = ?
            ''', (habit_id,))
        
        conn.commit()
        flash(f'Habit {"completed" if completed else "marked as missed"}!', 'success')
    except Exception as e:
        flash(f'Error tracking habit: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('dashboard'))


@app.route('/habits/<int:habit_id>/delete', methods=['POST'])
@login_required
def delete_habit(habit_id):
    """Delete a habit and all its tracking data"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Verify habit belongs to user
    cursor.execute('SELECT * FROM habits WHERE id = ? AND user_id = ?', (habit_id, session['user_id']))
    habit = cursor.fetchone()
    
    if not habit:
        flash('Habit not found!', 'danger')
        conn.close()
        return redirect(url_for('dashboard'))
    
    # Delete tracking records first (foreign key constraint)
    cursor.execute('DELETE FROM tracking WHERE habit_id = ?', (habit_id,))
    cursor.execute('DELETE FROM habits WHERE id = ?', (habit_id,))
    
    conn.commit()
    conn.close()
    
    flash(f'Habit "{habit["name"]}" deleted!', 'info')
    return redirect(url_for('dashboard'))


@app.route('/insights')
@login_required
def insights():
    """View detailed AI insights and analytics"""
    ai_insights = DisciplineAI.generate_insights(session['user_id'])
    return render_template('insights.html', insights=ai_insights)


@app.route('/habits/<int:habit_id>/history')
@login_required
def habit_history(habit_id):
    """View detailed history for a specific habit"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get habit details
    cursor.execute('SELECT * FROM habits WHERE id = ? AND user_id = ?', 
                   (habit_id, session['user_id']))
    habit = cursor.fetchone()
    
    if not habit:
        flash('Habit not found!', 'danger')
        conn.close()
        return redirect(url_for('dashboard'))
    
    # Get tracking history (last 30 days)
    cursor.execute('''
        SELECT date, completed, notes
        FROM tracking
        WHERE habit_id = ?
        ORDER BY date DESC
        LIMIT 30
    ''', (habit_id,))
    
    history = cursor.fetchall()
    conn.close()
    
    return render_template('habit_history.html', habit=habit, history=history)


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)