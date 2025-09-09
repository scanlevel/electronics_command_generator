from pathlib import Path
import subprocess
import os

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

# 기준 디렉토리: main.py가 있는 위치
BASE_DIR = Path(__file__).resolve().parent

# 환경 변수 설정: PYTHONPATH를 BASE_DIR로 설정
env = os.environ.copy()
env["PYTHONPATH"] = str(BASE_DIR)

# 실행할 파일 경로 설정
generate_command_path = BASE_DIR / "generator" / "generate_commands.py"
cluster_by_class_path = BASE_DIR / "generator" / "cluster_by_class.py"
tag_valid_test_path = BASE_DIR / "generator" / "tag_valid_test.py"
wochan_cluster_path = BASE_DIR / "generator" / "cluster_by_device_name.py"

FILE_MODE_LIST = ["종료",generate_command_path,cluster_by_class_path,tag_valid_test_path,wochan_cluster_path]

if __name__ == "__main__":
    
    # 터미널 클리어
    clear_terminal()
    print("실행시킬 파일을 선택하세요:")
    for idx,file_path in enumerate(FILE_MODE_LIST):
        file_name = str(file_path).split('/')[-1]
        print(f'{idx}. {file_name}')
        
    try:
        FILE_MODE = int(input("번호 입력 (0~4): "))
    except ValueError:
        print("숫자를 입력해야 합니다.")
        exit(1)
    if FILE_MODE == 0:
        print("프로그램을 종료합니다")
        exit(0)
    elif 1 <= FILE_MODE <= len(FILE_MODE_LIST):
        target_path = FILE_MODE_LIST[FILE_MODE]
    else:
        print("잘못된 번호입니다.")
        exit(1)
    
    # subprocess 실행 (str로 변환 필요)
    clear_terminal()
    result = subprocess.run(["python", str(target_path)], env=env)

    print(f"\n[종료 코드]: {result.returncode}")
