from flask import Flask, jsonify, request, render_template
from database import (
    create_table,
    get_all_students,
    add_student,
    update_student,
    delete_student
)

app = Flask(__name__)

create_table()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/students", methods=["GET"])
def get_students():

    students = get_all_students()

    student_list = []

    for student in students:
        student_data = {
            "id": student[0],
            "name": student[1],
            "age": student[2],
            "email": student[3],
            "course": student[4]
        }

        student_list.append(student_data)

    return jsonify(student_list)

@app.route("/students", methods=["POST"])
def create_student():

    data = request.get_json()

    name = data["name"]
    age = data["age"]
    email = data["email"]
    course = data["course"]

    add_student(name, age, email, course)

    return jsonify({
        "message": "Student added successfully"
    }), 201

@app.route("/students/<int:student_id>", methods=["PUT"])
def edit_student(student_id):

    data = request.get_json()

    name = data["name"]
    age = data["age"]
    email = data["email"]
    course = data["course"]

    update_student(
        student_id,
        name,
        age,
        email,
        course
    )

    return jsonify({
        "message": "Student updated successfully"
    })

@app.route("/students/<int:student_id>", methods=["DELETE"])
def remove_student(student_id):

    delete_student(student_id)

    return jsonify({
        "message": "Student deleted successfully"
    })

if __name__ == "__main__":
    app.run(debug=True)