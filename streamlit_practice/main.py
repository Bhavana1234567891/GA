# python -m streamlit run app.py


import streamlit as st

st.title("🎓 Student Registration")

# -------------------------------
# Initialize session state
# -------------------------------
if "students" not in st.session_state:
    st.session_state.students = []

# -------------------------------
# User Inputs
# -------------------------------
name = st.text_input("Student Name")

course = st.selectbox(
    "Course",
    ["Python", "AI", "Java"]
)

# -------------------------------
# Add Student Button
# -------------------------------
if st.button("Add Student"):

    if name.strip() == "":
        st.warning("Please enter a student name.")

    else:
        st.session_state.students.append(
            {
                "Name": name,
                "Course": course
            }
        )

        st.success(f"{name} added successfully!")

# -------------------------------
# Display Students
# -------------------------------
st.subheader("Registered Students")

if len(st.session_state.students) == 0:
    st.write("No students registered yet.")

else:
    for i, student in enumerate(st.session_state.students, start=1):
        st.write(
            f"{i}. {student['Name']} - {student['Course']}"
        )

# -------------------------------
# Clear List Button
# -------------------------------
if st.button("Clear All Students"):
    st.session_state.students = []
    st.success("Student list cleared.")