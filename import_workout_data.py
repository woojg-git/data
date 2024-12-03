import pandas as pd

# 운동 데이터를 CSV 파일에서 불러오는 함수
def get_workout_data():
    # CSV 파일의 경로
    file_path = r"C:\Users\seojimin\sql\서울올림픽기념국민체육진흥공단_국민체력100 운동처방 동영상주소 정보_20210727.csv"
    
    # 다른 인코딩 방식으로 파일 읽기
    try:
        df = pd.read_csv(file_path, encoding='ISO-8859-1')  # 'ISO-8859-1' 인코딩 시도
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding='cp949')  # 'cp949' 인코딩 시도 (주로 한국어 파일에 사용)
    
    # 데이터 확인 (디버깅용)
    print(df.head())  # 데이터의 첫 5행 출력
    
    return df
