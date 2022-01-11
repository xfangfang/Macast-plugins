# Update info.json
# this script is used by repo owner

import os
import re
import json

REPO_BASE_PATH = 'https://raw.githubusercontent.com/xfangfang/Macast-plugins/main/'
REPO_URL = "https://github.com/xfangfang/Macast-plugins"

def read_metadata(path):
    data = {}
    base_name = "/".join(path.split('/')[-2:])
    with open(path, 'r', encoding='utf-8') as f:
        renderer_file = f.read()
        metadata = re.findall("<macast.(.*?)>(.*?)</macast", renderer_file)
        print("< Load Renderer from {}".format(base_name))
        for key, value in metadata:
            print('%-10s: %s' % (key, value))
            data[key] = value
        data['url'] = REPO_BASE_PATH + base_name
        if 'renderer' in data:
            data['type'] = 'renderer'
        if 'protocol' in data:
            data['type'] = 'protocol'
    return data


def main():
    # get plugins path
    current_path = os.path.dirname(os.path.abspath(__file__))
    print(current_path)
    plugins_path = []
    for root, dirs, files in os.walk(current_path):
        for file in files:
            if ".py" in file and file not in ['update.py', 'info.py', 'example.py']:
                plugins_path.append(os.path.join(root, file))
    print('\n'.join(plugins_path))

    # update info
    info = dict()
    info['plugin_v1'] = []
    info['repo_url'] = REPO_URL
    for path in plugins_path:
        data = read_metadata(path)
        info['plugin_v1'].append(data)

    print(info)

    # write to file
    info_path = os.path.join(current_path, 'info.json')
    with open(info_path, "w") as f:
        json.dump(obj=info, fp=f, sort_keys=True, indent=4)


if __name__ == '__main__':
    main()
