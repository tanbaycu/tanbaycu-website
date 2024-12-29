import os
import random
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# import google.generativeai as genai
import json
import requests
import yt_dlp
import sys
import uuid
import time
from datetime import datetime
import re
import subprocess
from deep_translator import GoogleTranslator

# from vercel_kv import VercelKV
from flask import (
    Flask,
    request,
    render_template,
    redirect,
    flash,
    url_for,
    get_flashed_messages,
    jsonify,
    send_file,
    abort,
    Response,
)

# kv = VercelKV()
app = Flask(__name__)


@app.route('/')
def homepage():
    return send_file('index.html')
# Hàm xác thực URL
def validate_url(url):
    regex = re.compile(
        r"^(http://www\.|https://www\.|http://|https://)?[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,}(:[0-9]{1,5})?(\/.*)?$"
    )
    # Trả về True nếu URL hợp lệ, ngược lại trả về False
    return re.match(regex, url) is not None


def send_request(long_url):
    if validate_url(long_url):
        choice = random.choice(["TinyURL", "isgd", "vgd"])

        if choice == "isgd":
            return shorten_url_isgd(long_url)
        elif choice == "TinyURL":
            return shorten_url_tinyurl(long_url)
        elif choice == "vgd":
            return shorten_url_vgd(long_url)
    else:
        print("Invalid URL!")
        return None


def shorten_url_isgd(long_url):
    try:
        # URL encode the long URL
        encoded_long_url = requests.utils.quote(long_url)
        # Construct the request URL for is.gd
        request_url = f"https://is.gd/create.php?format=simple&url={encoded_long_url}"

        # Send the GET request to is.gd
        response = requests.get(request_url)

        # Check for successful response
        if response.status_code == 200:
            # The response should be the shortened URL in plain text
            return response.text.strip()
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        # Handle request errors
        print(f"Error while shortening URL with is.gd: {e}")
        return None


def shorten_url_tinyurl(long_url):
    try:
        # URL encode the long URL
        encoded_long_url = requests.utils.quote(long_url, safe="")
        # Construct the request URL for TinyURL
        request_url = f"http://tinyurl.com/api-create.php?url={encoded_long_url}"

        # Send the GET request to TinyURL
        response = requests.get(request_url)
        response.raise_for_status()  # Raise an exception for 4xx/5xx errors

        # Return the shortened URL in plain text
        return response.text.strip()
    except requests.exceptions.RequestException as e:
        # Handle request errors
        print(f"Error while shortening URL with TinyURL: {e}")
        return None


def shorten_url_vgd(long_url):
    try:
        # URL encode the long URL
        encoded_long_url = requests.utils.quote(long_url, safe="")
        # Construct the request URL for v.gd
        request_url = f"https://v.gd/create.php?format=simple&url={encoded_long_url}"

        # Send the GET request to v.gd
        response = requests.get(request_url)

        # Check for successful response
        if response.status_code == 200:
            # The response should be the shortened URL in plain text
            return response.text.strip()
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        # Handle request errors
        print(f"Error while shortening URL with v.gd: {e}")
        return None


@app.route("/about-me")
def about_me():
    return render_template("about_me.html")


@app.route("/dev")
def dev():
    return render_template("dev.html")


@app.route("/shorten-link", methods=["GET", "POST"])
def shorten_link():
    if request.method == "POST":
        long_url = request.form.get("long_url").strip()
        short_url = send_request(long_url)

        if short_url:
            return render_template(
                "shorten_link.html", short_url=short_url
            )  # Truyền short_url tới template
        else:
            flash("Không thể rút gọn URL.")
            return redirect(request.url)

    return render_template("shorten_link.html")  # Trả về trang rút gọn URL

UPLOAD_FOLDER = "/tmp/uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.secret_key = "28a03d4e9561e85914da8e57f55f5bbe"
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB

PIXELDRAIN_API_KEY = "fba3e1f5-269b-4758-8e44-78326d0d7d95"
RETRY_LIMIT = 3

upload_history = []
download_history = []

def clean_filename(filename):
    # Remove any non-word (non-alphanumeric + underscore) characters
    filename = re.sub(r'[^\w\.-]', '', filename)
    # Remove any runs of periods (as they're redundant)
    filename = re.sub(r'\.+', '.', filename)
    return filename

def upload_to_gofile(file_data, filename):
    url = "https://store1.gofile.io/uploadFile"
    files = {"file": (filename, file_data)}
    try:
        response = requests.post(url, files=files, timeout=600)
        response.raise_for_status()
        response_json = response.json()
        if response_json.get("status") == "ok":
            download_link = response_json.get("data", {}).get("downloadPage")
            return {"message": "Upload successful!", "link": download_link}
        else:
            return {
                "message": f"Failed to upload file. Error: {response_json.get('message')}"
            }
    except requests.exceptions.RequestException as e:
        return {"message": f"Request error: {e}"}
    except ValueError as e:
        return {"message": f"Error decoding JSON response: {e}"}

def upload_to_pixeldrain(file_data, filename):
    url = "https://pixeldrain.com/api/file"
    headers = {
        "Authorization": "Basic " + base64.b64encode(f":{PIXELDRAIN_API_KEY}".encode()).decode()
    }
    files = {"file": (filename, file_data)}
    try:
        response = requests.post(url, files=files, headers=headers, timeout=600)
        response.raise_for_status()
        response_json = response.json()
        file_id = response_json.get("id")
        if file_id:
            download_link = f"https://pixeldrain.com/u/{file_id}"
            return {"message": "Upload successful!", "link": download_link}
        else:
            return {"message": "Failed to upload file. No file ID returned."}
    except requests.exceptions.RequestException as e:
        return {"message": f"Request error: {e}"}
    except ValueError as e:
        return {"message": f"Error decoding JSON response: {e}"}

@app.route("/upload_file", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            return jsonify({"success": False, "message": "No file part"}), 400
        
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "message": "No selected file"}), 400

        if file:
            filename = clean_filename(file.filename)
            file_data = file.read()

            # Update upload history
            upload_history.append(filename)

            # Upload to a random service
            upload_service = random.choice(["gofile", "pixeldrain"])
            if upload_service == "gofile":
                response = upload_to_gofile(file_data, filename)
            else:
                response = upload_to_pixeldrain(file_data, filename)

            if "link" in response:
                download_link = response["link"]
                download_history.append(download_link)
                flash(response['message']) #Flash the message for later use
                return jsonify({
                    "success": True,
                    "message": response['message'],
                    "redirect_url": url_for('upload_result', filename=filename, link=download_link)
                })
            else:
                return jsonify({"success": False, "message": response['message']}), 500

    return render_template("chat.html")

@app.route("/upload-result")
def upload_result():
    filename = request.args.get('filename')
    link = request.args.get('link')
    response_message = get_flashed_messages()
    return render_template("upload_result.html", filename=filename, download_link=link, response=response_message)

@app.route("/upload-history")
def upload_history_page():
    return render_template(
        "history.html", history=upload_history, title="Lịch sử tải lên"
    )

@app.route("/download-history")
def download_history_page():
    return render_template(
        "history.html", history=download_history, title="Lịch sử tải xuống"
    )


@app.route("/about")
def about():
    return render_template("about.html")  # Tạo trang about.html


@app.route("/api-check", methods=["GET", "POST"])
def api_check():
    if request.method == "POST":
        data = request.json
        url = data.get("url")
        method = data.get("method")
        headers = data.get("headers")
        payload = data.get("payload")
        timeout = int(data.get("timeout", 30))

        # Parse headers
        try:
            headers = json.loads(headers) if headers else {}
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON in headers"}), 400

        # Parse payload
        try:
            payload = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON in payload"}), 400

        # Prepare request kwargs
        kwargs = {
            "url": url,
            "headers": headers,
            "timeout": timeout
        }

        if method in ["POST", "PUT", "PATCH"]:
            kwargs["json"] = payload

        # Send request
        try:
            response = requests.request(method, **kwargs)

            # Prepare response data
            response_data = {
                "status": response.status_code,
                "statusText": response.reason,
                "headers": dict(response.headers),
                "body": response.json() if response.headers.get("Content-Type") == "application/json" else response.text
            }

            return jsonify(response_data), 200

        except requests.exceptions.RequestException as e:
            return jsonify({"error": str(e)}), 500

    # If it's a GET request, render the api_check.html template
    return render_template("api_check.html")


@app.route("/qrcode")
def qrcode_page():
    return render_template("qrcode.html")


# Error handler for file size limit
@app.errorhandler(413)
def request_entity_too_large(error):
    flash("File is too large! The limit is 100MB.")
    return redirect(request.url), 413


@app.route("/clipython")
def clipython():
    return render_template("clipython.html")


@app.route("/run-python", methods=["POST"])
def run_python_code():
    data = request.json
    code = data.get("code", "")
    input_values = data.get("input_values", [])

    # Create a temporary file to store the Python code
    temp_file = f"/tmp/temp_{uuid.uuid4().hex}.py"
    with open(temp_file, "w") as f:
        f.write(code)

    try:
        # Run the Python code with the provided input
        process = subprocess.Popen(
            [sys.executable, temp_file],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = process.communicate(input="\n".join(input_values))

        if stderr:
            return jsonify({"output": stderr, "error": True})
        else:
            return jsonify({"output": stdout, "error": False})
    except Exception as e:
        return jsonify({"output": str(e), "error": True})
    finally:
        # Remove the temporary file
        if os.path.exists(temp_file):
            os.remove(temp_file)


@app.route("/share-code", methods=["POST"])
def share_code():
    data = request.json
    code = data.get("code", "")

    # Create a unique ID for the shared code
    share_id = uuid.uuid4().hex

    # Save the code to a file (in a real application, you'd use a database)
    with open(f"/tmp/shared_code_{share_id}.py", "w") as f:
        f.write(code)

    # Create the share URL
    share_url = f"/view/{share_id}"

    return jsonify({"share_url": share_url})


@app.route("/view/<share_id>")
def view_shared_code(share_id):
    # Read the code from the file (in a real application, you'd use a database)
    try:
        with open(f"/tmp/shared_code_{share_id}.py", "r") as f:
            code = f.read()
        return render_template("view_shared_code.html", code=code)
    except FileNotFoundError:
        return "Code does not exist or has expired", 404


@app.route("/install-library", methods=["POST"])
def install_library():
    # Note: Installing libraries on-the-fly is not recommended in a production environment
    # This is just for demonstration purposes
    data = request.json
    library = data.get("library", "")

    if not library:
        return jsonify({"success": False, "error": "Library name cannot be empty"})

    try:
        # Install the library using pip
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", library],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": result.stderr})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# Route để hiển thị trang facts.html
@app.route("/facts", methods=["GET"])
def facts_page():
    return render_template("fact.html")


# Route để lấy fact từ Numbers API và dịch sang tiếng Việt
@app.route("/get-fact/<string:type>/<string:number>", methods=["GET"])
def get_fact(type, number):
    # Gọi đến Numbers API để lấy fact
    response = requests.get(f"http://numbersapi.com/{number}/{type}")

    if response.status_code != 200:
        return jsonify({"error": "Không thể lấy thông tin từ API"}), 500

    # Lấy dữ liệu từ phản hồi
    fact = response.text

    # Dịch fact sang tiếng Việt
    translated_fact = GoogleTranslator(source="en", target="vi").translate(fact)

    return jsonify(
        {
            "original_fact": fact,  # Trả về văn bản gốc
            "translated_fact": translated_fact,  # Trả về văn bản đã dịch
        }
    )


# Route để lấy cat fact
@app.route("/get-cat-fact", methods=["GET"])
def get_cat_fact():
    response = requests.get("https://catfact.ninja/fact")

    if response.status_code != 200:
        return jsonify({"error": "Không thể lấy thông tin từ Cat Fact API"}), 500

    # Lấy dữ liệu từ phản hồi
    cat_fact = response.json().get("fact", "Không có thông tin")

    # Dịch cat fact sang tiếng Việt
    translated_cat_fact = GoogleTranslator(source="en", target="vi").translate(cat_fact)

    return jsonify({"cat_fact": cat_fact, "translated_cat_fact": translated_cat_fact})


# Route để lấy Joke với category
@app.route("/get-joke/<string:category>", methods=["GET"])
def get_joke(category):
    response = requests.get(f"https://v2.jokeapi.dev/joke/{category}")

    if response.status_code != 200:
        return jsonify({"error": "Không thể lấy thông tin từ JokeAPI"}), 500

    joke_data = response.json()
    if joke_data["type"] == "single":
        joke = joke_data["joke"]
    else:
        joke = f"{joke_data['setup']} - {joke_data['delivery']}"

    translated_joke = GoogleTranslator(source="en", target="vi").translate(joke)

    return jsonify({"joke": joke, "translated_joke": translated_joke})


@app.route("/get-useless-fact")
def get_useless_fact():
    response = requests.get("https://uselessfacts.jsph.pl/random.json")
    data = response.json()
    fact = data.get("text", "Không có thông tin.")  # Lấy text từ response

    # Dịch sang tiếng Việt
    translated_fact = GoogleTranslator(source="en", target="vi").translate(fact)

    return jsonify({"useless_fact": fact, "translated_useless_fact": translated_fact})


# Route dịch văn bản từ tiếng Anh sang tiếng Việt
@app.route("/translate", methods=["POST"])
def translate_text():
    data = request.get_json()
    text = data.get("text")

    if not text:
        return jsonify({"error": "Văn bản không được để trống"}), 400

    # Dịch văn bản sang tiếng Việt
    translated_text = GoogleTranslator(source="en", target="vi").translate(text)

    return jsonify({"translated_text": translated_text})


@app.route("/ipconfig")
def ipconfig():
    trace_url = "https://one.one.one.one/cdn-cgi/trace"
    geolocation_url = "https://speed.cloudflare.com/meta"

    try:
        # Lấy dữ liệu từ Cloudflare Trace API
        trace_response = requests.get(trace_url)
        trace_data = dict(
            line.split("=") for line in trace_response.text.strip().split("\n")
        )

        # Lấy dữ liệu từ Cloudflare Geolocation API
        geo_response = requests.get(geolocation_url)
        geo_data = geo_response.json()

        # Trả dữ liệu cho ipconfig.html
        return render_template("ipconfig.html", trace=trace_data, geo=geo_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


API_KEY_WEATHER = "714c27439667f61cbf15f7ab466525a0"


@app.route("/weather", methods=["GET", "POST"])
def weather():
    if request.method == "POST":
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")

        if latitude and longitude:
            weather_url = f"http://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid={API_KEY_WEATHER}&units=metric"
            weather_response = requests.get(weather_url)
            weather_data = weather_response.json()

            forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?lat={latitude}&lon={longitude}&appid={API_KEY_WEATHER}&units=metric"
            forecast_response = requests.get(forecast_url)
            forecast_data = forecast_response.json()

            if (
                weather_response.status_code == 200
                and forecast_response.status_code == 200
            ):
                current_weather = {
                    "city": weather_data["name"],
                    "temperature": weather_data["main"]["temp"],
                    "description": weather_data["weather"][0]["description"],
                    "humidity": weather_data["main"]["humidity"],
                    "wind_speed": weather_data["wind"]["speed"],
                }

                forecast_info = []
                for entry in forecast_data["list"][:5]:
                    forecast_info.append(
                        {
                            "time": entry["dt_txt"],
                            "temperature": entry["main"]["temp"],
                            "description": entry["weather"][0]["description"],
                            "humidity": entry["main"]["humidity"],
                            "wind_speed": entry["wind"]["speed"],
                        }
                    )

                return jsonify(
                    {"current_weather": current_weather, "forecast_info": forecast_info}
                )
            else:
                return jsonify({"error": "Could not retrieve weather data."}), 400
        return jsonify({"error": "Invalid latitude or longitude."}), 400

    return render_template("weather.html")


@app.route("/load_more_forecasts", methods=["GET"])
def load_more_forecasts():
    latitude = request.args.get("latitude")
    longitude = request.args.get("longitude")
    last_forecast_index = int(request.args.get("last_forecast_index", 0))

    # Gọi API để lấy dữ liệu dự báo
    forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?lat={latitude}&lon={longitude}&appid={API_KEY_WEATHER}&units=metric"
    forecast_response = requests.get(forecast_url)
    forecast_data = forecast_response.json()

    if forecast_response.status_code == 200:
        forecasts = []
        for entry in forecast_data["list"][
            last_forecast_index : last_forecast_index + 5
        ]:  # Lấy 5 bản ghi tiếp theo
            forecasts.append(
                {
                    "time": entry["dt_txt"],
                    "temperature": entry["main"]["temp"],
                    "description": entry["weather"][0]["description"],
                    "humidity": entry["main"]["humidity"],
                    "wind_speed": entry["wind"]["speed"],
                }
            )
        # Trả về dữ liệu dự báo mới
        return jsonify({"forecasts": forecasts})
    else:
        return jsonify({"error": "Unable to fetch forecast data."}), 400


@app.route("/weather_by_location", methods=["POST"])
def weather_by_location():
    province = request.form.get("province")
    district = request.form.get("district")
    ward = request.form.get("ward")
    country = request.form.get("country")
    country_code = request.form.get("country_code")

    # Xây dựng chuỗi địa điểm
    location = f"{ward}, {district}, {province}, {country}"
    if country_code:
        location += f" ({country_code})"
    base_url = "http://api.openweathermap.org/data/2.5/forecast"

    params = {
        "q": location,
        "appid": API_KEY_WEATHER,
        "units": "metric",
        "lang": "vi",
    }

    try:
        response = requests.get(base_url, params=params)
        data = response.json()

        if response.status_code == 200:
            current_weather = data["list"][0]
            city_name = data["city"]["name"]

            # Xử lý thời tiết hiện tại
            current_weather_data = {
                "city": city_name,
                "temperature": round(current_weather["main"]["temp"], 1),
                "description": current_weather["weather"][0]["description"],
                "humidity": current_weather["main"]["humidity"],
                "wind_speed": round(
                    current_weather["wind"]["speed"] * 3.6, 1
                ),  # Chuyển đổi từ m/s sang km/h
            }

            # Xử lý dự báo
            forecast_data = []
            for forecast in data["list"][1:6]:  # 5 dự báo tiếp theo
                forecast_data.append(
                    {
                        "time": datetime.fromtimestamp(forecast["dt"]).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "temperature": round(forecast["main"]["temp"], 1),
                        "description": forecast["weather"][0]["description"],
                        "humidity": forecast["main"]["humidity"],
                        "wind_speed": round(
                            forecast["wind"]["speed"] * 3.6, 1
                        ),  # Chuyển đổi từ m/s sang km/h
                    }
                )

            return jsonify(
                {
                    "current_weather": current_weather_data,
                    "forecast_info": forecast_data,
                }
            )
        else:
            return jsonify({"error": f"Lỗi: {data['message']}"}), 400

    except requests.RequestException as e:
        return jsonify({"error": f"Yêu cầu thất bại: {str(e)}"}), 500


@app.route("/urldownload", methods=["GET", "POST"])
def urldownload():
    if request.method == "POST":
        url = request.form.get("url")
        if url:
            try:
                ydl_opts = {
                    "format": "bestvideo+bestaudio/best",
                    "noplaylist": True,
                    "quiet": True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(url, download=False)
                    formats = info_dict.get("formats", [])

                    # Check for supported platforms
                    if (
                        "youtube" in info_dict["webpage_url"]
                        or "facebook" in info_dict["webpage_url"]
                    ):
                        return jsonify(
                            {
                                "title": info_dict.get("title"),
                                "formats": formats,
                                "url": url,
                            }
                        )
                    else:
                        return jsonify(
                            {
                                "error": "Unsupported platform. Please provide a YouTube or Facebook URL."
                            }
                        )
            except Exception as e:
                return jsonify({"error": str(e)})
        else:
            return jsonify({"error": "No URL provided."})
    return render_template("urldownload.html")


@app.route("/download")
def download_video():
    url = request.args.get("url")
    format_id = request.args.get("format")
    if not url or not format_id:
        return "Missing URL or format", 400

    try:
        ydl_opts = {
            "format": format_id,
            "outtmpl": "downloads/%(title)s.%(ext)s",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info_dict)

        return send_file(filename, as_attachment=True)
    except Exception as e:
        return str(e), 500


@app.route("/convert")
def convert_to_mp3():
    url = request.args.get("url")
    if not url:
        return "Missing URL", 400

    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "outtmpl": "downloads/%(title)s.%(ext)s",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info_dict)
            mp3_filename = os.path.splitext(filename)[0] + ".mp3"

        return send_file(mp3_filename, as_attachment=True)
    except Exception as e:
        return str(e), 500


PEXELS_API_KEY = "1RLKfe657NlpkTa6gv60FnAJDlncnMYy1g1zcvaM5OXXhpiAIZftxtbA"


@app.route("/random-image", methods=["GET", "POST"])
def random_image():
    images = []  # Biến để lưu trữ danh sách hình ảnh
    if request.method == "POST":
        headers = {"Authorization": PEXELS_API_KEY}

        # Thêm tham số page ngẫu nhiên để yêu cầu hình ảnh khác nhau
        random_page = random.randint(1, 1000)  # Có thể điều chỉnh theo tổng số trang
        # Lấy số lượng hình ảnh ngẫu nhiên từ 9 đến 45
        random_per_page = random.randint(9, 45)

        response = requests.get(
            f"https://api.pexels.com/v1/search?query=nature&per_page={random_per_page}&page={random_page}",
            headers=headers,
        )

        if response.status_code == 200:
            data = response.json()
            # Lấy tất cả các hình ảnh từ dữ liệu
            if data["photos"]:
                for photo in data["photos"]:
                    images.append(
                        photo["src"]["large"]
                    )  # Lấy URL của hình ảnh chất lượng cao hơn

    return render_template("display_image.html", images=images)


NEWS_API_KEY = "372acef8e721441ca1a98732b031d253"


@app.route("/news", methods=["GET"])
def news():
    response = requests.get(
        f"https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWS_API_KEY}"
    )
    articles = []

    if response.status_code == 200:
        data = response.json()
        articles = data.get("articles", [])

    return render_template("news.html", articles=articles)


@app.route("/math", methods=["GET", "POST"])
def math_operation():
    if request.method == "POST":
        # Get operation and expression from the form data
        operation = request.form["operation"]
        expression = request.form["expression"]

        # URL encode the expression
        encoded_expression = requests.utils.quote(expression)

        # Form the API URL
        url = f"https://newton.now.sh/api/v2/{operation}/{encoded_expression}"

        # Send a request to Newton API
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return render_template(
                "math.html",
                result=result["result"],
                expression=expression,
                operation=operation,
            )
        else:
            error = "Invalid request or operation"
            return render_template("math.html", error=error)

    # Render the form for GET request
    return render_template("math.html")


@app.route("/projects")
def projects():
    # Lấy dữ liệu từ GitHub API
    response = requests.get("https://api.github.com/users/tanbaycu/repos")
    repos = response.json()
    return render_template("projects.html", repos=repos)


@app.route("/aichat", methods=["GET"])
def aichat():
    return render_template("aichat.html")


@app.route("/pdf")
def pdf_page():
    return render_template("pdf.html")


@app.route("/tools")
def tools():
    return render_template("tools.html")


@app.route("/spotify")
def spotify_page():
    return render_template("spotify.html")


API_KEY = "1373341a3e6d7cb9a723fff1"
BASE_URL = "https://v6.exchangerate-api.com/v6/{API_KEY}/latest/{base_currency}"


@app.route("/crypto")
def crypto():
    response = requests.get(BASE_URL.format(API_KEY=API_KEY, base_currency="USD"))
    if response.status_code == 200:
        data = response.json()
        currencies = list(data["conversion_rates"].keys())
    else:
        currencies = []

    currency_symbols = {
        "USD": "🇺🇸",
        "EUR": "🇪🇺",
        "GBP": "🇬🇧",
        "JPY": "🇯🇵",
        "AUD": "🇦🇺",
        "CAD": "🇨🇦",
        "CHF": "🇨🇭",
        "CNY": "🇨🇳",
        "HKD": "🇭🇰",
        "NZD": "🇳🇿",
        "SEK": "🇸🇪",
        "KRW": "🇰🇷",
        "SGD": "🇸🇬",
        "NOK": "🇳🇴",
        "MXN": "🇲🇽",
        "INR": "🇮🇳",
        "RUB": "🇷🇺",
        "ZAR": "🇿🇦",
        "TRY": "🇹🇷",
        "BRL": "🇧🇷",
        "TWD": "🇹🇼",
        "DKK": "🇩🇰",
        "PLN": "🇵🇱",
        "THB": "🇹🇭",
        "IDR": "🇮🇩",
        "HUF": "🇭🇺",
        "CZK": "🇨🇿",
        "ILS": "🇮🇱",
        "CLP": "🇨🇱",
        "PHP": "🇵🇭",
        "AED": "🇦🇪",
        "COP": "🇨🇴",
        "SAR": "🇸🇦",
        "MYR": "🇲🇾",
        "RON": "🇷🇴",
    }

    return render_template(
        "crypto.html", currencies=currencies, currency_symbols=currency_symbols
    )


@app.route("/get_exchange_rates/<base_currency>")
def get_exchange_rates(base_currency):
    response = requests.get(
        BASE_URL.format(API_KEY=API_KEY, base_currency=base_currency)
    )
    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({"error": "Failed to fetch exchange rates"}), 400


@app.route("/formatcode")
def format_code():
    return render_template("format.html")


@app.route("/password")
def password():
    return render_template("password.html")


@app.route("/country", methods=["GET", "POST"])
def country():
    if request.method == "POST":
        country_name = request.form.get("country")
        try:
            country_url = f"https://restcountries.com/v3.1/name/{country_name}"
            response = requests.get(country_url)
            response.raise_for_status()
            country_data = response.json()[0]

            return jsonify(
                {
                    "name": country_data["name"]["common"],
                    "official_name": country_data["name"]["official"],
                    "capital": (
                        country_data["capital"][0]
                        if "capital" in country_data
                        else "N/A"
                    ),
                    "population": country_data["population"],
                    "area": country_data["area"],
                    "region": country_data["region"],
                    "subregion": country_data.get("subregion", "N/A"),
                    "languages": (
                        list(country_data["languages"].values())
                        if "languages" in country_data
                        else []
                    ),
                    "currencies": [
                        f"{code} ({data['name']})"
                        for code, data in country_data.get("currencies", {}).items()
                    ],
                    "flag": country_data["flags"]["svg"],
                    "coat_of_arms": country_data.get("coatOfArms", {}).get("svg", ""),
                    "map": country_data["maps"]["googleMaps"],
                    "timezones": country_data["timezones"],
                    "continents": country_data["continents"],
                    "borders": country_data.get("borders", []),
                    "independent": country_data["independent"],
                    "un_member": country_data["unMember"],
                    "gini": country_data.get("gini", {}),
                    "car": country_data["car"]["side"],
                }
            )
        except requests.RequestException as e:
            return jsonify({"error": f"Error fetching country data: {str(e)}"}), 500
        except (KeyError, IndexError) as e:
            return jsonify({"error": f"Error processing country data: {str(e)}"}), 500

    return render_template("country.html")


@app.route("/bmi")
def bmi():
    return render_template("bmi.html")


@app.route("/documents")
def documents():
    return render_template("documents.html")


MORSE_CODE_DICT = {
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    "0": "-----",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    " ": " ",
}

SHARED_CONVERSIONS = {}


@app.route("/mamorse", methods=["GET"])
def morse_maestro():
    return render_template("morse.html")


@app.route("/convert", methods=["POST"])
def convert():
    data = request.json
    text = data["text"]
    mode = data["mode"]

    try:
        if mode == "to_morse":
            result = " ".join(MORSE_CODE_DICT.get(char.upper(), char) for char in text)
        else:
            morse_to_char = {v: k for k, v in MORSE_CODE_DICT.items()}
            result = "".join(morse_to_char.get(code, code) for code in text.split())

        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/share", methods=["POST"])
def share_conversion():
    data = request.json
    share_id = str(uuid.uuid4())
    SHARED_CONVERSIONS[share_id] = data
    return jsonify({"share_id": share_id})


@app.route("/shared/<share_id>", methods=["GET"])
def get_shared_conversion(share_id):
    if share_id in SHARED_CONVERSIONS:
        return jsonify(SHARED_CONVERSIONS[share_id])
    else:
        abort(404)


@app.route("/morse_code_dict", methods=["GET"])
def get_morse_code_dict():
    return jsonify(MORSE_CODE_DICT)


@app.route("/trivia", methods=["GET"])
def trivia():
    return render_template("trivia.html")


routes = [
    {'path': '/', 'name': 'Home'},
    {'path': '/about-me', 'name': 'About Me'},
    {'path': '/dev', 'name': 'Dev'},
    {'path': '/shorten-link', 'name': 'URL Shortener'},
    {'path': '/upload_file', 'name': 'File Upload'},
    {'path': '/upload-history', 'name': 'Upload History'},
    {'path': '/download-history', 'name': 'Download History'},
    {'path': '/about', 'name': 'About'},
    {'path': '/api-check', 'name': 'API Check'},
    {'path': '/qrcode', 'name': 'QR Code'},
    {'path': '/clipython', 'name': 'CLI Python'},
    {'path': '/facts', 'name': 'Facts'},
    {'path': '/ipconfig', 'name': 'IP Config'},
    {'path': '/weather', 'name': 'Weather'},
    {'path': '/urldownload', 'name': 'URL Download'},
    {'path': '/random-image', 'name': 'Random Image'},
    {'path': '/news', 'name': 'News'},
    {'path': '/math', 'name': 'Math Operations'},
    {'path': '/projects', 'name': 'Projects'},
    {'path': '/aichat', 'name': 'AI Chat'},
    {'path': '/pdf', 'name': 'PDF'},
    {'path': '/tools', 'name': 'Tools'},
    {'path': '/spotify', 'name': 'Spotify'},
    {'path': '/crypto', 'name': 'Crypto'},
    {'path': '/formatcode', 'name': 'Format Code'},
    {'path': '/password', 'name': 'Password'},
    {'path': '/country', 'name': 'Country'},
    {'path': '/bmi', 'name': 'BMI Calculator'},
    {'path': '/documents', 'name': 'Documents'},
    {'path': '/mamorse', 'name': 'Morse Code'},
    {'path': '/trivia', 'name': 'Trivia'},
]

@app.route('/status')
def status_page():
    return render_template('status.html', routes=routes)

@app.route('/check-route-status')
def check_route_status():
    path = request.args.get('path')
    route_name = next((route['name'] for route in routes if route['path'] == path), path)
    start_time = time.time()
    try:
        # Simulating API call with random response time and status
        time.sleep(random.uniform(0.1, 2.0))
        response_time = round((time.time() - start_time) * 1000)
        
        if random.random() < 0.9:  # 90% chance of success
            if response_time < 200:
                status = 'up'
            elif response_time < 1000:
                status = 'degraded'
            else:
                status = 'down'
        else:
            status = 'down'
            response_time = None
    except Exception:
        status = 'down'
        response_time = None

    return render_template('status_card.html', status=status, response_time=response_time, route_name=route_name)

@app.route('/check-all-routes')
def check_all_routes():
    return render_template('status.html', routes=routes)

@app.route('/api/incidents')
def get_incidents():
    # Simulated incident data
    incidents = [
        {
            "id": 1,
            "service": "API Check",
            "description": "Intermittent outages due to server overload",
            "status": "Resolved",
            "created_at": "2023-05-15T14:30:00Z",
            "updated_at": "2023-05-15T16:45:00Z"
        },
        {
            "id": 2,
            "service": "URL Shortener",
            "description": "Database connection issues causing slow response times",
            "status": "Investigating",
            "created_at": "2023-05-18T09:15:00Z",
            "updated_at": "2023-05-18T10:30:00Z"
        }
    ]
    return jsonify(incidents)


@app.route("/webapp")
def webapp():
    return render_template("webapp.html")

@app.route("/solar3d")
def solar3d():
    return render_template("solar3d.html")



SENDER_EMAIL = "testuserbaycu@gmail.com"  # Email của bạn
SENDER_PASSWORD = "jqzq kbqh hywd gmxw"  # Mật khẩu ứng dụng của Gmail
RECEIVER_EMAIL = "tanbaycu@gmail.com"  # Email cá nhân của bạn

@app.route('/subscribe', methods=['POST'])
def subscribe():
    data = request.json
    subscriber_email = data.get('email')

    if not subscriber_email:
        return jsonify({"success": False, "message": "Email không hợp lệ"}), 400

    try:
        # Gửi email thông báo cho bạn
        send_notification_email(subscriber_email)
        
        # Gửi email xác nhận cho người đăng ký
        send_confirmation_email(subscriber_email)

        return jsonify({"success": True, "message": "Đăng ký thành công! Vui lòng kiểm tra email của bạn."}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "message": "Đã xảy ra lỗi khi đăng ký. Vui lòng thử lại sau."}), 500

def send_notification_email(subscriber_email):
    subject = "Đăng ký mới nhận bản tin"
    body = f"Có người dùng mới đăng ký nhận bản tin:\n\nEmail: {subscriber_email}"
    send_email(RECEIVER_EMAIL, subject, body)

def send_confirmation_email(subscriber_email):
    subject = "Chào mừng bạn đến với Tân 7 Cú - Bắt đầu hành trình số hóa của bạn! 🚀"
    body = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Chào mừng đến với Tân 7 Cú</title>
    </head>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
        <div style="background-color: #6c63ff; color: #ffffff; padding: 20px; text-align: center; border-radius: 5px 5px 0 0;">
            <h1 style="margin: 0;">Chào mừng bạn đến với Tân 7 Cú! 🎉</h1>
        </div>
        <div style="background-color: #ffffff; padding: 20px; border-radius: 0 0 5px 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
            <p>Xin chào người bạn mới thân mến,</p>
            <p>Chúng tôi vô cùng phấn khởi chào đón bạn vào đại gia đình Tân 7 Cú! 🚀 Cảm ơn bạn đã tin tưởng và đăng ký nhận bản tin của chúng tôi. Bạn đã sẵn sàng cho một hành trình tuyệt vời chưa?</p>
            <h2 style="color: #6c63ff;">🌟 Khám phá thế giới số cùng chúng tôi</h2>
            <ul style="list-style-type: none; padding-left: 0;">
                <li style="margin-bottom: 10px;">🚀 Trải nghiệm công cụ trực tuyến đột phá và tiện lợi</li>
                <li style="margin-bottom: 10px;">💡 Tiếp cận kho tàng kiến thức và kinh nghiệm từ các chuyên gia hàng đầu</li>
                <li style="margin-bottom: 10px;">🌐 Luôn cập nhật với những xu hướng công nghệ mới nhất và hot nhất</li>
                <li style="margin-bottom: 10px;">🤝 Kết nối với cộng đồng đam mê công nghệ sôi động</li>
            </ul>
            <h2 style="color: #6c63ff;">🎨 Bắt đầu hành trình sáng tạo của bạn</h2>
            <p>Hãy khám phá ngay những tính năng tuyệt vời mà chúng tôi đã chuẩn bị dành riêng cho bạn:</p>
            <ul>
                <li><a href="https://tanbaycu.vercel.app/upload_file" style="color: #6c63ff;">📁 Tải lên và chia sẻ tệp - Lưu trữ an toàn, chia sẻ dễ dàng</a></li>
                <li><a href="https://tanbaycu.vercel.app/aichat" style="color: #6c63ff;">🤖 Trò chuyện với AI thông minh - Khám phá trí tuệ nhân tạo tiên tiến</a></li>
                <li><a href="https://tanbaycu.vercel.app/shorten-link" style="color: #6c63ff;">🔗 Rút gọn liên kết - Tạo URL ngắn gọn, ấn tượng</a></li>
                <li><a href="https://tanbaycu.vercel.app/qrcode" style="color: #6c63ff;">📱 Tạo mã QR độc đáo - Kết nối thế giới thực và số</a></li>
            </ul>
            <p>Đừng bỏ lỡ những tin tức hấp dẫn và tính năng mới nhất! Hãy theo dõi chúng tôi trên mạng xã hội:</p>
            <p>
                <a href="https://github.com/tanbaycu" style="color: #6c63ff; margin-right: 10px;">GitHub</a>
                <a href="https://www.facebook.com/tanbaycu.kaiser/" style="color: #6c63ff;">Facebook</a>
            </p>
            <p>Chúc bạn có những trải nghiệm tuyệt vời và đầy cảm hứng cùng Tân 7 Cú! Hãy sẵn sàng để khám phá, học hỏi và sáng tạo!</p>
            <p>Trân trọng,<br>Đội ngũ Tân 7 Cú</p>
        </div>
        <div style="margin-top: 20px; text-align: center; font-size: 12px; color: #888;">
            <p>Email này được gửi đến {subscriber_email}. Nếu bạn không yêu cầu email này, vui lòng bỏ qua nó.</p>
            <p>Tân 7 Cú - Nơi đổi mới sáng tạo gặp gỡ, Cộng đồng kết nối không ngừng</p>
        </div>
    </body>
    </html>
    """
    send_email(subscriber_email, subject, body, is_html=True)

def send_email(to_email, subject, body, is_html=False):
    message = MIMEMultipart()
    message['From'] = SENDER_EMAIL
    message['To'] = to_email
    message['Subject'] = subject

    if is_html:
        message.attach(MIMEText(body, 'html'))
    else:
        message.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(message)




if __name__ == "__main__":
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    app.run(debug=True)
