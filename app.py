from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import requests
import datetime
import os
import json
from werkzeug.security import generate_password_hash, check_password_hash
from groq import Groq

app = Flask(__name__)
app.secret_key = "jarvis_gizli_anahtar_2024"

API_KEY = os.environ.get("API_KEY", "5ab012c8fd1875d8330b951e11556c56")
SEHIR = os.environ.get("SEHIR", "Istanbul")
GROQ_KEY = os.environ.get("GROQ_API_KEY", "gsk_keyin")

groq_client = Groq(api_key=GROQ_KEY)

KULLANICILAR_DOSYA = "kullanicilar.json"
SOHBETLER_DOSYA = "sohbetler.json"

def kullanicilari_yukle():
    if os.path.exists(KULLANICILAR_DOSYA):
        with open(KULLANICILAR_DOSYA, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def kullanicilari_kaydet(kullanicilar):
    with open(KULLANICILAR_DOSYA, "w", encoding="utf-8") as f:
        json.dump(kullanicilar, f, ensure_ascii=False, indent=2)

def sohbetleri_yukle():
    if os.path.exists(SOHBETLER_DOSYA):
        with open(SOHBETLER_DOSYA, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def sohbetleri_kaydet(sohbetler):
    with open(SOHBETLER_DOSYA, "w", encoding="utf-8") as f:
        json.dump(sohbetler, f, ensure_ascii=False, indent=2)

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
    elif "google" in komut:
        os.startfile("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe")
        return "Google açılıyor efendim.", mesajlar
    elif "youtube" in komut:
        os.system('start "" "C:\\Program Files\\Google\\Chrome\\Application\\chrome_proxy.exe" --profile-directory="Profile 1" --app-id=agimnkijcaahngcdmfeangaknmldooml')
        return "YouTube açılıyor efendim.", mesajlar
    elif "spotify" in komut:
        os.startfile("C:\\Users\\mehme\\AppData\\Local\\Microsoft\\WindowsApps\\Spotify.exe")
        return "Spotify açılıyor efendim.", mesajlar
    elif "valorant" in komut:
        os.system('start "" "C:\\Riot Games\\Riot Client\\RiotClientServices.exe" --launch-product=valorant --launch-patchline=live')
        return "Valorant açılıyor efendim.", mesajlar
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
        kullanici_adi = veri.get("kullanici_adi")
        sifre = veri.get("sifre")
        kullanicilar = kullanicilari_yukle()
        if kullanici_adi in kullanicilar and check_password_hash(kullanicilar[kullanici_adi]["sifre"], sifre):
            session["kullanici"] = kullanici_adi
            return jsonify({"ok": True})
        return jsonify({"ok": False, "mesaj": "Kullanıcı adı veya şifre hatalı!"})
    return render_template("giris.html")

@app.route("/kayit", methods=["POST"])
def kayit():
    veri = request.json
    kullanici_adi = veri.get("kullanici_adi")
    email = veri.get("email")
    sifre = veri.get("sifre")
    kullanicilar = kullanicilari_yukle()
    for k, v in kullanicilar.items():
        if v.get("email") == email:
            return jsonify({"ok": False, "mesaj": "Bu email zaten kayıtlı!"})
    if kullanici_adi in kullanicilar:
        return jsonify({"ok": False, "mesaj": "Bu kullanıcı adı zaten alınmış!"})
    kullanicilar[kullanici_adi] = {
        "sifre": generate_password_hash(sifre),
        "email": email
    }
    kullanicilari_kaydet(kullanicilar)
    session.permanent = True
    session["kullanici"] = kullanici_adi
    return jsonify({"ok": True})
@app.route("/sohbetler", methods=["GET"])
def sohbetleri_getir():
    if "kullanici" not in session:
        return jsonify({})
    kullanici = session["kullanici"]
    sohbetler = sohbetleri_yukle()
    kullanici_sohbetleri = {k: v for k, v in sohbetler.items() if v.get("kullanici") == kullanici}
    return jsonify(kullanici_sohbetleri)

@app.route("/yeni_sohbet", methods=["POST"])
def yeni_sohbet():
    if "kullanici" not in session:
        return jsonify({"hata": "Giriş yapılmamış"})
    sohbetler = sohbetleri_yukle()
    veri = request.json
    sohbet_id = str(datetime.datetime.now().timestamp())
    sohbetler[sohbet_id] = {
        "isim": veri.get("isim", "Yeni Sohbet"),
        "mesajlar": [],
        "kullanici": session["kullanici"]
    }
    sohbetleri_kaydet(sohbetler)
    return jsonify({"id": sohbet_id})

@app.route("/sohbet_isim", methods=["POST"])
def sohbet_isim_degistir():
    sohbetler = sohbetleri_yukle()
    veri = request.json
    sohbet_id = veri.get("id")
    yeni_isim = veri.get("isim")
    if sohbet_id in sohbetler:
        sohbetler[sohbet_id]["isim"] = yeni_isim
        sohbetleri_kaydet(sohbetler)
    return jsonify({"ok": True})

@app.route("/sohbet_sil", methods=["POST"])
def sohbet_sil():
    sohbetler = sohbetleri_yukle()
    veri = request.json
    sohbet_id = veri.get("id")
    if sohbet_id in sohbetler:
        del sohbetler[sohbet_id]
        sohbetleri_kaydet(sohbetler)
    return jsonify({"ok": True})

@app.route("/komut", methods=["POST"])
def komut():
    if "kullanici" not in session:
        return jsonify({"hata": "Giriş yapılmamış"})
    sohbetler = sohbetleri_yukle()
    veri = request.json
    komut_metni = veri.get("komut", "").lower().strip()
    sohbet_id = veri.get("sohbet_id")
    if sohbet_id not in sohbetler:
        return jsonify({"hata": "Sohbet bulunamadı"})
    mesajlar = sohbetler[sohbet_id]["mesajlar"]
    cevap, mesajlar = komutu_isle(komut_metni, mesajlar)
    sohbetler[sohbet_id]["mesajlar"] = mesajlar
    sohbetleri_kaydet(sohbetler)
    return jsonify({"cevap": cevap})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
    app.run(debug=True)