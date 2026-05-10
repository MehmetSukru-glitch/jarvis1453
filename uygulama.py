import subprocess
import threading
import time
from app import app

def flask_baslat():
    app.run(port=5000)

if __name__ == "__main__":
    t = threading.Thread(target=flask_baslat, daemon=True)
    t.start()
    time.sleep(1.5)
    subprocess.Popen([
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "--app=http://127.0.0.1:5000",
        "--window-size=1200,750"
    ])
    input()