import streamlit as st
import subprocess
import json

st.title("🛡️ OSINT-REILLY: Інтерфейс Керування")

# 1. Поле введення первинного запиту
user_query = st.text_input("Введіть об'єкт або гео-точку для дослідження:")

if user_query:
    st.subheader("🤖 Діалог уточнення завдання з REILLY")
    
    # Тут запускається легка модель, яка аналізує запит і задає 2-3 питання
    # Користувач відповідає в чаті, формуючи фінальний фокус
    
    st.info("ШІ пропонує сфокусуватися на: Економічних індексах та Логістиці.")
    
    # 2. Кнопка фінального запуску «Танка»
    if st.button("Запустити глибоке дослідження"):
        with st.spinner("Дdeployed Digital Residents. Працює Bright Data..."):
            
            # Інтерфейс викликає наш main.py у фоновому режимі
            result = subprocess.run(
                ["python3", "main.py", "--mode", "hackathon", "--target", user_query],
                capture_output=True, text=True
            )
            st.success("Аналітичний звіт сформовано!")