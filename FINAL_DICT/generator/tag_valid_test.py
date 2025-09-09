import json
from pathlib import Path

# 경로 설정
ACTION_PATH = Path("data/FINAL_ACTION.json")
DEVICE_PATH = Path("data/FINAL_DEVICE.json")

def load_json(path: Path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data: dict, path: Path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

print("태그 오류 검출 및 수정 시작")

# 데이터 불러오기
action_data = load_json(ACTION_PATH)
device_data = load_json(DEVICE_PATH)

invalid_mappings = []
fixed_count = 0

# Step-by-step 구조 순회 및 수정
for device_name, class_dict in device_data.items():
    for class_name, actions in class_dict.items():
        for action_key in actions:
            if class_name not in action_data or action_key not in action_data[class_name]:
                invalid_mappings.append({
                    "device": device_name,
                    "class": class_name,
                    "action": action_key,
                    "error": "Action not defined in action_data"
                })
                continue

            tag_list = action_data[class_name][action_key].get("Tag", [])
            if device_name not in tag_list:
                # 태그 누락: 자동 추가
                action_data[class_name][action_key].setdefault("Tag", []).append(device_name)
                fixed_count += 1
                invalid_mappings.append({
                    "device": device_name,
                    "class": class_name,
                    "action": action_key,
                    "error": f"[Fixed] Added missing tag '{device_name}' to action's Tag"
                })

# 결과 출력
for item in invalid_mappings:
    print(f"[오류] Device: {item['device']} / Class: {item['class']} / Action: {item['action']} → {item['error']}")

# 수정된 action_data 저장
save_json(action_data, ACTION_PATH)
print(f"\n누락된 태그 자동 추가 완료: {fixed_count}개 수정됨.")
