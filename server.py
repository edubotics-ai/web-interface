import os
import sys
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, Response
from flask.helpers import send_from_directory
from flask_cors import CORS
import requests
import shutil
from dotenv import load_dotenv, dotenv_values
from utils import update_repo, README_CONFIG
import git
from huggingface_hub import HfApi, create_repo, login

load_dotenv()

PROD = os.getenv('PROD') == 'false'

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')


hf_token = os.getenv('HF_TOKEN')
environment_secrets = dotenv_values('.env')

CORS(app)

# Define the base directory for instances
INSTANCES_DIR = os.path.join(os.path.dirname(__file__), 'instances')
TEMPLATE_REPO_URL = "https://github.com/edubotics-ai/edubotics-app"

STATIC_DIR = os.path.join(os.path.dirname(
    __file__), 'frontend/client/dist/public' if PROD else 'frontend/client')

# Create instances directory if it doesn't exist
os.makedirs(INSTANCES_DIR, exist_ok=True)


def set_state(user_info):
    print(f"Setting state for {user_info}")
    session['user_data'] = user_info
    return 'State set'


@app.route('/get_state')
def get_state():
    return session.get('user_data', {})


@app.route('/create-instance', methods=['POST'])
def create_instance():
    class_number = request.form.get('classNumber')
    class_name = request.form.get('className')
    instructor_name = request.form.get('instructorName')
    class_url = request.form.get('classUrl')
    # Create a directory for this class instance
    class_dir = os.path.join(
        INSTANCES_DIR, f'{instructor_name.lower()}_{class_number}')

    class_info = {
        'class_number': class_number,
        'class_name': class_name,
        'instructor_name': instructor_name,
        'class_url': class_url
    }
    set_state(class_info)

    try:
        # Create the directory (fail if already exists to prevent overwrites)
        os.makedirs(class_dir)

        repo = git.Repo.clone_from(TEMPLATE_REPO_URL,
                                   class_dir,
                                   branch='main')

        print(f"Created new instance in {class_dir}. {repo}")

    except FileExistsError:
        print(f"Instance for class {class_number} already exists")
        # You might want to handle this case differently

    try:
        result = update_repo(class_dir, class_info)
    except Exception as e:
        return render_template('error.html', error=str(e))

    return redirect(url_for('success', class_name=class_name, class_number=class_number, instructor_name=instructor_name))


@app.route("/success")
def success():
    class_name = request.args.get('class_name')
    class_number = request.args.get('class_number')
    instructor_name = request.args.get('instructor_name')
    return render_template('success.html', class_name=class_name, class_number=class_number, instructor_name=instructor_name)


@app.route("/error")
def error():
    error = request.args.get('error') or "An unknown error occurred"
    return render_template('error.html', error=error)


@app.route("/publish", methods=['GET', 'POST'])
def publish():
    if request.method == 'POST':
        # Get form data
        # hf_token = request.form.get('hf_token')
        space_name = request.form.get('space_name')

        # Get class info from session
        class_info = session.get('user_data', {})
        class_number = class_info.get('class_number')
        instructor_name = class_info.get('instructor_name')

        if not hf_token or not space_name:
            return render_template('error.html', error="Hugging Face token and space name are required")

        if not class_number or not instructor_name:
            return render_template('error.html', error="Class information not found in session, please create an instance first. <a href='/'>Create an instance</a>")

        # Directory for this class instance
        class_dir = os.path.join(
            INSTANCES_DIR, f'{instructor_name.lower()}_{class_number}')

        if not os.path.exists(class_dir):
            return render_template('error.html', error="Class repository not found, please create an instance first. <a href='/'>Create an instance</a>")

        try:
            # Login to Hugging Face
            login(token=hf_token)

            # Initialize the Hugging Face API
            hf_api = HfApi(token=hf_token)

            # Create a new Space or get existing one
            space_id = f"edubotics/{space_name}"
            secrets = [{"key": key, "value": value}
                       for key, value in environment_secrets.items()]
            try:
                create_repo(space_id, repo_type="space",
                            space_sdk="docker", space_secrets=secrets)
            except Exception as e:
                print(f"Note: {str(e)}")

            # Push the local repository to the Space
            hf_api.upload_folder(
                folder_path=class_dir,
                repo_id=space_id,
                repo_type="space",
                commit_message="Initial setup from EduBotics App"
            )

            # Return success page with the Space URL
            space_url = f"https://huggingface.co/spaces/{space_id}"

            return render_template('publish_success.html', space_url=space_url)

        except Exception as e:
            return render_template('error.html', error=f"Failed to publish to Hugging Face: {str(e)}")

    # GET request - show the publish form
    return render_template('publish.html')


@app.route('/', defaults={'path': ''})
def catch_all(path):
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
