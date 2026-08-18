import streamlit as st

st.title("Chai Taste Poll")

col1, col2= st.columns(2)

with col1:
    st.header("Masala Chai")
    #st.image("https://t3.ftcdn.net/jpg/10/00/57/10/360_F_1000571096_8ZmPCpNg5FJraw8aaIOW0ZVMO3CuNOy4")
    vote1= st.button("Vote Masala Chai")

with col2:
    st.header("Adrak Chai")
    #st.image("https://t3.ftcdn.net/jpg/10/00/57/10/360_F_1000571096_8ZmPCpNg5FJraw8aaIOW0ZVMO3CuNOy4")
    vote2=st.button("Vote Adrak Chai")

if vote1:
    st.success("thanks for voteing masala chai !")    
elif vote2:
    st.success("thanks for voteing adrak chai !") 

name=st.sidebar.text_input("Enter your name")
tea=st.sidebar.selectbox("Choose your chai",["masala","kesar","adrak"])

with st.expander("Show chai boiling instructions"):
    st.write("""
    1.
    2.
    3.
""")
    
st.markdown('### Welcome to Chai App')
st.markdown('> Bolckquote')





