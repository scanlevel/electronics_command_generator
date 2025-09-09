import json
from pathlib import Path
from collections import defaultdict


from kiwipiepy import Kiwi
from verb_generator.korean_lemmatizer.soylemma import Lemmatizer
from verb_generator.conjugator import KConjugator
from verb_generator.config_verb import config_options


# 초기화
kiwi = Kiwi(model_type='sbg')
kiwi.load_user_dictionary("./verb_generator/user_dict.txt")
lemmatizer = Lemmatizer()
conjugation_cache = {}  # 메모이제이션 캐시

# 동사 어미 선택
def choose_eomi(stem):
    if stem == "하":
        return "어"
    last_char = stem[-1]
    base = ord(last_char) - 0xAC00
    jungseong_index = (base // 28) % 21
    jung_list = ["ㅏ", "ㅐ", "ㅑ", "ㅒ", "ㅓ", "ㅔ", "ㅕ", "ㅖ",
                 "ㅗ", "ㅘ", "ㅙ", "ㅚ", "ㅛ", "ㅜ", "ㅝ", "ㅞ", "ㅟ",
                 "ㅠ", "ㅡ", "ㅢ", "ㅣ"]
    last_vowel = jung_list[jungseong_index]
    return "아" if last_vowel in ["ㅏ", "ㅗ"] else "어"


# 동사 기반 보조용언 조합 생성 (VV)
def generate_vv_combinations(verb_stem):
    results = set()
    results.add(verb_stem)
    eomi = choose_eomi(verb_stem)

    #기본형 + 보조사 추가
    stem_aux1 = [config_options["aux1"]["options"][i] for i in user_input["aux1"]]
    stem_aux2 = [config_options["aux2"]["options"][i] for i in user_input["aux2"]]
    
    try:
        # Kiwi join으로 어간 + 어미 결합
        conj = kiwi.join([(verb_stem, 'VV'), (eomi, 'EF')])
    except:
        conj = verb_stem + eomi
    
    for aux in stem_aux1 + stem_aux2:
        if not aux:  # 빈 문자열 "", 빈 리스트 [], None 등 모두 걸러짐
            continue
        results.add(f"{conj}{aux}")


    # ex_stem + 보조사 추가
    stem_exstem = config_options["ex_stem"]["options"][user_input["ex_stem"]] 

    for suffix2 in stem_exstem: # -도록, -게
        try:
            subord = kiwi.join([(verb_stem, 'VV'), (suffix2, 'EC')])
            basic = subord + " 하"
        except:
            subord = verb_stem + suffix2
            basic = subord + " 하"
            
        results.add(basic)
        
        eomi = choose_eomi('하')
        conj = kiwi.join([('하', 'VX'), (eomi, 'EF')])
        append = subord + " "+conj

        for aux in stem_aux1 + stem_aux2:
            if not aux:  # 빈 문자열 "", 빈 리스트 [], None 등 모두 걸러짐
                continue
            results.add(f"{append}{aux}")
    
    return sorted(results)

# 명사 기반 조합 생성 (NNG)
def generate_partial_conjugations(noun):
    
    stem_options = config_options["stem_type"]["options"][user_input["stem_type"]] 
    stem_aux1 = [config_options["aux1"]["options"][i] for i in user_input["aux1"]]
    stem_aux2 = [config_options["aux2"]["options"][i] for i in user_input["aux2"]]
   
    
    results = set()
    for suffix in stem_options:  # -하-, -시키-
        results.add(f"{noun}{suffix}")
        
        ###### 보조사 1,2 추가 ######
        eomi = choose_eomi(suffix)  
        conj = kiwi.join([(suffix, 'VV'), (eomi, 'EF')])  
        
        for aux in stem_aux1 + stem_aux2:
            if not aux:  # 빈 문자열 "", 빈 리스트 [], None 등 모두 걸러짐
                continue
            results.add(f"{noun}{conj}{aux}")
    
        
    stem_exstem = config_options["ex_stem"]["options"][user_input["ex_stem"]] 

    for suffix in stem_options:  
        for suffix2 in stem_exstem: # -도록, -게
            results.add(f"{noun}{suffix}{suffix2}" + " 하")
       
            ###### 보조사 1,2 추가 ###### 
            eomi = choose_eomi('하')  
            conj = kiwi.join([('하', 'VX'), (eomi, 'EF')])  

            
            append = f"{noun}{suffix}{suffix2} "+conj  
            for aux in stem_aux1 + stem_aux2:
                if not aux:  # 빈 문자열 "", 빈 리스트 [], None 등 모두 걸러짐
                    continue
                results.add(append + aux)

    return sorted(results)


# 놓 축약 후처리
def shrink_nota_phrase(text):
    text = text.replace('놓아', '놔')
    text = text.replace('놓아요', '놔요')
    text = text.replace('놓아라', '놔라')
    text = text.replace('놓아서', '놔서')
    text = text.replace('놓았', '놨')
    text = text.replace('놓을래', '놀래')
    return text


# 활용형 생성
def collect_conjugated_verbs(verb_stem):
    # 0) 캐시 확인
    if verb_stem in conjugation_cache:
        return conjugation_cache[verb_stem]

    kc = KConjugator(verb_stem)
    result_set = set()

    # 1) 인덱스→상수 매핑
    mode_map = {
        1: kc.M_DECLARATIVE,   # 평서문
        2: kc.M_IMPERATIVE,    # 명령문
        3: kc.M_PROPOSITIVE,   # 청유문
        4: kc.M_ADJECTIVAL     # 관형사형
    }
    tense_map = {
        1: kc.T_PRESENT,       # 현재
        2: kc.T_FUTURE         # 미래
    }
    formality_map = {
        1: kc.F_INFORMAL,      # 비격식
        2: kc.F_FORMAL         # 격식
    }
    honorific_map = {
        1: kc.H_LOW,           # 낮춤
        2: kc.H_HIGH           # 높임
    }

    # 2) 허용할 인덱스 조합 (mode, tense, formality, honorific)
    #    관형사형은 honorific 구분이 없으므로 None 처리
    ALLOWED_IDX = [
        (1,1,1,1), (1,1,1,2),               # 평서문·현재·비격식·낮춤/높임
        (2,1,1,1), (2,1,1,2),               # 명령문·현재·비격식·낮춤/높임
        (2,1,2,1), (2,1,2,2),               # 명령문·현재·격식·낮춤/높임
        (3,1,2,1), (3,1,2,2),               # 청유문·현재·격식·낮춤/높임
        (4,2,1,None), (4,2,2,None),         # 관형사형·미래·비격식/격식
    ]

    # 3) 사용자 선택값 가져오기 (없으면 “전체 허용 인덱스” 기준으로)
    sel_m = set(user_input.get("sentence_type") or [m for m,_,_,_ in ALLOWED_IDX])
    sel_t = set(user_input.get("tense")         or [t for _,t,_,_ in ALLOWED_IDX])
    sel_f = set(user_input.get("formality")     or [f for _,_,f,_ in ALLOWED_IDX])
    # honorific은 None 은 항상 허용
    raw_h = user_input.get("honorific")
    if raw_h:
        sel_h = set(raw_h)
    else:
        sel_h = {h for *_,h in ALLOWED_IDX if h is not None}

    # 4) 허용 조합 필터링
    filtered = []
    for m_idx, t_idx, f_idx, h_idx in ALLOWED_IDX:
        if m_idx not in sel_m:      continue
        if t_idx not in sel_t:      continue
        if f_idx not in sel_f:      continue
        # honorific None은 무시, 아니면 선택값에 포함돼야 함
        if h_idx is not None and h_idx not in sel_h:
            continue
        filtered.append((m_idx, t_idx, f_idx, h_idx))

    # 5) 실제 conjugate 호출
    for m_idx, t_idx, f_idx, h_idx in filtered:
        m = mode_map[m_idx]
        t = tense_map[t_idx]
        f = formality_map[f_idx]
        # honorific None 은 0 으로
        h = honorific_map[h_idx] if h_idx else 0

        try:
            out = kc.conjugate(m, t, f, h)
            result_set.add(shrink_nota_phrase(out))
        except Exception:
            continue

    conjugation_cache[verb_stem] = result_set
    return result_set



def collect_question_verbs(verb_stem):
    if verb_stem in conjugation_cache:
        return conjugation_cache[verb_stem]

    kc = KConjugator(verb_stem)
    result_set = set()

    # 기존: 과거/대과거 조합
    for t in [kc.T_PAST, kc.T_PLUPERFECT]:
        for f in [kc.F_INFORMAL, kc.F_FORMAL]:
            for h in [kc.H_LOW, kc.H_HIGH]:
                res = kc.conjugate(kc.M_INQUISITIVE, t, f, h)
                result_set.add(shrink_nota_phrase(res))

    for h in [kc.H_LOW, kc.H_HIGH]:
        res = kc.conjugate(kc.M_INQUISITIVE, kc.T_PRESENT, kc.F_FORMAL, h)
        result_set.add(shrink_nota_phrase(res))

    conjugation_cache[verb_stem] = result_set
    return result_set


def run_root_append_pipeline(verb_list , 
                 input_config ={
                            "stem_type": 3,
                            "ex_stem": 3,
                            "aux1": list(range(1, 6)),
                            "aux2": list(range(1, 7)),
                            "sentence_type": [1, 2, 3, 4],
                            "honorific": [1,2],
                            "formality": [1,2],  
                            "tense": [1,2]          
                        }
):
    global user_input 
    user_input = input_config
    
    final_result = {}
    question = -1
    
    for sentence in verb_list if isinstance(verb_list, list) else [verb_list]:
        li = sentence.strip().split()
        if not li:
            continue
        
        last_word = li[-1]
        tokens = kiwi.tokenize(last_word)
        
        suffixes = ["야", "니", "냐", "예요", "입니까", "였어", "였습니까"]

        if tokens[-1].tag == "SF":
            question = 1
            toeken_all = kiwi.tokenize(sentence)
            
            if any(tok.form in ["얼마", "도", "퍼", "퍼센트", '상황', '정도', '언제'] for tok in toeken_all):
                # 문장 전체에서 SF 포함 이전 어절을 분석
                base = sentence.rstrip("?!.").strip()

                # 어미 제거 (야, 니, ... 등)
                for sfx in suffixes:
                    if base.endswith(sfx):
                        prefix = base[: -len(sfx)]
                        break
                else:
                    prefix = base  # 어미 없으면 그대로 사용

                combined = [prefix + suf for suf in suffixes]
                final_result[sentence] = combined
                return final_result
 
        """
        NNG: 일반 명사

        VV: 동사 어간
        
        VV-I : 불규칙일때

        VV-R: 동사 활용형의 결합형(예: ‘하-’처럼 보조동사 어간)

        VA: 형용사

        VA-I: 형용사 불규칙형(일부 분석기에서 나타남)
        """
        
        
            
        
        roots = {"NNG": [], "VV": []}
        
        if tokens[0].tag in ["NNG", "VV", "VV-R", "VA-I", "VA","VX", "VV-I", "MAG", "XSV"]:
            if tokens[0].tag == "VV-R" or tokens[0].tag == "VX" or tokens[0].tag == "VV-I" or tokens[0].tag == 'XSV':
                roots["VV"].append(tokens[0].form)
            elif tokens[0].tag in ["VA-I", "VA", "MAG"]:
                if(tokens[0].form == "어떻"):
                    roots["VV"].append(tokens[0].form )
                else:
                    step1 = kiwi.join([(tokens[0].form, tokens[0].tag), ('하', 'XSV')])
                    roots["VV"].append(step1)
            else:
                roots[tokens[0].tag].append(tokens[0].form)

        if not roots["NNG"] and not roots["VV"]:
            continue
        else:
            output = build_output_from_roots(roots, question)
        
        prefix = " ".join(li[:-1])
        combined = []
        for stem, forms in output.items():
            for v in forms:
                full = f"{prefix} {v}" if prefix else v
                combined.append(full)
                # print(f"- {full}")

        final_result[sentence] = combined
    return final_result





def run_root_pipeline(verb_list , 
                 input_config ={
                            "stem_type": 3,
                            "ex_stem": 3,
                            "aux1": list(range(1, 6)),
                            "aux2": list(range(1, 7)),
                            "sentence_type": [1, 2, 3, 4],
                            "honorific": [1,2],
                            "formality": [1,2],  
                            "tense": [1,2]          
                        }
):
    global user_input 
    user_input = input_config
    
    final_result = {}
    question = -1
    
    for sentence in verb_list if isinstance(verb_list, list) else [verb_list]:
        li = sentence.strip().split()
        if not li:
            continue
        
        last_word = li[-1]
        tokens = kiwi.tokenize(last_word)
        
        suffixes = ["야", "니", "냐", "예요", "입니까", "였어", "였습니까"]

        if tokens[-1].tag == "SF":
            question = 1
            toeken_all = kiwi.tokenize(sentence)
            
            if any(tok.form in ["얼마", "도", "퍼", "퍼센트", '상황', '정도', '언제'] for tok in toeken_all):
                # 문장 전체에서 SF 포함 이전 어절을 분석
                base = sentence.rstrip("?!.").strip()

                # 어미 제거 (야, 니, ... 등)
                for sfx in suffixes:
                    if base.endswith(sfx):
                        prefix = base[: -len(sfx)]
                        break
                else:
                    prefix = base  # 어미 없으면 그대로 사용

                combined = [prefix + suf for suf in suffixes]
                final_result[sentence] = combined
                return final_result
 
        """
        NNG: 일반 명사

        VV: 동사 어간
        
        VV-I : 불규칙일때

        VV-R: 동사 활용형의 결합형(예: ‘하-’처럼 보조동사 어간)

        VA: 형용사

        VA-I: 형용사 불규칙형(일부 분석기에서 나타남)
        """
        
        
            
        
        roots = {"NNG": [], "VV": []}
        
        if tokens[0].tag in ["NNG", "VV", "VV-R", "VA-I", "VA","VX", "VV-I", "MAG", "XSV"]:
            if tokens[0].tag == "VV-R" or tokens[0].tag == "VX" or tokens[0].tag == "VV-I" or tokens[0].tag == 'XSV':
                roots["VV"].append(tokens[0].form)
            elif tokens[0].tag in ["VA-I", "VA", "MAG"]:
                if(tokens[0].form == "어떻"):
                    roots["VV"].append(tokens[0].form )
                else:
                    step1 = kiwi.join([(tokens[0].form, tokens[0].tag), ('하', 'XSV')])
                    roots["VV"].append(step1)
            else:
                roots[tokens[0].tag].append(tokens[0].form)

        if not roots["NNG"] and not roots["VV"]:
            continue
        else:
            final_result[sentence] = roots["VV"]
            final_result[sentence] = roots["NNG"]
            
        
    return final_result



def build_output_from_roots(roots, question=-1):
    """
    NNG와 VV 루트를 기반으로 활용형 후보를 생성하고 반환하는 함수

    Parameters:
        roots (dict): {"NNG": [...], "VV": [...]}
        question (int): 의문문 여부 (1이면 의문문 활용형 생성)

    Returns:
        dict: {root: [활용형 리스트]}
    """
    output = {}

    if question == 1:
        # 의문문일 경우: root 자체에 대해 활용형 생성
        for key in ("NNG", "VV"):
            for root in roots.get(key, []):
                try:
                    conjugated = collect_question_verbs(root)
                    output[root] = sorted(conjugated)
                except Exception as e:
                    print(f"{root}: 오류 발생 - {e}")
        return output

    # 일반 평서문/명령문/청유문 등 처리용
    def process(root_list, generator_fn):
        for root in root_list:
            candidates = generator_fn(root)
            output[root] = sorted(candidates)

    # NNG 처리
    process(roots.get("NNG", []), generate_partial_conjugations)

    # VV 처리
    process(roots.get("VV", []), generate_vv_combinations)

    return output


def load_json(path: Path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_roots_with_pipeline(device_data, action_data, root_func, common_threshold=20):
    device_root_map = defaultdict(set)
    root_to_devices = defaultdict(set)

    for device_name, action_classes in device_data.items():
        for action_class, actions in action_classes.items():
            for action_name in actions:
                try:
                    verb_list = action_data[action_class][action_name]['Verb']
                except KeyError:
                    continue

                for verb in verb_list:
                    root_result = root_func(verb)  # 예: {"켜다": ["켜", ...]}
                    for _, roots in root_result.items():
                        for root in roots:
                            if not root:
                                continue
                            device_root_map[device_name].add(root)
                            root_to_devices[root].add(device_name)

    common_roots = {r for r, devs in root_to_devices.items() if len(devs) >= common_threshold}

    result = {"common": sorted(common_roots)}
    for device, roots in device_root_map.items():
        unique_roots = sorted(roots - common_roots)
        if unique_roots:
            result[device] = unique_roots

    return result

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 실행
if __name__ == "__main__":
    DEVICE_PATH = Path("data/FINAL_DEVICE.json")
    ACTION_PATH = Path("data/FINAL_ACTION.json")

    device_data = load_json(DEVICE_PATH)
    action_data = load_json(ACTION_PATH)

    # 기본 root 추출 결과
    basic_result = extract_roots_with_pipeline(device_data, action_data, run_root_pipeline, common_threshold=20)
    save_json(basic_result, Path("result/device_verb_basic.json"))

    # 확장된 root 후보 포함 결과
    extended_result = extract_roots_with_pipeline(device_data, action_data, run_root_append_pipeline, common_threshold=20)
    save_json(extended_result, Path("result/device_verb_extended.json"))
