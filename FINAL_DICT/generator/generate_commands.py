import json
from itertools import product
from pathlib import Path
from pyjosa.josa import Josa
from verb_generator.action_conjun import run_pipeline
from functools import lru_cache
import time
import sys
import traceback
import random
from numeral_form import num2kr


ACTION_PATH = Path('data/FINAL_ACTION.json')
DEVICE_PATH = Path('data/FINAL_DEVICE.json')
ATTRIBUTE_PATH = Path('data/FINAL_ATTRIBUTE.json')
PARTICLE_PATH = Path('data/FINAL_PARTICLE.json')
ADVERB_PATH = Path('data/FINAL_ADVERB.json')
NUMBER_PATH = Path('data/FINAL_NUMBER.json')
CONFIG_PATH = Path('data/USER_CONFIG.json')
JOSA_LIST = ["을","으로","은","이가"]
AFTER_LIST = ["뒤에", "뒤","있다","있다가","후에","후"]

def load_json(path : Path):
    with open(path, 'r', encoding = 'utf-8') as f:
        return json.load(f)

action_data = load_json(ACTION_PATH)
device_data = load_json(DEVICE_PATH)
attribute_data = load_json(ATTRIBUTE_PATH)
particle_data = load_json(PARTICLE_PATH)
adverb_data = load_json(ADVERB_PATH)
number_data = load_json(NUMBER_PATH)
user_config = load_json(CONFIG_PATH)
verb_dictionary = {}

@lru_cache(maxsize=100000)
def cached_get_full_string(word, particle):
    return Josa.get_full_string(word, particle)

@lru_cache(maxsize=1000)
def num_to_kr(num):
    return num2kr.num2kr(num,1)

@lru_cache(maxsize=100000)
def cached_get_attribute_value(attribute_name,RANDOM_NUM_MODE):
    return get_attribute_value(attribute_name,attribute_data,RANDOM_NUM_MODE)

def get_attribute_value(attribute_name, attribute_data,RANDOM_NUM_MODE):
    attribute = attribute_data.get(attribute_name)
    if not attribute:
        return []
    if attribute["type"] == "Categorical":
        if "unit" in attribute:
            result = list(product(attribute['option'],attribute['unit']))
            return list(map(lambda x: "".join(x),result))
        else:
            return attribute['option']
    elif attribute['type'] == 'Numerical':
        option = attribute['option']
        result = []
        
        if RANDOM_NUM_MODE == 1:
            # attribute 참조하여 범위 숫자 생성
            for num in range(option['min'],option['max']+1,option['step']):
                for unit in option["unit"]:
                    if option['numeralType'] == "Cardinal":
                        result.append(f'{number_data["Cardinal"][str(num)]}{unit}')
                    else:
                        result.append(f'[{num_to_kr(num)}]{unit}')
                        
        elif RANDOM_NUM_MODE == 2:
            # 숫자 uniform 하게 생성하는 코드
            for unit in option["unit"]:
                if option['numeralType'] == "Cardinal":
                    # {} -> 기수
                    result.append(lambda unit=unit: number_data["Cardinal"][str(random.randint(1, 99))] + unit)
                else:
                    # [] -> 서수
                    result.append(lambda unit=unit: f'[{num_to_kr(random.choice(list(range(1,100)) + list(range(100,1001,10))))}]{unit}')
        return result
    return []

def generate_commands(device_name, device_data, action_data, attribute_data, particle_data,RANDOM_NUM_MODE):
    result = []
    device_action = device_data[device_name]
    for action_class in device_action:
        for action_name,sentences in device_action[action_class].items():
            action_in_class = action_data[action_class]
            verb = action_in_class[action_name]["Verb"]
            particle_list = action_in_class[action_name]["Particle"]
            
            attribute_combinations = []
            particle_combinations = []
            base_verbs  = verb
            
            # 명사 생성
            try:
                for sentence in sentences:
                    sentence_list = []
                    for attribute in sentence:
                        if type(attribute) == str:
                            if attribute == "":
                                sentence_list.append([""])
                            else:
                                sentence_list.append(cached_get_attribute_value(attribute,RANDOM_NUM_MODE))
                        elif type(attribute) == list:
                            temp_list = []
                            for attr in attribute:
                                if attr == "":
                                    temp_list.append([""])
                                else:
                                    temp_list.append(cached_get_attribute_value(attr,RANDOM_NUM_MODE))
                            sentence_list.append(temp_list)
                    attribute_combinations.append(sentence_list)
            except Exception as e:
                traceback.print_exc()
                print(e,"DEVICE의 ACTION에 올바른 ATTRIBUTE를 넣었는지 확인하세요")
                exit()
            
            
            # 조사 생성
            try:
                for particle_struct in particle_list:
                    for particle in particle_struct:
                        particle_combinations.append(particle_data[particle])
            except Exception as e:
                traceback.print_exc()
                print(e,"ACTION의 조사를 올바르게 설정했는지 확인하세요")
                exit()
            
            command_elements = [["",device_name]]
            
            # 조사 합성
            try:
                for a in attribute_combinations:
                    for order,group in enumerate(a):
                        if all(isinstance(item, list) for item in group):
                            flat = sum(group, [])
                        else:
                            flat = group
                        temp = []
                        for o in flat:
                            for p in particle_combinations[order]:
                                if o=='':
                                    if p in AFTER_LIST:
                                        temp.append(p)
                                    else:
                                        temp.append("")
                                elif p=='':
                                    temp.append(o)
                                else:
                                    if p in JOSA_LIST:
                                        if callable(o):
                                            temp.append(lambda o=o, p=p: ((val := o()) + Josa.get_josa(val.strip("[]"), p)))
                                        else:
                                            temp.append(cached_get_full_string(o,p))
                                    else:
                                        if callable(o):
                                            temp.append(lambda o=o,p=p: f'{o()}{p}')
                                        else:
                                            temp.append(o+p)
                        command_elements.append(temp)
            except Exception as e:
                traceback.print_exc()
                print(e,"ATTRIBUTE는 한글로 끝나야 합니다")
                exit()
                
            # 동사        
            try:
                expanded_verbs = []
                for v in base_verbs:
                    if len(v) > 0:
                        temptemp = verb_dictionary[v]
                        if v[-1] == '?':
                            temptemp = list(map(lambda x: x+'?',temptemp))
                        expanded_verbs.extend(temptemp)
                        # else:
                            # expanded_verbs.append(v)
                    else:
                        expanded_verbs.append("")
                command_elements.append(expanded_verbs)
                # print(command_elements)
            except Exception as e:
                traceback.print_exc()
                print(e,"오류 : 동사가 생성되지 않았습니다")
                exit()
                
            # 최종 조합
            for combination in product(*command_elements):
                continue_flag = False
                for idx,val in enumerate(combination):
                    # 시간 AFTER 예외 처리 (~~뒤에, ~~후에) -> 시,분,초가 모두 등장하지 않으면 조사를 뺌
                    if val in AFTER_LIST and all(tt == "" for tt in combination[max(0,idx-3):idx]):
                        continue_flag = True
                        break
                if continue_flag:
                    continue
                combination = [x() if callable(x) else x for x in combination]
                combination[-1] = "/".join(combination[-1].split())
                result.append("/".join(combination).strip())
            
    result = list(set(result))
    return result

def make_verb_dictionary():
    global verb_dictionary
    for _, actions in action_data.items():
        for __, action in actions.items():
            for vvv in action["Verb"]:
                if vvv:
                    verb_dictionary.update(run_pipeline(vvv,user_config))


def get_device_attributes(device_name):
    """
    주어진 디바이스(device_name)에 관련된 attribute만
    attribute_data에서 뽑아 dict 형태로 반환합니다.

    Raises:
        ValueError: device_name이 device_data에 없을 경우
    """
    if device_name not in device_data:
        raise ValueError(f"알 수 없는 디바이스입니다: {device_name}")

    used_attrs = set()
    # device_data 구조 순회: action_class → action_name → sentences (list of lists)
    for action_class, actions in device_data[device_name].items():
        for action_name, sentences in actions.items():
            for sentence in sentences:
                for item in sentence:
                    if isinstance(item, str):
                        if item:
                            used_attrs.add(item)
                    elif isinstance(item, list):
                        for sub in item:
                            if sub:
                                used_attrs.add(sub)

    # attribute_data에 실제로 존재하는 것만 필터링
    return {
        attr: attribute_data[attr]
        for attr in used_attrs
        if attr in attribute_data
    }


def extract_attribute_options(device_name):
    """
    주어진 디바이스(device_name)에 사용된 속성들의 옵션만 뽑아서 dict로 반환합니다.
    - Categorical: option 리스트
    - Numerical:
        * min == max → unit 리스트만
        * 그 외     → 전체 option dict
    Raises:
        ValueError: device_name이 device_data에 없을 경우
    """
    if device_name not in device_data:
        raise ValueError(f"알 수 없는 디바이스: {device_name}")

    attrs = get_device_attributes(device_name)
    options = {}

    for name, info in attrs.items():
        opt = info["option"]
        if info["type"] == "Numerical":
            # 값이 고정된 속성은 unit만
            if opt.get("min") == opt.get("max"):
                options[name] = opt["unit"]
            else:
                options[name] = opt
        else:  # Categorical
            options[name] = opt

    return options
# ##################### 동사 예외 처리 #################################
#                     if vvv not in verb_dictionary:
#                         verb_dictionary[vvv] = [vvv]
##################### 예외 처리 끝 #####################################

if __name__ == "__main__":
    print("명령어 생성기 시작")

    # 동사 사전 생성
    start = time.time()
    make_verb_dictionary()
    dictionary_complete = time.time()
    print(f'사전 생성 완료, 소요 시간 : {dictionary_complete - start:.3f} 초')
    
    MODE = 0
    RANDOM_NUM_MODE = 0
    while True:
        MODE = input("선택할 모드의 숫자를 입력하세요\n1. 1개 가전 / 2. 전체 가전\n")
        if not MODE.isdigit():
            print("숫자가 올바르지 않습니다. 다시 입력해주세요")
        else:
            MODE = int(MODE)
            break
    
    if MODE == 1:
        # 1개 가전 테스트용
        SELECTED_DEVICE = input("가전을 1개 선택하세요\n")
        if SELECTED_DEVICE not in device_data:
            print("해당 가전이 없습니다. 다른 가전을 입력하거나, 사전을 추가하세요")
            exit(0)
            
    # 숫자 모드 선택
    # 1. data에 있는 attribute 참조하여 숫자 생성
    # 2. 생성 후 각 항목에 랜덤하게 숫자를 삽입
    # Cardinal -> 1~99, 1단위
    # Ordinal -> 1~99, 1단위, 100~1000, 10단위
    while True:
        RANDOM_NUM_MODE = input("숫자 모드를 골라주세요\n1. 원본 숫자 사용\n2. 랜덤 숫자 사용\n")
        if not RANDOM_NUM_MODE.isdigit():
            print("숫자가 올바르지 않습니다. 다시 입력해주세요")
        else:
            RANDOM_NUM_MODE = int(RANDOM_NUM_MODE)
            break
        
    
    select_complete = time.time()
    
    ####### 1차 처리 - [ 서술어, 조사, 동사 ] 결합 #####   
    
    # 명령어 생성
    result = []
    for device_name in device_data:
        
        if MODE == 1:
            # 테스트용
            if device_name != SELECTED_DEVICE:
                continue
        result.append(f'# ==== <{device_name}> START ==== #')
        result.extend(generate_commands(device_name, device_data, action_data, attribute_data, particle_data,RANDOM_NUM_MODE))
        result.append(f'# ==== <{device_name}> END ==== #')
        if MODE == 2:
            print(f'{device_name} 생성 완료, 현재 명령어 수 : {len(result)}')
    
    generate_complete = time.time()
    result_count = len(result)
    print(f'(1/5) 명령어 {result_count:,} 생성 완료, 소요 시간 : {generate_complete - select_complete:.3f} 초')
        
    ############ 1차 처리 끝 ##############    
    
      
   ######## 2차 처리 - [시제, 부사, 종결어, 문말 어미] 5% 확률로 추가 ####### 
    flex_list = adverb_data["flexible"]
    pre_v_list = adverb_data["pre_verb"]
    post_v_list = adverb_data["post_verb"]

    transform_indices = set(random.sample(range(len(result)), int(len(result) * 0.05)))

    for idx, line in enumerate(result):
        if len(line)==0 or '#' in line:
            continue
        
        parts = line.strip('/\n').split('/')
        
        if idx not in transform_indices:
            sentence = " ".join([p for p in parts if p])
            result[idx] = sentence
            continue
        
        
        flex_idx = random.randrange(len(flex_list))
        pre_idx = random.randrange(len(pre_v_list))
        post_idx = random.randrange(len(post_v_list))
        flex = flex_list[flex_idx]
        pre_v = pre_v_list[pre_idx]
        post_v = post_v_list[post_idx]
        if pre_v:
            parts.insert(len(parts)-1, pre_v)
        if post_v:
            parts.append(post_v)
        if flex:
            i = random.randrange(len(parts)+1)
            parts = parts[:i] + [flex] + parts[i:]
        sentence = " ".join([p for p in parts if p])
        result[idx] = sentence
        ############ 2차 처리 끝 ###############
        

    ######## 추가로 문장 마지막에 등장 조사 제외 ("로","으로"는 예외)
    ToRemoveParticle = particle_data["AllParticle"]
    Particle_list = sorted(ToRemoveParticle,key=lambda x : -len(x))
        
    for idx,line in enumerate(result):
        for p in Particle_list:
            if line.endswith(p):
                line = line[:-len(p)]
                continue
    ##############################################################


    secondary_complete = time.time()
    print(f'(2/5) 부사 삽입 완료, 소요 시간 : {secondary_complete - generate_complete:.3f} 초')
        
        
    result_normal = []
    result_ordinal = []
    normal_count = 0
    ordinal_count = 0
    for com in result:
        if not com:
            continue
        if com[0] == '#':
            result_normal.append(com)
            result_ordinal.append(com)
        elif '[' in com or ']' in com:
            result_ordinal.append(com)
            ordinal_count+=1
        else:
            result_normal.append(com)
            normal_count+=1
    classify_complete = time.time()
    print(f'Normal Command : {normal_count:,}, Ordinal Command : {ordinal_count:,}')
    print(f'(3/5) 분류 완료, 소요 시간 : {classify_complete - secondary_complete:.3f} 초')        
    
    # command.txt로 출력
    # 청크 사이즈
    chunk_size = 20000

    output_path_all = "result/command.txt"
    output_path_with_normal = "result/command_normal.txt"
    output_path_with_ordinal = "result/command_ordinal.txt"
    
    with open(output_path_all,'w',encoding='utf-8',buffering=1024*1024) as f_o:
        # 단위별로 묶어서 출력
        for i in range(0,len(result),chunk_size):
            chunk = result[i:min(i+chunk_size,len(result))]
            print('\n'.join(chunk),file=f_o)
            
    with open(output_path_with_normal,'w',encoding='utf-8',buffering=1024*1024) as f_o:
        # 단위별로 묶어서 출력
        for i in range(0,len(result_normal),chunk_size):
            chunk = result_normal[i:min(i+chunk_size,len(result_normal))]
            print('\n'.join(chunk),file=f_o)
            
    with open(output_path_with_ordinal,'w',encoding='utf-8',buffering=1024*1024) as f_n:
        # 단위별로 묶어서 출력
        for i in range(0,len(result_ordinal),chunk_size):
            chunk = result_ordinal[i:min(i+chunk_size,len(result_ordinal))]
            print('\n'.join(chunk),file=f_n)
        
            
    print()
    file_write_complete = time.time()
    print(f'(4/5) 파일 출력 완료, 소요 시간 : {file_write_complete - classify_complete:.3f} 초')
    print(f'전체 -> {output_path_all}\n서수 -> {output_path_with_ordinal}\n서수 제외 -> {output_path_with_normal}')
    print(f'실행 완료, 총 소요 시간 : {file_write_complete-start:.3f} 초')
    
    