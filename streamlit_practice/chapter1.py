import streamlit as st

st.title("Hello Bhavana")

st.subheader("Exploring streamlit")

st.text("Welcome to your first web interactive app")

st.write("choose your fav. cake")

cake= st.selectbox("you fav flavour: ",["Mango","Chocklete","Pineapple","Cheese","Honey"])

st.write(f"You choose {cake}. Excellent choice")

st.success("Your cake has been brewed")

