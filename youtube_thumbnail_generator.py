import csv
from urllib.parse import urlparse, parse_qs

# 유튜브 URL에서 비디오 ID 추출하는 함수
def get_video_id(url):
    parsed_url = urlparse(url)
    if parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
        video_id = parse_qs(parsed_url.query).get('v')
        if video_id:
            return video_id[0]
    return None

# CSV 파일 읽기 (파일 경로를 수정하세요)
def read_csv(file_name):
    workouts = []
    with open(file_name, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            workouts.append(row)
    return workouts

# 썸네일 URL 추가
def add_thumbnails(workouts):
    for workout in workouts:
        video_url = workout['동영상주소']  # CSV 파일에서 '동영상주소' 컬럼이 있어야 합니다.
        video_id = get_video_id(video_url)
        if video_id:
            workout['썸네일'] = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        else:
            workout['썸네일'] = None
    return workouts

# CSV 파일에서 데이터 읽고 썸네일 추가
workouts = read_csv(r'C:\Users\seojimin\sql\data\서울올림픽기념국민체육진흥공단_국민체력100 운동처방 동영상주소 정보_20210727.csv.csv')  # 파일 경로 수정
workouts = add_thumbnails(workouts)

# HTML 파일 생성
def create_html(workouts):
    html_content = '''
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>추천 운동</title>
        <style>
            body {
                font-family: 'Arial', sans-serif;
                background-color: #f7f7f7;
                color: #333;
                margin: 0;
                padding: 0;
            }

            h1 {
                text-align: center;
                color: #ff7f50;
                margin-top: 50px;
            }

            ul {
                list-style-type: none;
                padding: 0;
                text-align: center;
            }

            li {
                background-color: #ffffff;
                border-radius: 10px;
                padding: 15px;
                margin: 10px 0;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                max-width: 500px;
                margin-left: auto;
                margin-right: auto;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }

            li:hover {
                transform: translateY(-5px);
                box-shadow: 0 8px 12px rgba(0, 0, 0, 0.15);
            }

            strong {
                font-size: 18px;
                color: #ff6347;
            }

            a {
                display: block;
                margin-top: 10px;
                color: #64b3f4;
                text-decoration: none;
                font-size: 16px;
            }

            a:hover {
                color: #ff7f50;
            }

            .thumbnail {
                width: 100%;
                max-width: 200px;
                height: auto;
                margin-right: 15px;
                border-radius: 8px;
            }

            .video-item {
                display: flex;
                justify-content: center;
                align-items: center;
            }
        </style>
    </head>
    <body>
        <h1>추천 운동</h1>
        <ul>
    '''

    for workout in workouts:
        if workout['썸네일']:
            html_content += f'''
            <li class="video-item">
                <img class="thumbnail" src="{workout['썸네일']}" alt="썸네일">
                <div>
                    <strong>{workout['제목']}</strong><br>
                    <a href="{workout['동영상주소']}" target="_blank">영상 보기</a>
                </div>
            </li>
            '''

    html_content += '''
        </ul>
    </body>
    </html>
    '''

    # HTML 파일 저장 (recommend.html로 저장)
    with open('recommend.html', 'w', encoding='utf-8') as file:
        file.write(html_content)

# HTML 파일 생성
create_html(workouts)
