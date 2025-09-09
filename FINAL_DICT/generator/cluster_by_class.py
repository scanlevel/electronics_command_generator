import json
from itertools import product
from pathlib import Path
from pyjosa.josa import Josa
from verb_generator.action_conjun import run_pipeline
from functools import lru_cache
import time
import sys
import traceback 
from collections import Counter

def load_json(path : Path):
    with open(path, 'r', encoding = 'utf-8') as f:
        return json.load(f)
    
############## korean common prefix ###############
CHO = [chr(c) for c in range(0x1100, 0x1113)]
JUNG = [chr(c) for c in range(0x1161, 0x1176)]
JONG = [""] + [chr(c) for c in range(0x11A8, 0x11C3)]
CHOSUNG_COMPAT = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']

# 예: 'ᄂ' -> 'ㄴ'
def to_compat_chosung(cho):
    if cho in CHO:
        return CHOSUNG_COMPAT[CHO.index(cho)]
    raise ValueError(f"{cho} 는 초성이 아닙니다.")

def decompose(ch):
    code = ord(ch)
    if 0xAC00 <= code <= 0xD7A3:
        code -= 0xAC00
        cho = CHO[code // (21 * 28)]
        jung = JUNG[(code % (21 * 28)) // 28]
        jong = JONG[code % 28]
        return (cho, jung, jong)
    else:
        return (ch,)  # 한글 아님

def decompose_string(s):
    return [decompose(ch) for ch in s]

def compose(cho, jung, jong=""):
    cho_i = CHO.index(cho)
    jung_i = JUNG.index(jung)
    jong_i = JONG.index(jong) if jong else 0
    code = 0xAC00 + (cho_i * 21 * 28) + (jung_i * 28) + jong_i
    return chr(code)

def common_prefix_by_jamos_flexible(strings):
    if not strings:
        return ""
    
    decomposed_list = [decompose_string(s) for s in strings]
    min_len = min(len(d) for d in decomposed_list)

    result = ""

    for i in range(min_len):
        units = [d[i] for d in decomposed_list]
        if all(len(u) == 3 for u in units):
            cho_set = set(u[0] for u in units)
            jung_set = set(u[1] for u in units)
            jong_set = set(u[2] for u in units)

            if len(cho_set) == 1 and len(jung_set) == 1 and len(jong_set) == 1:
                # 초중종 다 같음 → 완전한 글자
                result += compose(units[0][0], units[0][1], units[0][2])
            elif len(cho_set) == 1 and len(jung_set) == 1:
                # 초+중만 같음 → 조합 후 멈춤
                result += compose(units[0][0], units[0][1])
                break
            elif len(cho_set) == 1:
                # 초성만 같음 → 초성 문자만 추가
                # ㄱ~ㅎ 유니코드 범위 내 자음 추출
                chosung = units[0][0]
                chosung_char = to_compat_chosung(chosung)
                result += chosung_char
                break
            else:
                break
        elif all(u == units[0] for u in units):
            # ✅ 한글 아닌 공백이나 문장부호도 일치할 경우 결과에 추가
            result += units[0][0]
        else:
            break  # 비한글 또는 길이 다른 경우

    return result
    
############## korean common prefix ###############



ACTION_PATH = Path('data/FINAL_ACTION.json')
CONFIG_PATH = Path('data/USER_CONFIG.json')
action_data = load_json(ACTION_PATH)
user_config = load_json(CONFIG_PATH)

@lru_cache(maxsize=100000)
def cached_run_pipeline(vvv):
    return run_pipeline(vvv,user_config)


TOP_COUNT = input("빈출 단어를 최대 몇 개 뽑을 지 입력하세요\n")
if not TOP_COUNT.isdigit():
    print("오류 발생, 기본값 5개만 뽑습니다")
    TOP_COUNT = 5

print("ACTION 분류 기준 빈출 어근 검색 시작")
verb_dictionary = {}
def make_verb_dictionary():
    global verb_dictionary
    verb_dictionary['']=[]
    for _, actions in action_data.items():
        for __, action in actions.items():
            for vvv in action["Verb"]:
                if vvv:
                    verb_dictionary.update(cached_run_pipeline(vvv))
                    
Action_Class_Dict = {}
Final_Action_Dict = {}
for action_class,actions in action_data.items():
    Action_Class_Dict[action_class] = []
    Final_Action_Dict[action_class] = []
    for action, property in actions.items():
        Action_Class_Dict[action_class].extend(property["Verb"] * len(property["Tag"]))
    for idx, keyword in enumerate(Action_Class_Dict[action_class]):
        Action_Class_Dict[action_class][idx] = cached_run_pipeline(keyword)
    for keyword_conjugation_dict in Action_Class_Dict[action_class]:
        common_prefix = ""
        for keyword, conjugation in keyword_conjugation_dict.items():
            common_prefix = common_prefix_by_jamos_flexible(conjugation)
        
        Final_Action_Dict[action_class].append(common_prefix)
    action_class_count = Counter(Final_Action_Dict[action_class])
    # 넉넉히 뽑아두고 공백 아닌 것 상위 몇 개 추려냄
    top_verbs = []
    for prefix, count in action_class_count.most_common(20):
        if prefix.strip():
            top_verbs.append((prefix, count))
        if len(top_verbs) == TOP_COUNT:
            break
    Final_Action_Dict[action_class] = top_verbs


# converted_json = {
#     action_class: {prefix: count for prefix, count in top_verbs}
#     for action_class, top_verbs in Final_Action_Dict.items()
# }

# with open("result/prefix_summary.json", "w", encoding="utf-8") as f:
#     json.dump(converted_json, f, indent=2, ensure_ascii=False)

# print(json.dumps(converted_json, indent=2, ensure_ascii=False))
print("생성 완료")
print("출력 모드를 선택하세요:")
print("1: 접두사별 빈도만 출력")
print("2: 접두사별 빈도 + 태그(Tag) 포함 출력")
MODE = input("선택 (1/2): ").strip()

converted_json = {}

for action_class, prefix_list in Final_Action_Dict.items():
    if MODE == "1":
        converted_json[action_class] = {
            prefix: count for prefix, count in prefix_list if prefix.strip()
        }
    elif MODE == "2":
        prefix_map = {}
        for prefix, count in prefix_list:
            if prefix.strip() == "":
                continue

            matched_tags = set()
            for action_name, action_info in action_data[action_class].items():
                for verb in action_info.get("Verb", []):
                    if verb.startswith(prefix):
                        matched_tags.update(action_info.get("Tag", []))
            prefix_map[prefix] = {
                "count": count,
                "tags": sorted(matched_tags)
            }
        converted_json[action_class] = prefix_map
    else:
        print("잘못된 입력입니다. 기본값(1)으로 진행합니다.")
        converted_json[action_class] = {
            prefix: count for prefix, count in prefix_list if prefix.strip()
        }


with open("result/prefix_summary.json", "w", encoding="utf-8") as f:
    json.dump(converted_json, f, indent=2, ensure_ascii=False)

print(json.dumps(converted_json, indent=2, ensure_ascii=False))
