const API = "http://127.0.0.1:5000/students";

// Load all students
async function loadStudents() {

    const response = await fetch(API);
    const students = await response.json();

    const table = document.getElementById("studentTable");
    table.innerHTML = "";

    students.forEach(student => {

        table.innerHTML += `
        <tr>
            <td>${student.id}</td>
            <td>${student.name}</td>
            <td>${student.age}</td>
            <td>${student.email}</td>
            <td>${student.course}</td>

            <td>
                <button class="edit"
                    onclick="editStudent(
                        ${student.id},
                        '${student.name}',
                        ${student.age},
                        '${student.email}',
                        '${student.course}'
                    )">
                    Edit
                </button>
            </td>

            <td>
                <button class="delete"
                    onclick="deleteStudent(${student.id})">
                    Delete
                </button>
            </td>
        </tr>
        `;
    });
}


// Save Student (POST) OR Update Student (PUT)

async function saveStudent() {

    const id = document.getElementById("studentId").value;

    const name = document.getElementById("name").value;
    const age = document.getElementById("age").value;
    const email = document.getElementById("email").value;
    const course = document.getElementById("course").value;

    const student = {
        name,
        age,
        email,
        course
    };

    if (id == "") {

        // POST
        await fetch(API, {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify(student)

        });

    } else {

        // PUT
        await fetch(API + "/" + id, {

            method: "PUT",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify(student)

        });

    }

    clearForm();

    loadStudents();

}


// Fill Form For Editing

function editStudent(id, name, age, email, course) {

    document.getElementById("studentId").value = id;

    document.getElementById("name").value = name;

    document.getElementById("age").value = age;

    document.getElementById("email").value = email;

    document.getElementById("course").value = course;

}


// Delete Student

async function deleteStudent(id) {

    const confirmDelete = confirm("Delete this student?");

    if (!confirmDelete)
        return;

    await fetch(API + "/" + id, {

        method: "DELETE"

    });

    loadStudents();

}


// Clear Form

function clearForm() {

    document.getElementById("studentId").value = "";

    document.getElementById("name").value = "";

    document.getElementById("age").value = "";

    document.getElementById("email").value = "";

    document.getElementById("course").value = "";

}


window.onload = loadStudents;