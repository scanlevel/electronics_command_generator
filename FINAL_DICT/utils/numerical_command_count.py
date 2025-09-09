import json
from itertools import product
from pathlib import Path
from pyjosa.josa import Josa
from verb_generator.action_conjun import run_pipeline
from functools import lru_cache
import time
import random
from math import prod
from bisect import bisect_right

ACTION_PATH = Path('data/FINAL_ACTION.json')
DEVICE_PATH = Path('data/FINAL_DEVICE.json')
ATTRIBUTE_PATH = Path('data/FINAL_ATTRIBUTE.json')
PARTICLE_PATH = Path('data/FINAL_PARTICLE.json')
JOSA_LIST = ["을", "으로"]

def load_json(path: Path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

action_data = load_json(ACTION_PATH)
device_data = load_json(DEVICE_PATH)
attribute_data = load_json(ATTRIBUTE_PATH)
particle_data = load_json(PARTICLE_PATH)

verb_dictionary = {}

@lru_cache(maxsize=100000)
def cached_get_full_string(word, particle):
    return Josa.get_full_string(word, particle)

def get_attribute_value(attribute_name, attribute_data):
    attribute = attribute_data.get(attribute_name)
    if not attribute:
        return [], False
    if attribute["type"] == "Categorical":
        return attribute['option'], False
    elif attribute['type'] == 'Numerical':
        option = attribute['option']
        values = [f'{num}{unit}' for num in range(option['min'], option['max'] + 1, option['step']) for unit in option['unit']]
        return values, True
    return [], False

def generate_commands(device_name, device_data, action_data, attribute_data, particle_data):
    result = []
    device_action = device_data[device_name]
    for action_class in device_action:
        for action_name, sentences in device_action[action_class].items():
            action_in_class = action_data[action_class]
            verb = action_in_class[action_name]["Verb"]
            particle_list = action_in_class[action_name]["Particle"]

            attribute_combinations = []
            particle_combinations = []
            base_verbs = verb
            numerical_flag = False

            for sentence in sentences:
                sentence_list = []
                for attribute in sentence:
                    if isinstance(attribute, str):
                        values, is_numerical = get_attribute_value(attribute, attribute_data)
                        numerical_flag |= is_numerical
                        sentence_list.append(values)
                    elif isinstance(attribute, list):
                        temp_list = []
                        for attr in attribute:
                            if attr == "":
                                temp_list.append([""])
                            else:
                                values, is_numerical = get_attribute_value(attr, attribute_data)
                                numerical_flag |= is_numerical
                                temp_list.append(values)
                        sentence_list.append(temp_list)
                attribute_combinations.append(sentence_list)

            for particle_struct in particle_list:
                for particle in particle_struct:
                    particle_combinations.append(particle_data[particle])

            command_elements = [["", device_name]]

            for a in attribute_combinations:
                for order, group in enumerate(a):
                    flat = sum(group, []) if all(isinstance(item, list) for item in group) else group
                    temp = []
                    for o in flat:
                        for p in particle_combinations[order]:
                            if o == '':
                                continue
                            elif p == '':
                                temp.append(o)
                            else:
                                if p in JOSA_LIST:
                                    temp.append(cached_get_full_string(o, p))
                                else:
                                    temp.append(o + p)
                    command_elements.append(temp)

            expanded_verbs = []
            for v in base_verbs:
                if v:
                    expanded_verbs.extend(verb_dictionary[v])
                else:
                    expanded_verbs.append("")
            command_elements.append(expanded_verbs)

            result.append((command_elements, numerical_flag))

    return result

def make_verb_dictionary():
    global verb_dictionary
    for _, actions in action_data.items():
        for __, action in actions.items():
            for vvv in action["Verb"]:
                verb_dictionary.update(run_pipeline(vvv))

if __name__ == "__main__":
    start = time.time()
    make_verb_dictionary()
    dictionary_complete = time.time()

    command_list = []
    for device_name in device_data:
        command_list.extend(generate_commands(device_name, device_data, action_data, attribute_data, particle_data))
    
    generate_complete = time.time()
    # for adsaf in command_list:
    #     print(adsaf)
    # 총 명령어 수
    total_count = sum(prod(len(g) for g in cs) for cs, _ in command_list)
    numerical_count = sum(prod(len(g) for g in cs) for cs, is_numerical in command_list if is_numerical)

    print(f'총 명령어 수: {total_count}')
    print(f'Numerical 명령어 수: {numerical_count}')
    print(f'Categorical만 있는 명령어 수 : {total_count - numerical_count}')
    print(f'{100*(total_count - numerical_count)/total_count:.2f} %')

    # # 샘플 추출
    # SAMPLE_COUNT = int(input("샘플 수를 고르세요\n"))

    # group_sizes = [prod(len(l) for l in group) for group, _ in command_list]
    # cumsum = [0]
    # for size in group_sizes:
    #     cumsum.append(cumsum[-1] + size)

    # def global_to_local_index(cumsum, global_idx):
    #     group_idx = bisect_right(cumsum, global_idx) - 1
    #     local_idx = global_idx - cumsum[group_idx]
    #     return group_idx, local_idx

    # def kth_product(group_lists, k):
    #     result = []
    #     sizes = [len(l) for l in group_lists]
    #     for size, lst in zip(reversed(sizes), reversed(group_lists)):
    #         idx = k % size
    #         result.append(lst[idx])
    #         k //= size
    #     return list(reversed(result))

    # total = cumsum[-1]
    # random_indices = random.sample(range(total), SAMPLE_COUNT)

    # with open("./result/command.txt", 'w', encoding='utf-8') as f:
    #     for global_idx in random_indices:
    #         group_idx, local_idx = global_to_local_index(cumsum, global_idx)
    #         command = kth_product(command_list[group_idx][0], local_idx)
    #         print('/'.join(command), file=f)

    # end = time.time()
    # print(f"총 소요 시간: {end - start:.3f} 초")
