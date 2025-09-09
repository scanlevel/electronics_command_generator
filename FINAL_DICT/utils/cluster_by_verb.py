import unicodedata
from pathlib import Path
import json
from verb_generator.action_conjun import run_pipeline

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
            # elif len(cho_set) == 1:
            #     # 초성만 같음 → 초성 문자만 추가
            #     # ㄱ~ㅎ 유니코드 범위 내 자음 추출
            #     chosung = units[0][0]
            #     chosung_char = to_compat_chosung(chosung)
            #     result += chosung_char
            #     break
            else:
                break
        elif all(u == units[0] for u in units):
            # ✅ 한글 아닌 공백이나 문장부호도 일치할 경우 결과에 추가
            result += units[0][0]
        else:
            break  # 비한글 또는 길이 다른 경우

    return result



ACTION_PATH = Path('data/FINAL_ACTION.json')
DEVICE_PATH = Path('data/FINAL_DEVICE.json')
ATTRIBUTE_PATH = Path('data/FINAL_ATTRIBUTE.json')
PARTICLE_PATH = Path('data/FINAL_PARTICLE.json')

def load_json(path : Path):
    with open(path, 'r', encoding = 'utf-8') as f:
        return json.load(f)

action_data = load_json(ACTION_PATH)
device_data = load_json(DEVICE_PATH)
attribute_data = load_json(ATTRIBUTE_PATH)
particle_data = load_json(PARTICLE_PATH)

if __name__ == "__main__":
    
    device_verbs = {}
    
    for device_name,action_classes in device_data.items():
        device_verbs[device_name] = {}
        verbs = set()
        for action_class, actions in action_classes.items():
            for action_name in actions.keys():
                verb_list = action_data[action_class][action_name]['Verb']
                verbs.update(verb_list)
        for v in verbs:
            verb_conjugated_form = run_pipeline(v)[v]
            print(type(verb_conjugated_form))
            verb_LCP = common_prefix_by_jamos_flexible(verb_conjugated_form)
            
            if verb_LCP in device_verbs[device_name]:
                device_verbs[device_name][verb_LCP].update(verb_conjugated_form)
            else:
                device_verbs[device_name][verb_LCP] = set(verb_conjugated_form)
    
    
    common_verbs = set()
    unique_verbs = []
    for device_name, verbs in device_verbs.items():
        unique_verbs.append(set(verbs.keys()))
    common_verbs = set.intersection(*unique_verbs)
            
    result = {}
    
    result['common'] = {}

    for lcp in common_verbs:
        for device_name in device_verbs:
            if lcp in device_verbs[device_name]:
                result['common'][lcp] = list(device_verbs[device_name][lcp])
                break

    for device_index, device_name in enumerate(device_verbs.keys()):
        for common_LCP in common_verbs:
            del device_verbs[device_name][common_LCP]
        result[device_name] = {
            lcp: list(verbs) for lcp, verbs in device_verbs[device_name].items()
        }
        
    
    with open('result/device_verb.json','w') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)