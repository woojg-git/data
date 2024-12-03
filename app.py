from flask import Flask, render_template, request, redirect, url_for, session,g
from flask_login import login_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import cv2
import random
import os
import pandas as pd
import re
import sqlite3
import mediapipe as mp
import numpy as np


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션 암호화에 사용

# 데이터 파일 경로 설정
DATA_FILE = r"C:\Users\woo\sql\data\서울올림픽기념국민체육진흥공단_국민체력100 운동처방 동영상주소 정보_20210727.csv.csv"
DATA_FILE_MBTI = r"C:\Users\woo\sql\data\KS_YNGBGS_INFNTCHLD_UTILIIZA_POSBL_ALSFC_PROGRM_INFO_202411.csv"
DATA_EXERCISE = r"C:\Users\woo\sql\data\한국건강증진개발원_보건소 모바일 헬스케어 운동_20240919.csv"
DATA_calorie = r"C:\Users\woo\sql\data\농림수산식품교육문화정보원_칼로리 정보_20190926.csv"

# 데이터 로드
def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE, encoding='cp949')
        return df
    else:
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {DATA_FILE}")

# MBTI 데이터 로드 함수
def load_data_mbti():
    if os.path.exists(DATA_FILE_MBTI):
        df = pd.read_csv(DATA_FILE_MBTI, encoding='utf-8')
        return df
    else:
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {DATA_FILE_MBTI}")

# EXERCISE 데이터 로드 함수
def load_data_exercise():
    if os.path.exists(DATA_EXERCISE):
        df = pd.read_csv(DATA_EXERCISE, encoding='cp949')
        return df
    else:
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {DATA_EXERCISE}")


# DB 초기화 함수
def drop_photo_records_table():
    conn = sqlite3.connect('photo_records.db')
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS photo_records")
    conn.commit()
    conn.close()

# 사용자 정보를 저장할 테이블(회원가입 및 로그인)
def init_user_db():
    conn = sqlite3.connect('photo_records.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS photo_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,  -- 사용자 ID 추가
            photo_path TEXT NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)  -- 사용자 테이블과 연결
        )
    ''')
    conn.commit()
    conn.close()


# 회원가입
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # 비밀번호 해싱
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        try:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "이미 존재하는 사용자입니다. 다른 아이디를 사용해주세요."

    return render_template('register.html')

# 데이터베이스_로그인 연결 함수
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('users.db', timeout=10)  # 10초 동안 잠금을 기다립니다.
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# 로그인
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']  # 입력한 아이디
        password = request.form['password']  # 입력한 비밀번호

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()

        if user and check_password_hash(user[2], password):  # 비밀번호 확인
            session['user_id'] = user[0]  # 사용자 ID 저장
            session['username'] = username  # 사용자 이름 저장
            return redirect(url_for('index'))  # 메인 페이지로 이동
        else:
            return "아이디 또는 비밀번호가 잘못되었습니다."

    return render_template('login.html')


# 로그아웃
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)  # 세션에서 사용자 ID 삭제
    session.pop('username', None)  # 세션에서 사용자 이름 삭제
    return redirect(url_for('login'))


# 로그인 상태확인 로그인 안하면 로그인페이지로 다이렉트
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/protected')
@login_required
def protected():
    return "이 페이지는 로그인한 사용자만 볼 수 있습니다."

# 음식 선택
@app.route("/select_food", methods=["GET", "POST"])
def select_food():
    if request.method == "POST":
        selected_foods = request.form.getlist("foods")
        calorie_data = load_data_calorie()

        total_nutrition = {
            "칼로리": 0,
            "탄수화물": 0,
            "단백질": 0,
            "지방": 0,
            "콜레스트롤": 0,
            "식이섬유": 0,
            "나트륨": 0
        }

        # 기존 음식 목록에서 영양소 합산
        for food in selected_foods:
            food_row = calorie_data[calorie_data["음식명"] == food].iloc[0]
            total_nutrition["칼로리"] += food_row["1인분칼로리(kcal)"]
            total_nutrition["탄수화물"] += food_row["탄수화물(g)"]
            total_nutrition["단백질"] += food_row["단백질(g)"]
            total_nutrition["지방"] += food_row["지방(g)"]
            total_nutrition["콜레스트롤"] += food_row.get("콜레스트롤(g)", 0)
            total_nutrition["식이섬유"] += food_row["식이섬유(g)"]
            total_nutrition["나트륨"] += food_row["나트륨(g)"]

        # 수동 입력 음식 처리
        manual_food_name = request.form.get("manual_food_name")
        if manual_food_name:
            total_nutrition["칼로리"] += float(request.form.get("manual_food_calories", 0))
            total_nutrition["탄수화물"] += float(request.form.get("manual_food_carbs", 0))
            total_nutrition["단백질"] += float(request.form.get("manual_food_protein", 0))
            total_nutrition["지방"] += float(request.form.get("manual_food_fat", 0))
            total_nutrition["콜레스트롤"] += float(request.form.get("manual_food_cholesterol", 0))
            total_nutrition["식이섬유"] += float(request.form.get("manual_food_fiber", 0))
            total_nutrition["나트륨"] += float(request.form.get("manual_food_sodium", 0))

        return render_template("nutrition_result.html", total_nutrition=total_nutrition)

    # 음식 목록 로드
    calorie_data = load_data_calorie()
    food_list = calorie_data["음식명"].tolist()
    return render_template("select_food.html", food_list=food_list)

# 칼로리 데이터 로드 함수
def load_data_calorie():
    if os.path.exists(DATA_calorie):
        df = pd.read_csv(DATA_calorie, encoding='cp949')
        return df
    else:
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {DATA_calorie}")

# 운동명 검색 후 결과 보여주는 페이지
@app.route("/search", methods=["GET", "POST"])
def search_exercise():
    results = []
    if request.method == "POST":
        search_term = request.form["search_teㅋrm"]

        # 운동 데이터 로드
        exercise_df = load_data_exercise()
                # 검색어를 포함하는 운동명 찾기
        results = exercise_df[exercise_df["운동명"].str.contains(search_term, case=False, na=False)]

        # 검색 결과를 리스트로 변환
        results = results[["운동명", "단위체중당에너지소비량"]].to_dict(orient='records')

    return render_template("search.html", results=results)

# 칼로리 계산 페이지
@app.route('/calculate_energy', methods=['POST'])
def calculate_energy():
    weight = request.form['weight']
    exercise_time = request.form['exercise_time']
    exercise_name = request.form['exercise_name']

    # 간단한 열량 계산 로직
    calories_burned = float(exercise_time) * 5  # 대략적인 계산 (시간 * 5 칼로리)

    # 결과를 출력할 HTML로 데이터 전달
    return render_template('search_result.html', calories_burned=calories_burned, weight=weight, exercise_name=exercise_name, exercise_time=exercise_time)

# 유튜브 썸네일 URL 생성 함수
def get_youtube_thumbnail(video_url):
    video_id = None
    youtube_patterns = [
        r"youtube.com/watch\?v=([a-zA-Z0-9_-]+)",  # 유튜브
        r"youtu.be/([a-zA-Z0-9_-]+)"               # youtu.be
    ]

    for pattern in youtube_patterns:
        match = re.search(pattern, video_url)
        if match:
            video_id = match.group(1)
            break

    if video_id:
        return f"https://img.youtube.com/vi/{video_id}/0.jpg"
    return None

# 업로드 폴더 설정
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 파일 확장자 허용 함수
def allowed_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# DB 초기화 함수
def init_db():
    conn = sqlite3.connect('photo_records.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS photo_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,  -- 사용자 ID 추가
            photo_path TEXT NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)  -- 사용자 테이블과 연결
        )
    ''')
    conn.commit()
    conn.close()


# 앱 시작 시 DB 초기화
init_db()

# 사진 업로드 처리
@app.route("/upload", methods=["GET", "POST"])
def upload_photo():
    if request.method == "POST":
        file = request.files["photo"]
        date = request.form["date"]

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)  # 저장 경로
            file.save(file_path)  # 파일 저장

            # DB에 저장
            user_id = session['user_id']  # 현재 로그인한 사용자 ID
            conn = sqlite3.connect('photo_records.db')
            c = conn.cursor()
            c.execute("INSERT INTO photo_records (user_id, photo_path, date) VALUES (?, ?, ?)", (user_id, filename, date))
            conn.commit()
            conn.close()

            # 업로드 후 분석 페이지로 리디렉션
            return redirect(url_for('analyze_photo_route', image_src=filename))
    return render_template("upload.html")




# DB에서 사진 기록을 불러오기
@app.route("/calendar", methods=["GET"])
def view_calendar():
    user_id = session.get('user_id')  # 현재 로그인한 사용자 ID
    conn = sqlite3.connect('photo_records.db')
    c = conn.cursor()
    c.execute("SELECT * FROM photo_records WHERE user_id = ?", (user_id,))
    records = c.fetchall()  # 해당 사용자에 대한 모든 사진 기록 가져오기
    conn.close()

    # 각 사진의 경로를 'uploads/파일명'으로 합치기
    records_with_full_path = [(record[0], os.path.join('uploads', record[2]), record[3]) for record in records]

    return render_template("calendar.html", records=records_with_full_path)  # 템플릿에 전달

@app.route('/edit/<int:record_id>', methods=['GET', 'POST'])
def edit_photo(record_id):
    conn = sqlite3.connect('photo_records.db')
    c = conn.cursor()
    c.execute("SELECT * FROM photo_records WHERE id = ?", (record_id,))
    record = c.fetchone()
    conn.close()

    if request.method == 'POST':
        photo = request.files['photo']
        if photo and allowed_file(photo.filename):
            new_filename = secure_filename(photo.filename)
            # 기존 파일 삭제
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], record[1]))  
            # 새로운 파일 저장
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))

            # DB 업데이트
            conn = sqlite3.connect('photo_records.db')
            c = conn.cursor()
            c.execute("UPDATE photo_records SET photo_path = ? WHERE id = ?", (new_filename, record_id))
            conn.commit()
            conn.close()

            return redirect(url_for('view_calendar'))  # 수정 후 달력 페이지로 이동

    return render_template('edit_photo.html', filename=record[1], record_id=record_id)

@app.route('/delete/<int:record_id>', methods=['POST'])
def delete_photo(record_id):
    # 해당 record_id에 맞는 기록을 불러와 삭제합니다
    conn = sqlite3.connect('photo_records.db')
    c = conn.cursor()
    c.execute("SELECT photo_path FROM photo_records WHERE id = ?", (record_id,))
    record = c.fetchone()
    if record:
        # 파일 삭제
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], record[0])
        if os.path.exists(file_path):
            os.remove(file_path)

        # DB에서 삭제
        c.execute("DELETE FROM photo_records WHERE id = ?", (record_id,))
        conn.commit()
    conn.close()

    return redirect(url_for('view_calendar'))

#신체분석
# MediaPipe 준비
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
mp_drawing = mp.solutions.drawing_utils


@app.route('/analyze_photo/<image_src>', methods=['GET'])
@login_required
def analyze_photo_route(image_src):
    # 이미지 파일 경로 설정
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], image_src)

    if os.path.exists(file_path):
        # 이미지 읽기 및 분석
        image = cv2.imread(file_path)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # 신체 분석
        results = pose.process(image_rgb)

        if results.pose_landmarks:
            mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

            # 특정 관절 위치 추출
            landmarks = results.pose_landmarks.landmark
            # 어깨, 허리, 엉덩이, 무릎 좌표 추출
            left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
            left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
            right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value]
            left_knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value]
            right_knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value]

            # 비율 분석: 상체와 하체 비율
            shoulder_height = (left_shoulder.y + right_shoulder.y) / 2
            hip_height = (left_hip.y + right_hip.y) / 2

            analysis_results = []

            # 상체와 하체 비율 평가
            if shoulder_height < hip_height:
                analysis_results.append("상체에 비해 하체가 더 부실한 상태입니다. 하체 운동을 고려하세요.")
            elif shoulder_height > hip_height:
                analysis_results.append("상체가 상대적으로 더 두드러진 상태입니다. 상체 운동을 고려하세요.")
            else:
                analysis_results.append("상체와 하체의 비율이 적절합니다.")

            # 자세 분석
            if abs(left_shoulder.y - left_hip.y) > 0.1 or abs(right_shoulder.y - right_hip.y) > 0.1:
                analysis_results.append("자세가 비정상적입니다. 올바른 자세를 유지하기 위한 운동이나 스트레칭을 추천합니다.")
            else:
                analysis_results.append("자세가 올바릅니다.")

            # 체지방 분포 분석
            waist_height = (left_hip.y + right_hip.y) / 2
            knee_height = (left_knee.y + right_knee.y) / 2
            if waist_height < knee_height:
                analysis_results.append("복부 비만이 두드러질 수 있습니다. 복부 운동을 고려하세요.")
            else:
                analysis_results.append("체지방 분포가 적절합니다.")

            # 결과 이미지 경로 설정
            relative_image_path = f"/static/uploads/{image_src}"

            # 결과 보여주기
            return render_template('analysis_result.html', results=analysis_results, image_path=relative_image_path)

        return "신체 관절을 찾을 수 없습니다."
    
    return "이미지를 찾을 수 없습니다."




# 운동 추천 방식 선택 페이지
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # 사용자가 선택한 운동 추천 방식
        recommendation_type = request.form.get("recommendation_type")
        if recommendation_type == "direct":
            return redirect(url_for('direct_recommendation'))
        elif recommendation_type == "mbti":
            return redirect(url_for('mbti_test'))
        elif recommendation_type == "calorie":
            return redirect(url_for('select_food'))

    return render_template("index.html")

# 직접 추천 페이지/ 랜덤 추천
@app.route("/direct_recommendation", methods=["GET", "POST"])
def direct_recommendation():
    # 미리 정의된 동영상 목록
    videos = [
        ["https://img.youtube.com/vi/iOSYLKBk894/0.jpg", "운동 1", "https://youtu.be/iOSYLKBk894?si=GdgNEILwk0Kt-PoX"],
        ["https://img.youtube.com/vi/VNQpP6C1fJg/0.jpg", "운동 2", "https://youtu.be/VNQpP6C1fJg?si=0dzq9m5y1l0fQvn5"],
        ["https://img.youtube.com/vi/2Uv1B3kjCOI/0.jpg", "운동 3", "https://youtu.be/2Uv1B3kjCOI?si=mPy4Hd-8Ioe1AoFR"],
        ["https://img.youtube.com/vi/lKwZ2DU4P-A/0.jpg", "운동 4", "https://youtu.be/lKwZ2DU4P-A?si=Qp02bs_zwFlf4LsQ"],
        ["https://img.youtube.com/vi/NDsjmxTROEo/0.jpg", "운동 5", "https://youtu.be/NDsjmxTROEo?si=S7dim0DkBQQuktEU"],
        ["https://img.youtube.com/vi/gMaB-fG4u4g/0.jpg", "운동 6", "https://youtu.be/gMaB-fG4u4g?si=dW37R4NSwavoWvi1"],
        ["https://img.youtube.com/vi/ZW1pnq0b8Hs/0.jpg", "운동 7",  "https://youtu.be/ZW1pnq0b8Hs?si=1vpM_lhv4DH_IGoG"],
        ["https://img.youtube.com/vi/1uJV1ZmzeoI/0.jpg", "운동 8", "https://youtu.be/1uJV1ZmzeoI?si=gAlHHB2E-u36zuM4"],
        ["https://img.youtube.com/vi/swRNeYw1JkY/0.jpg", "운동 9", "https://youtu.be/swRNeYw1JkY?si=4Y_MXPYZPpvBq0G7"],
        ["https://img.youtube.com/vi/UYHfk45Yi2c/0.jpg", "운동 10", "https://youtu.be/UYHfk45Yi2c?si=WlLVNhtO4fo8X4-a"],
        ["https://img.youtube.com/vi/dJXZRZvqbYg/0.jpg", "운동 11", "https://youtu.be/dJXZRZvqbYg?si=MMjvnOKtleMgv5mF"],
        ["https://img.youtube.com/vi/nOGT4lXlSHw/0.jpg", "운동 12", "https://youtu.be/nOGT4lXlSHw?si=0P0Ccia9470sD0Sn"],
        # 추가적인 동영상 추가 가능
    ]
    
    # 랜덤으로 3~4개 동영상 추천
    random_videos = random.sample(videos, 3)  # 3개의 랜덤 동영상

    # 데이터를 불러와서 카테고리 필터링 작업
    df = load_data()
    categories = {
        "대분류": df["대분류"].unique(),
        "중분류": df["중분류"].unique(),
        "소분류": df["소분류"].unique()
    }

    selected_category = request.form.get("category")
    selected_subcategory = request.form.get("subcategory")
    selected_subsubcategory = request.form.get("subsubcategory")
    result = []

    if request.method == "POST":
        if selected_category and selected_subcategory and selected_subsubcategory:
            filtered_df = df[
                (df["대분류"] == selected_category) &
                (df["중분류"] == selected_subcategory) &
                (df["소분류"] == selected_subsubcategory)
            ]
            result = [(get_youtube_thumbnail(url), title, url) for url, title in filtered_df[["동영상주소", "제목"]].values.tolist()]

    # 대분류 선택에 따른 중분류 및 소분류 필터링
    subcategories = df[df["대분류"] == selected_category]["중분류"].unique() if selected_category else []
    subsubcategories = df[df["중분류"] == selected_subcategory]["소분류"].unique() if selected_subcategory else []

    return render_template(
        "direct_recommendation.html",
        categories=categories,
        selected_category=selected_category,
        selected_subcategory=selected_subcategory,
        selected_subsubcategory=selected_subsubcategory,
        result=result,
        subcategories=subcategories,
        subsubcategories=subsubcategories,
        random_videos=random_videos  # 랜덤 추천 동영상도 전달
    )

# MBTI 검사 페이지
@app.route("/mbti_test", methods=["GET", "POST"])
def mbti_test():
    questions = [
        {"question": "빠르게 움직이며 에너지를 발산하는 운동을 즐기시나요?", "key": "question_1"},
        {"question": "혼자서 운동할 때, 나만의 시간을 보내는 것이 편안한가요?", "key": "question_2"},
        {"question": "다른 사람들과 협력하며 목표를 함께 이루는 운동을 선호하나요?", "key": "question_3"},
        {"question": "실외에서 운동하는것이 좋으신가요?", "key": "question_4"}
    ]

    if request.method == "POST":
        answers = {key: request.form.get(key) for key in ['question_1', 'question_2', 'question_3', 'question_4']}
        mbti_type = determine_mbti_type(answers)
        sport_types = get_sport_types(mbti_type)

        return render_template("mbti_sport_type.html", sport_types=sport_types, mbti_type=mbti_type)

    return render_template("mbti_test.html", questions=questions)

# MBTI 유형을 계산하는 함수
def determine_mbti_type(answers):
    if answers["question_1"] == "yes" and answers["question_2"] == "no" and answers["question_4"] == "yes":  # 팀 활동 실외
        return "활동적인 팀 플레이어"
    elif answers["question_1"] == "yes" and answers["question_2"] == "no" and answers["question_4"] == "no":  # 팀 활동 실내
        return "실내 전략가"
    elif answers["question_1"] == "yes" and answers["question_2"] == "yes" and answers["question_4"] == "no":  # 혼자 활동 실내
        return "활동적인 개인플레이어"
    elif answers["question_1"] == "yes" and answers["question_2"] == "yes" and answers["question_4"] == "yes":  # 혼자 활동 실외
        return "자유로운 영혼"
    elif answers["question_1"] == "no" and answers["question_2"] == "yes" and answers["question_4"] == "no":  # 혼자 활동 실내
        return "평화로운 독주자"
    elif answers["question_1"] == "no" and answers["question_2"] == "no" and answers["question_4"] == "no":  # 팀 활동 실내
        return "협력의 마스터"
    elif answers["question_1"] == "no" and answers["question_2"] == "no" and answers["question_4"] == "yes":  # 혼자 활동 실외
        return "자연을 사랑하는 독립적 탐험가"
    else:
        return "모험을 함께하는 팀"  # 팀 활동 실외

# MBTI 유형에 따른 운동 종류 선택
def get_sport_types(mbti_type):
    df = load_data_mbti()  # 데이터프레임 로딩
    
    # 각 MBTI 유형에 따른 운동 종류 예시
    if mbti_type == "활동적인 팀 플레이어":
        sport_types_df = df[
            df["PROGRM_TY_NM"].str.contains("축구|야구|티볼") |
            df["PROGRM_NM"].str.contains("축구|야구|티볼")
        ]
    elif mbti_type == "실내 전략가":
        sport_types_df = df[
            df["PROGRM_TY_NM"].str.contains("배드민턴|농구|풋살|줌바|로빅|태권도") |
            df["PROGRM_NM"].str.contains("배드민턴|농구|풋살|줌바|로빅|태권도")
        ]
    elif mbti_type == "활동적인 개인플레이어":
        sport_types_df = df[
            df["PROGRM_TY_NM"].str.contains("수영|검도|복싱|스쿼시|핏밸런스|피겨|스피닝") |
            df["PROGRM_NM"].str.contains("수영|검도|복싱|스쿼시|핏밸런스|피겨|스피닝")
        ]
    elif mbti_type == "자유로운 영혼":
        sport_types_df = df[
            df["PROGRM_TY_NM"].str.contains("인라인|줄넘기") |
            df["PROGRM_NM"].str.contains("인라인|줄넘기")
        ]
    elif mbti_type == "평화로운 독주자":
        sport_types_df = df[
            df["PROGRM_TY_NM"].str.contains("헬스|발레|건강|자세|마사지|피아노|바둑|볼링") |
            df["PROGRM_NM"].str.contains("헬스|발레|건강|자세|마사지|피아노|바둑|볼링")
        ]
    elif mbti_type == "협력의 마스터":
        sport_types_df = df[
            df["PROGRM_TY_NM"].str.contains("요가|필라테스|볼링") |
            df["PROGRM_NM"].str.contains("요가|필라테스|볼링")
        ]
    elif mbti_type == "자연을 사랑하는 독립적 탐험가":
        sport_types_df = df[
            df["PROGRM_TY_NM"].str.contains("드론") |
            df["PROGRM_NM"].str.contains("드론")
        ]
    else:  # "팀 활동하는 실외"
        sport_types_df = df[
            df["PROGRM_TY_NM"].str.contains("골프|조깅") |
            df["PROGRM_NM"].str.contains("골프|조깅")
        ]
    
    return sport_types_df

if __name__ == "__main__":
    drop_photo_records_table()  # 기존 테이블 삭제
    init_user_db()  # 사용자 데이터베이스 초기화
    app.run(debug=True)
