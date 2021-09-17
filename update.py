# copy Macast-plugins to your local config dirs

import os
import shutil
import appdirs

CONFIG_DIR = appdirs.user_config_dir('Macast', 'xfangfang')


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

    # create macast config dir
    target = os.path.join(CONFIG_DIR, 'renderer')
    try:
        os.makedirs(target)
    except FileExistsError as e:
        pass

    # copy plugins to macast config dir
    for i in plugins_path:
        try:
            shutil.copy(i, target)
        except Exception as e:
            print(e)


if __name__ == '__main__':
    main()
