import os
import random
import base64
# import google.generativeai as genai
import json
import requests
import yt_dlp
import sys
import re
import os
import subprocess
from deep_translator import GoogleTranslator

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
)

app = Flask(__name__)
UPLOAD_FOLDER = '/tmp/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.secret_key = "28a03d4e9561e85914da8e57f55f5bbe"
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB
# api_key = "AIzaSyCSz6oCSnlQnpFKVFjZc421IDWjoVRwQaM"
# genai.configure(api_key=api_key)

PIXELDRAIN_API_KEY = "fba3e1f5-269b-4758-8e44-78326d0d7d95"
RETRY_LIMIT = 3

upload_history = []
download_history = []

"""
def convert_chat_history(history):
    converted_history = []
    for message in history:
        if message["role"] == "user":
            converted_history.append({"role": "user", "parts": [message["text"]]})
        elif message["role"] == "model":
            converted_history.append({"role": "model", "parts": [message["text"]]})
    return converted_history


# Đọc lịch sử chat từ file
try:
    with open("geminimath.json", "r", encoding="utf-8") as file:
        raw_history = json.load(file)
except FileNotFoundError:
    raw_history = []

# Chuyển đổi lịch sử sang định dạng mong muốn
chat_history = convert_chat_history(raw_history)

generation_config = {
    "temperature": 2,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

# Khởi tạo mô hình
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

# Khởi tạo phiên trò chuyện với lịch sử đã chuyển đổi
chat_session = model.start_chat(history=chat_history)

"""

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


def upload_to_gofile(file_path):
    url = "https://store1.gofile.io/uploadFile"
    with open(file_path, "rb") as file:
        files = {"file": file}
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
            return f"Request error: {e}"
        except ValueError as e:
            return f"Error decoding JSON response: {e}"


def upload_to_pixeldrain(file_path):
    url = "https://pixeldrain.com/api/file"
    headers = {
        "Authorization": "Basic "
        + base64.b64encode(f":{PIXELDRAIN_API_KEY}".encode()).decode()
    }
    with open(file_path, "rb") as file:
        files = {"file": file}
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
            return f"Request error: {e}"
        except ValueError as e:
            return f"Error decoding JSON response: {e}"


@app.route("/")
def homepage():
    return send_file("index.html")


@app.route("/upload_file", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file part")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)

        if file:
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            try:
                file.save(file_path)
            except Exception as e:
                flash(f"Error saving file: {e}")
                return redirect(request.url)

            # Update upload history
            upload_history.append(file.filename)

            # Upload to a random service
            upload_service = random.choice(["gofile", "pixeldrain"])
            if upload_service == "gofile":
                response = upload_to_gofile(file_path)
            else:
                response = upload_to_pixeldrain(file_path)

            # Combine message and download link
            if "link" in response:
                download_link = response["link"]
                response_message = f"{response['message']} Download link: <a href='{download_link}' target='_blank' style='color: #50fa7b;'>Click here</a>."
                download_history.append(download_link)
            else:
                response_message = response["message"]

            # Clean up the uploaded file
            os.remove(file_path)

            # Flash the response message and redirect
            flash(
                response_message
            )  # Flash the response message for display on the next page
            return redirect(
                url_for("upload_result")
            )  # Redirect to a new route to display the result

    return render_template("chat.html")


# Upload history route (Lịch sử tải lên)
@app.route("/upload-history")
def upload_history_page():
    return render_template(
        "history.html", history=upload_history, title="Lịch sử tải lên"
    )


@app.route("/upload-result")
def upload_result():
    response_message = get_flashed_messages()  # Get the flashed message
    return render_template("upload_result.html", response=response_message)


# Download history route (Lịch sử tải xuống)
@app.route("/download-history")
def download_history_page():
    return render_template(
        "history.html", history=download_history, title="Lịch sử tải xuống"
    )


"""@app.route("/aibot-chat", methods=["GET"])
def aibot_chat():
    return render_template("aibot.html")


@app.route("/message", methods=["POST"])
def message():
    user_input = request.json.get("message")
    try:
        response = chat_session.send_message(user_input)
    except genai.generation_types.StopCandidateException as e:
        return jsonify({"error": "Safety filter triggered", "details": str(e)}), 400

    # Thêm tin nhắn mới vào lịch sử với định dạng yêu cầu
    chat_history.append({"role": "user", "parts": [user_input]})
    chat_history.append({"role": "model", "parts": [response.text]})

    # Lưu lịch sử tin nhắn vào file với định dạng yêu cầu
    try:
        with open("geminimath.json", "w", encoding="utf-8") as file:
            json.dump(chat_history, file, ensure_ascii=False, indent=4)
    except Exception as e:
        return jsonify({"error": f"Failed to save chat history: {str(e)}"}), 500

    return jsonify({"response": response.text})


@app.route("/clear-history", methods=["POST"])
def clear_history():
    global chat_history
    chat_history = []
    try:
        with open("geminimath.json", "w", encoding="utf-8") as file:
            json.dump([], file, ensure_ascii=False, indent=4)  # Xóa nội dung file
        return jsonify({"message": "History cleared successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

"""
@app.route("/about")
def about():
    return render_template("about.html")  # Tạo trang about.html


@app.route("/api-check", methods=["GET", "POST"])
def api_check():
    if request.method == "POST":
        url = request.form.get("url")
        method = request.form.get("method")
        payload = request.form.get("payload")

        # Kiểm tra phương thức và gửi yêu cầu
        try:
            if method == "GET":
                response = requests.get(url)
            elif method == "POST":
                response = requests.post(
                    url, json=json.loads(payload) if payload else {}
                )
            elif method == "PUT":
                response = requests.put(
                    url, json=json.loads(payload) if payload else {}
                )
            elif method == "DELETE":
                response = requests.delete(url)

            # Trả về kết quả
            return (
                jsonify(
                    {
                        "status": response.status_code,
                        "data": (
                            response.json()
                            if response.headers.get("Content-Type")
                            == "application/json"
                            else response.text
                        ),
                    }
                ),
                response.status_code,
            )

        except requests.exceptions.RequestException as e:
            return jsonify({"error": str(e)}), 500

    # Nếu là phương thức GET, render trang api_check.html
    return render_template("api_check.html")


@app.route("/qrcode")
def qrcode_page():
    return render_template("qrcode.html")


# Error handler for file size limit
@app.errorhandler(413)
def request_entity_too_large(error):
    flash("File is too large! The limit is 100MB.")
    return redirect(request.url), 413


@app.route("/clipython", methods=["GET"])
def clipython_page():
    return render_template("clipython.html")


@app.route("/run-python", methods=["POST"])
def run_python_code_temp():
    data = request.json

    if "code" not in data:
        return jsonify({"error": "Không có mã Python nào được gửi."}), 400

    code = data.get("code", "")
    input_values = data.get("input_values", [])  # Nhận danh sách giá trị đầu vào

    # Lưu mã Python vào tệp tạm thời
    with open("temp_script.py", "w", encoding="utf-8") as f:
        f.write(code)

    # Tạo một iterator để gửi lần lượt các giá trị vào input()
    input_values_iter = iter(input_values)
    try:
        # Tạo một hàm để thay thế input() trong mã Python
        def mock_input(prompt):
            return next(input_values_iter)

        # Ghi đè hàm input trong mã Python
        result = subprocess.run(
            ["python", "temp_script.py"],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            input="\n".join(input_values),  # Gửi tất cả các giá trị đầu vào
        )
        output = result.stdout
    except subprocess.CalledProcessError as e:
        output = e.stderr

    os.remove("temp_script.py")

    return jsonify({"output": output})


@app.route("/install-library", methods=["POST"])
def install_library():
    data = request.json
    library_name = data.get("library")

    if not library_name:
        return jsonify({"error": "Vui lòng cung cấp tên thư viện."}), 400

    try:
        # Cài đặt thư viện bằng pip
        subprocess.check_call([sys.executable, "-m", "pip", "install", library_name])
        return jsonify(
            {"message": f"Thư viện {library_name} đã được cài đặt thành công."}
        )
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Lỗi khi cài đặt thư viện: {str(e)}"}), 500


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


API_KEY = "714c27439667f61cbf15f7ab466525a0"


@app.route("/weather", methods=["GET", "POST"])
def weather():
    if request.method == "POST":
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")

        if latitude and longitude:
            # Lấy thông tin thời tiết hiện tại
            weather_url = f"http://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid={API_KEY}&units=metric"
            weather_response = requests.get(weather_url)
            weather_data = weather_response.json()

            # Lấy thông tin dự báo thời tiết 5 giờ tiếp theo
            forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?lat={latitude}&lon={longitude}&appid={API_KEY}&units=metric"
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

                # Lấy thông tin dự báo trong 5 giờ
                forecast_info = []
                for entry in forecast_data["list"][
                    :5
                ]:  # Lấy 5 bản ghi (tương ứng với 5 giờ tiếp theo)
                    forecast_info.append(
                        {
                            "time": entry["dt_txt"],
                            "temperature": entry["main"]["temp"],
                            "description": entry["weather"][0]["description"],
                            "humidity": entry["main"]["humidity"],
                            "wind_speed": entry["wind"]["speed"],
                        }
                    )

                # Lưu trữ thông tin forecast để lấy sau
                return render_template(
                    "weather.html",
                    current_weather=current_weather,
                    forecast_info=forecast_info,
                    latitude=latitude,
                    longitude=longitude,
                    last_forecast_index=5,  # Để theo dõi vị trí đã lấy dự báo
                )

            else:
                error_message = (
                    "Could not retrieve weather data. Please check the location."
                )
                return render_template("weather.html", error=error_message)

    return render_template("weather.html")


@app.route("/load_more_forecasts", methods=["GET"])
def load_more_forecasts():
    latitude = request.args.get("latitude")
    longitude = request.args.get("longitude")
    last_forecast_index = int(request.args.get("last_forecast_index", 0))

    # Gọi API để lấy dữ liệu dự báo
    forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?lat={latitude}&lon={longitude}&appid={API_KEY}&units=metric"
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


@app.route("/urldownload", methods=["GET", "POST"])
def urldownload():
    if request.method == "POST":
        url = request.form.get("url")
        if url:
            try:
                # Tùy chọn cho yt-dlp
                ydl_opts = {
                    "format": "bestvideo+bestaudio/best",
                    "noplaylist": True,
                    "quiet": True,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(url, download=False)
                    formats = info_dict.get("formats", [])

                    # Lọc video từ Facebook và YouTube
                    if (
                        "youtube" in info_dict["webpage_url"]
                        or "facebook" in info_dict["webpage_url"]
                    ):
                        return render_template(
                            "urldownload.html",
                            formats=formats,
                            title=info_dict.get("title"),
                            url=url,
                        )
                    else:
                        return "Unsupported platform. Please provide a YouTube or Facebook URL."
            except Exception as e:
                return str(e)
    return render_template("urldownload.html", formats=None)


PEXELS_API_KEY = "1RLKfe657NlpkTa6gv60FnAJDlncnMYy1g1zcvaM5OXXhpiAIZftxtbA"


@app.route("/random-image", methods=["GET", "POST"])
def random_image():
    images = []  # Biến để lưu trữ danh sách hình ảnh
    if request.method == "POST":
        headers = {"Authorization": PEXELS_API_KEY}

        # Thêm tham số page ngẫu nhiên để yêu cầu hình ảnh khác nhau
        random_page = random.randint(1, 1000)  # Có thể điều chỉnh theo tổng số trang
        response = requests.get(
            f"https://api.pexels.com/v1/search?query=nature&per_page=10&page={random_page}",
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


if __name__ == "__main__":
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    app.run(debug=True)
