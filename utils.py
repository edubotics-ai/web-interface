import os
import shutil
import yaml

README_CONFIG = """
---
title: {class_name} ({class_number})
description: AI Assistant for {class_name} class ({class_number})
emoji: 🎓
colorFrom: red
colorTo: green
sdk: docker
app_port: 7860
---
"""


def update_repo(class_dir, class_info):
    ai_tutor_dir = os.path.join(class_dir, "apps", "ai_tutor")
    config_path = os.path.join(ai_tutor_dir, "config", "project_config.yml")
    storage_path = os.path.join(ai_tutor_dir, "storage")

    urls_file = os.path.join(storage_path, "urls.txt")
    with open(urls_file, "w+") as f:
        f.write(class_info["class_url"])

    with open(config_path, "r") as f:
        config_file = yaml.safe_load(f)
    config_file["metadata"]["class_name"] = class_info["class_name"]
    config_file["metadata"]["class_number"] = class_info["class_number"]
    config_file["metadata"]["instructor_name"] = class_info["instructor_name"]

    with open(config_path, "w+") as f:
        yaml.dump(config_file, f, indent=4)

        shutil.copy(os.path.join(os.path.dirname(__file__),
                                 'assets/Dockerfile'), os.path.join(class_dir, 'Dockerfile'))

    with open(os.path.join(class_dir, "README.md"), "w") as f:
        f.write(README_CONFIG.format(
            class_name=class_info["class_name"], class_number=class_info["class_number"]))

    with open(os.path.join(class_dir, "requirements.txt"), "w") as f:
        f.write("edubotics-core")

    return True


if __name__ == "__main__":
    update_repo(
        "instances/thomas gardos_DS542",
        {
            "class_name": "Something else",
            "class_number": "DS542",
            "instructor_name": "Thomas Gardos",
            "class_url": "https://x.com",
        },
    )
