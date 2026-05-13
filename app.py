from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import requests
import datetime
import os
import json
import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash, check_password_hash
from groq import Groq

app = Flask(__name__)
app.secret_key = "jarvis_gizli_anahtar_2024"
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=3650)

API_KEY = os.environ.get("API_KEY", "5ab012c8fd1875d8330b951e11556c56")
SEHIR = os.environ.get("SEHIR", "Istanbul")
GROQ_KEY = os.environ.get("GROQ_API_KEY", "buraya_groq_keyin")
DATABASE_URL = os.environ.get("DATABASE_URL")

groq_client = Groq(api_key=GROQ_KEY)

def db_baglan():
    return psycopg2.connect(DATABASE_URL)

def db_kur():
    conn = db_baglan()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kullanicilar (
            id SERIAL PRIMARY KEY,
            kullanici_adi VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(200) UNIQUE NOT NULL,
            sifre TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sohbetler (
            id VARCHAR(50) PRIMARY KEY,
            isim VARCHAR(200) NOT NULL,
            mesajlar TEXT NOT NULL,
            kullanici VARCHAR(100) NOT NULL
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

db_kur()

def jarvis_ai(mesajlar, soru):
    mesajlar.append({"role": "user", "content": soru})
    cevap = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Sen J.A.R.V.I.S. 1453 adında bir yapay zeka asistansın. Seni Mehmet Şükrü Sevinç geliştirdi. Türkçe konuşuyorsun. Net ve efendice cevap veriyorsun. Kullanıcına 'efendim' diye hitap ediyorsun."}
        ] + mesajlar,
        max_tokens=500
    )
    cevap_metni = cevap.choices[0].message.content
    mesajlar.append({"role": "assistant", "content": cevap_metni})
    return cevap_metni, mesajlar

def komutu_isle(komut, mesajlar):
    if "saat" in komut:
        zaman = datetime.datetime.now()
        saat = zaman.hour
        dakika = zaman.minute
        if dakika == 0:
            return f"Şu an saat tam {saat}.", mesajlar
        else:
            return f"Şu an saat {saat} {dakika}.", mesajlar
    elif "hava" in komut:
        sehir_bul = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": f"Bu cümlede hangi şehirden bahsediliyor? Sadece şehir adını İngilizce yaz. Şehir yoksa Istanbul yaz. Cümle: {komut}"}],
            max_tokens=20
        )
        sehir = sehir_bul.choices[0].message.content.strip()
        url = f"http://api.openweathermap.org/data/2.5/weather?q={sehir}&appid={API_KEY}&units=metric&lang=tr"
        veri = requests.get(url).json()
        sicaklik = round(veri["main"]["temp"])
        hissedilen = round(veri["main"]["feels_like"])
        nem = veri["main"]["humidity"]
        durum = veri["weather"][0]["description"]
        if sicaklik >= 30:
            yorum = "Oldukça sıcak bir hava efendim."
        elif sicaklik >= 20:
            yorum = "Güzel ve ılıman bir hava efendim."
        elif sicaklik >= 10:
            yorum = "Serin bir hava efendim."
        else:
            yorum = "Oldukça soğuk bir hava efendim."
        return f"{sehir}'da şu an hava {durum}. Sıcaklık {sicaklik} derece, hissedilen {hissedilen} derece. Nem yüzde {nem}. {yorum}", mesajlar
    else:
        cevap, mesajlar = jarvis_ai(mesajlar, komut)
        return cevap, mesajlar

@app.route("/")
def index():
    if "kullanici" not in session:
        return redirect(url_for("giris"))
    return render_template("index.html", kullanici=session["kullanici"])

@app.route("/giris", methods=["GET", "POST"])
def giris():
    if request.method == "POST":
        veri = request.json
        giris_bilgisi = veri.get("kullanici_adi")
        sifre = veri.get("sifre")
        conn = db_baglan()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM kullanicilar WHERE kullanici_adi=%s OR email=%s", (giris_bilgisi, giris_bilgisi))
        kullanici = cur.fetchone()
        cur.close()
        conn.close()
        if kullanici and check_password_hash(kullanici["sifre"], sifre):
            session.permanent = True
            session["kullanici"] = kullanici["kullanici_adi"]
            return jsonify({"ok": True})
        return jsonify({"ok": False, "mesaj": "Kullanıcı adı/email veya şifre hatalı!"})
    return render_template("giris.html")

@app.route("/kayit", methods=["POST"])
def kayit():
    veri = request.json
    kullanici_adi = veri.get("kullanici_adi")
    email = veri.get("email")
    sifre = veri.get("sifre")
    conn = db_baglan()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO kullanicilar (kullanici_adi, email, sifre) VALUES (%s, %s, %s)",
                    (kullanici_adi, email, generate_password_hash(sifre)))
        conn.commit()
        session.permanent = True
        session["kullanici"] = kullanici_adi
        cur.close()
        conn.close()
        return jsonify({"ok": True})
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"ok": False, "mesaj": "Bu kullanıcı adı veya email zaten kayıtlı!"})

@app.route("/cikis")
def cikis():
    session.pop("kullanici", None)
    return redirect(url_for("giris"))

@app.route("/sohbetler", methods=["GET"])
def sohbetleri_getir():
    if "kullanici" not in session:
        return jsonify({})
    conn = db_baglan()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM sohbetler WHERE kullanici=%s", (session["kullanici"],))
    satirlar = cur.fetchall()
    cur.close()
    conn.close()
    sohbetler = {}
    for s in satirlar:
        sohbetler[s["id"]] = {
            "isim": s["isim"],
            "mesajlar": json.loads(s["mesajlar"]),
            "kullanici": s["kullanici"]
        }
    return jsonify(sohbetler)

@app.route("/yeni_sohbet", methods=["POST"])
def yeni_sohbet():
    if "kullanici" not in session:
        return jsonify({"hata": "Giriş yapılmamış"})
    veri = request.json
    sohbet_id = str(datetime.datetime.now().timestamp())
    conn = db_baglan()
    cur = conn.cursor()
    cur.execute("INSERT INTO sohbetler (id, isim, mesajlar, kullanici) VALUES (%s, %s, %s, %s)",
                (sohbet_id, veri.get("isim", "Yeni Sohbet"), "[]", session["kullanici"]))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"id": sohbet_id})

@app.route("/sohbet_isim", methods=["POST"])
def sohbet_isim_degistir():
    veri = request.json
    conn = db_baglan()
    cur = conn.cursor()
    cur.execute("UPDATE sohbetler SET isim=%s WHERE id=%s", (veri.get("isim"), veri.get("id")))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})

@app.route("/sohbet_sil", methods=["POST"])
def sohbet_sil():
    veri = request.json
    conn = db_baglan()
    cur = conn.cursor()
    cur.execute("DELETE FROM sohbetler WHERE id=%s", (veri.get("id"),))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})

@app.route("/komut", methods=["POST"])
def komut():
    if "kullanici" not in session:
        return jsonify({"hata": "Giriş yapılmamış"})
    veri = request.json
    komut_metni = veri.get("komut", "").lower().strip()
    sohbet_id = veri.get("sohbet_id")
    conn = db_baglan()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM sohbetler WHERE id=%s", (sohbet_id,))
    sohbet = cur.fetchone()
    if not sohbet:
        cur.close()
        conn.close()
        return jsonify({"hata": "Sohbet bulunamadı"})
    mesajlar = json.loads(sohbet["mesajlar"])
    cevap, mesajlar = komutu_isle(komut_metni, mesajlar)
    cur2 = conn.cursor()
    cur2.execute("UPDATE sohbetler SET mesajlar=%s WHERE id=%s", (json.dumps(mesajlar, ensure_ascii=False), sohbet_id))
    conn.commit()
    cur.close()
    cur2.close()
    conn.close()
    return jsonify({"cevap": cevap})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)