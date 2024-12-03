import pandas as pd

def load_and_split_data(file_path):
    try:
        file_path = r"C:\Users\seojimin\sql\서울올림픽기념국민체육진흥공단_국민체력100 운동처방 동영상주소 정보_20210727.csv"
        df = pd.read_csv(file_path, encoding='utf-8')  # 적절한 인코딩 설정
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding='cp949')  # 다른 인코딩 시도
    
    # 열 이름 강제 수정 (깨진 경우)
    df.columns = ['번호', '대분류', '중분류', '소분류', '제목', '동영상주소']
    
    # '대분류'로 데이터 나누기
    if '대분류' in df.columns:
        grouped_data = {category: group for category, group in df.groupby('대분류')}
        return grouped_data
    else:
        raise KeyError("'대분류' 열이 CSV 파일에 존재하지 않습니다.")
