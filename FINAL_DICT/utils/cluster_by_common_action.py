import json
from itertools import product
from pathlib import Path
from pyjosa.josa import Josa
from verb_generator.action_conjun import run_pipeline
from functools import lru_cache
import time
import sys
import traceback

ACTION_PATH = Path('data/FINAL_ACTION.json')
DEVICE_PATH = Path('data/FINAL_DEVICE.json')
ATTRIBUTE_PATH = Path('data/FINAL_ATTRIBUTE.json')
PARTICLE_PATH = Path('data/FINAL_PARTICLE.json')
JOSA_LIST = ["을","으로"]

def load_json(path : Path):
    with open(path, 'r', encoding = 'utf-8') as f:
        return json.load(f)

action_data = load_json(ACTION_PATH)
device_data = load_json(DEVICE_PATH)
attribute_data = load_json(ATTRIBUTE_PATH)
particle_data = load_json(PARTICLE_PATH)

verb_dictionary = {}
device_action_dictionary = {}

common_command = []
unique_command = {}

@lru_cache(maxsize=100000)
def cached_get_full_string(word, particle):
    return Josa.get_full_string(word, particle)

def get_attribute_value(attribute_name, attribute_data):
    attribute = attribute_data.get(attribute_name)
    if not attribute:
        return []
    if attribute["type"] == "Categorical":
        return attribute['option']
    elif attribute['type'] == 'Numerical':
        option = attribute['option']
        return [f'{num}{unit}' for num in range(option['min'],option['max']+1,option['step']) for unit in option['unit']]
    return []

# 공통 Action set 찾기
def make_common_set():
    for device_name in device_data:
        device_action_dictionary[device_name] = set()
        device_action = device_data[device_name]
        for action_class in device_action:
            for action_name in device_action[action_class]:
                device_action_dictionary[device_name].add(action_name)

# 명령어 생성 함수
def generate_commands(device_name, device_data, action_data, attribute_data, particle_data):
    unique_result = []
    common_result = []
    
    device_action = device_data[device_name]    
    for action_class in device_action:
        for action_name,sentences in device_action[action_class].items():
            action_in_class = action_data[action_class]
            verb = action_in_class[action_name]["Verb"]
            particle_list = action_in_class[action_name]["Particle"]
            
            aa,b,c = [],[],verb
            
            # 명사 생성
            for sentence in sentences:
                sentence_list = []
                for attribute in sentence:
                    if type(attribute) == str:
                        sentence_list.append(get_attribute_value(attribute,attribute_data))
                    elif type(attribute) == list:
                        temp_list = []
                        for attr in attribute:
                            if attr == "":
                                temp_list.append([""])
                            else:
                                temp_list.append(get_attribute_value(attr,attribute_data))
                        sentence_list.append(temp_list)
                aa.append(sentence_list)
            
            
            # 조사 생성
            for particle_struct in particle_list:
                for particle in particle_struct:
                    b.append(particle_data[particle])
            
            # 기기명 포함
            # result_list = [["",device_name]]
            
            # 기기명 미포함
            result_list = []
            
            # 조사 합성
            for a in aa:
                for order,group in enumerate(a):
                    if all(isinstance(item, list) for item in group):
                        flat = sum(group, [])
                    else:
                        flat = group
                    temp = []
                    for o in flat:
                        for p in b[order]:
                            if o=='' and p=='':
                                continue
                            elif o=='' or p=='' or p not in JOSA_LIST:
                                temp.append(o)
                            else:
                                temp.append(cached_get_full_string(o,p))
                    result_list.append(temp)
                
            # 동사
            if action_name in common_set:
                new_c = []
                for v in c:
                    new_c.extend(verb_dictionary[v])
                result_list.append(new_c)
                
                for combination in product(*result_list):
                    common_result.append(" ".join(combination).strip())
                result_list.pop()
            else:
                new_c = []
                for v in c:
                    new_c.extend(verb_dictionary[v])
                result_list.append(new_c)
                
                for combination in product(*result_list):
                    unique_result.append(" ".join(combination).strip())
                result_list.pop()
                
    return common_result,unique_result

def make_verb_dictionary():
    global verb_dictionary
    for _, actions in action_data.items():
        for __, action in actions.items():
            for vvv in action["Verb"]:
                    verb_dictionary.update(run_pipeline(vvv))
                    
# ##################### 동사 예외 처리 ###################################
#                     if vvv not in verb_dictionary:
#                         verb_dictionary[vvv] = [vvv]
##################### 예외 처리 끝 #####################################

if __name__ == "__main__":
    
    # # 테스트용
    # SELECTED_DEVICE = input("가전을 1개 선택하세요")
    
    # 동사 사전 생성
    start = time.time()
    make_verb_dictionary()
    dictionary_complete = time.time()
    print(f'사전 생성 완료, 소요 시간 : {dictionary_complete - start:.3f} 초')
    
    # 디바이스별 액션
    make_common_set()
    common_set = set.intersection(*device_action_dictionary.values())
    print(common_set)
        
    # 명령어 생성
    for device_name in device_data:
        
        # # 테스트 용
        # if device_name != SELECTED_DEVICE:
        #     continue
        
        # 기기별 공통, 기기 단독 구분하여 생성
        device_common_commands, device_unique_commands = generate_commands(device_name, device_data, action_data, attribute_data, particle_data)
        common_command.extend(device_common_commands)
        unique_command[device_name] = device_unique_commands
                
        print(f'{device_name} 생성 완료, 현재 명령어 수 : {len(common_command)+sum([len(i) for i in unique_command.values()])}')
    
    generate_complete = time.time()
    common_count = len(common_command)
    unique_count = sum([len(i) for i in unique_command.values()])
    result_count = common_count + unique_count
    
    print(f'명령어 {result_count} 생성 완료, 소요 시간 : {generate_complete - dictionary_complete:.3f} 초')
    
    # 중복 제거
    deduplicate_time = time.time()
    common_command = list(set(common_command))
    for device_name in unique_command:
        unique_command[device_name] = list(set(unique_command[device_name]))
    
    print(f'중복 제외 {len(common_command)+sum([len(i) for i in unique_command.values()])} 확정, 소요 시간 : {generate_complete - dictionary_complete:.3f} 초')
    
    # 청크 사이즈
    chunk_size = 1000000
    with open('result/command_by_device/common.txt','w',encoding='utf-8',buffering=1024*1024) as f:
        for i in range(0,common_count,chunk_size):
            chunk = common_command[i:min(i+chunk_size,common_count)]
            print('\n'.join(chunk),file=f)
            
    for device_name, device_unique_command_list in unique_command.items():
        with open(f'result/command_by_device/{device_name}.txt','w',encoding='utf-8',buffering=1024*1024) as f:
            for i in range(0,unique_count,chunk_size):
                chunk = device_unique_command_list[i:min(i+chunk_size,unique_count)]
                print('\n'.join(chunk),file=f)
            
                        
    print()
    file_write_complete = time.time()
    print(f'파일 출력 완료, 소요 시간 : {file_write_complete - deduplicate_time:.3f} 초')
    print(f'\n 실행 완료, 소요 시간 : {file_write_complete-start:.3f} 초')
    
    
    