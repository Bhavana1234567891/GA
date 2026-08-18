# python -m uvicorn main:app --reload


from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="ToDo API")

# -----------------------------
# Data Model
# -----------------------------

class Todo(BaseModel):
    title: str
    completed: bool = False

# -----------------------------
# Temporary Database
# -----------------------------

todos = {}

# -----------------------------
# Home Endpoint
# -----------------------------

@app.get("/")
def home():
    return {
        "message": "Welcome to Todo API"
    }

# -----------------------------
# Get All Todos
# -----------------------------

@app.get("/todos")
def get_todos():
    return todos

# -----------------------------
# Get One Todo
# -----------------------------

@app.get("/todos/{todo_id}")
def get_todo(todo_id: int):

    if todo_id not in todos:
        raise HTTPException(
            status_code=404,
            detail="Todo not found"
        )

    return todos[todo_id]

# -----------------------------
# Create Todo
# -----------------------------

@app.post("/todos", status_code=201)
def create_todo(todo: Todo):

    todo_id = len(todos) + 1

    todos[todo_id] = todo

    return {
        "id": todo_id,
        "message": "Todo created successfully",
        "todo": todo
    }

# -----------------------------
# Update Todo
# -----------------------------

@app.put("/todos/{todo_id}")
def update_todo(todo_id: int, todo: Todo):

    if todo_id not in todos:
        raise HTTPException(
            status_code=404,
            detail="Todo not found"
        )

    todos[todo_id] = todo

    return {
        "message": "Todo updated successfully",
        "todo": todo
    }

# -----------------------------
# Delete Todo
# -----------------------------

@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int):

    if todo_id not in todos:
        raise HTTPException(
            status_code=404,
            detail="Todo not found"
        )

    del todos[todo_id]

    return {
        "message": "Todo deleted successfully"
    }