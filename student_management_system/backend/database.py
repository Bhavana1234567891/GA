import sqlite3

DATABASE_NAME = "students.db"


def get_connection():
    """
    Creates and returns a connection to the SQLite database.
    """
    return sqlite3.connect(DATABASE_NAME)

def create_table():
    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER,
        email TEXT,
        course TEXT
    )
    """)

    conn.commit()
    conn.close()

def add_student(name, age, email, course):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO students(name, age, email, course)
    VALUES (?, ?, ?, ?)
    """, (name, age, email, course))

    conn.commit()

    conn.close()

def update_student(student_id, name, age, email, course):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        UPDATE students
        SET
            name = ?,
            age = ?,
            email = ?,
            course = ?
        WHERE id = ?
    """, (name, age, email, course, student_id))

    conn.commit()

    conn.close()

def delete_student(student_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM students
        WHERE id = ?
    """, (student_id,))

    conn.commit()

    conn.close()

def get_all_students():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students")

    students = cursor.fetchall()

    conn.close()

    return students

if __name__ == "__main__":
    create_table()
    add_student("Bhavana",18,"bmk@gmail.com","India")
    print("Students table created successfully!")