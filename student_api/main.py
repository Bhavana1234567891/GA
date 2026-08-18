from fastapi import FastAPI, Query, Header, Cookie
from typing import Optional

app = FastAPI()


students = {
    1: {"name": "Bhavana", "branch": "CSE", "age": 21},
    2: {"name": "Rahul", "branch": "ECE", "age": 22},
    3: {"name": "Anjali", "branch": "ISE", "age": 20},
    4: {"name": "Anjali Rao", "branch": "ISE", "age": 20},
}


@app.get("/students/{student_id}")
def get_student(
    student_id: int,
    username: str = Header(None)
):
    if username != "Chrome":
        return {"message": "Access Denied"}

    return students.get(student_id, {"message": "Student not found"})
#curl -H "username: Chrome" http://127.0.0.1:8000/students/1    in command prompt

#uvicorn main:app --reload   get url

#Query Parameter
@app.get("/search")
def search_student(branch: str = Query(...)):
    result = []

    for student in students.values():
        if student["branch"] == branch:
            result.append(student)

    return result

# http://127.0.0.1:8000/search?branch=CSE   url
# GET /search?branch=CSE   request

#Multiple Query Parameters

@app.get("/filter")
def filter_students(
    branch: Optional[str] = None,
    age: Optional[int] = None
):
    result = []

    for student in students.values():

        if branch and student["branch"] != branch:
            continue

        if age and student["age"] != age:
            continue

        result.append(student)

    return result

#GET /filter?branch=CSE&age=21

@app.get("/profile")
def profile(
    username: str = Header(None)
):
    if username != "Chrome":
        return {"message": "Access Denied"}

    return {"message": "Welcome Student"}














