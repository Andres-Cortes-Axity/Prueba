import subprocess


def lanzar_streamlit():
    subprocess.run(["streamlit", "run", "frontend/app.py"])
