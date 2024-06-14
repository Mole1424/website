from functools import wraps
from logging import INFO, basicConfig, info, warning
from os import environ, getenv, path, getcwd, makedirs, listdir
from random import randint

from flask import (
    Flask,
    redirect,
    render_template,
    request,
    Request,
    session,
    send_from_directory,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from markdown import markdown
from markupsafe import escape
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from db_schema import Projects, db

dev = True  # if true then uses config.txt to set environment variables
if dev:
    with open("config.txt", "r") as f:
        for line in f.readlines():
            split_line = line.split(";")
            environ[split_line[0]] = split_line[1].strip()


app = Flask(__name__)

password = getenv("DB_PASSWORD")

app.config["SQLALCHEMY_DATABASE_URI"] = getenv("DB_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # sets up databases
db.init_app(app)

app.secret_key = getenv("SECRET_KEY")

app.config["UPLOAD_FOLDER"] = getenv("PHOTO_LOC")


def login_required(func):  # decorator to restrict access to certain pages
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "logged_in" in session:
            if session["logged_in"]:  # if the user is logged in then allow access
                return func(*args, **kwargs)
        return redirect("/")  # otherwise redirect to home page

    wrapper.__name__ = func.__name__
    return wrapper


limiter = Limiter(  # limits the amount of requests per hour (mainly for logging in page for security)
    get_remote_address,
    app=app,
    storage_uri="memory://",
)

basicConfig(level=INFO)  # allows info to be displayed in portainer logs


@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html", projects=get_projects_from_db(False))


@app.route("/projects/smallprojects")
def small_projects():
    projects = get_projects_from_db(True)
    for project in projects:
        project.description = convert_to_html(project.description)
    return render_template("smallprojects.html", projects=get_projects_from_db(True))


@app.route("/projects/<int:project_id>")
def project(project_id: int):
    project = Projects.query.filter_by(id=project_id).first()
    if project is None:  # protect against invalid project ids which caused 500 errors
        return render_template("noproject.html")
    markdown_html = convert_to_html(project.blog)
    return render_template(
        "projectpage.html", project=project, markdown_html=markdown_html
    )


def get_projects_from_db(small: bool):
    projects = Projects.query.filter(
        Projects.blog == "" if small else Projects.blog != ""
    ).all()
    return projects[::-1]


def convert_to_html(text: str):
    escaped = escape(text)
    markdown_html = markdown(escaped)
    coded_html = remove_amp_from_code_tags(markdown_html)
    striked_html = add_stike_through(coded_html)
    return striked_html


def remove_amp_from_code_tags(text: str):
    # removes "amp;" from code tags to fix escaping issues

    lines = text.splitlines()  # split all html by lines
    code_block = False
    modified_lines = []

    for line in lines:
        if "<code>" in line:  # when opening tag is found now in code block
            code_block = True
            line = line.replace(
                "amp;", ""
            )  # some code will be on same line as decleration
            modified_lines.append(line)
            continue

        if "</code>" in line:  # when closing tag is found no longer in code block
            code_block = False
            line = line.replace("amp;", "")
            modified_lines.append(line)
            continue

        if code_block:  # during code block remove amps
            line = line.replace("amp;", "")

        modified_lines.append(line)  # if nothing just append unedited line

    return "\n".join(modified_lines)


def add_stike_through(text: str):
    # adds strike through to text
    start_index = text.find("~~")
    if start_index != -1:
        end_index = text.find("~~", start_index + 2)
        if end_index != -1:
            added = (
                text[:start_index]
                + "<s>"
                + text[start_index + 2 : end_index]
                + "</s>"
                + text[end_index + 2 :]
            )
            return add_stike_through(added)
    return text


@app.route("/projects/<int:project_id>/edit")
@login_required
def edit_project(project_id: int):
    project = Projects.query.filter_by(id=project_id).first()
    return render_template(
        "editproject.html",
        action=f"/projects/{project.id}/editing",
        title=project.title,
        description=project.description,
        image=project.image,
        blog=project.blog,
        delete=False,
    )


@app.route("/projects/<int:project_id>/editing", methods=["POST"])
@login_required
def editing_project(project_id: int):
    correct_password = check_password_hash(password, request.form["password"])
    log_blog_change(request.remote_addr, "edited", project_id, correct_password)
    # edits project if password is correct
    if correct_password:
        project = Projects.query.filter_by(id=project_id).first()
        project.title = request.form["title"]
        project.description = request.form["description"]
        project.image = request.form["image"]
        project.blog = request.form["blog"]
        db.session.commit()
        # gets all the data from the form and updates the project
        # dont have to check for change as all fields are pre-populated
        return redirect(f"/projects/{project_id}")
    return redirect(f"/projects/{project_id}/edit")


@app.route("/projects/newproject")
@login_required
def new_project():
    # same as edit project but with empty fields
    return render_template(
        "editproject.html",
        action="/projects/creatingnewproject",
        title="New Project",
        description="",
        image="",
        blog="",
        delete=False,
    )


@app.route("/projects/creatingnewproject", methods=["POST"])
@login_required
def creating_new_project():
    correct_password = check_password_hash(password, request.form["password"])
    if correct_password:
        # creates new project if password is correct
        project = Projects(
            request.form["title"],
            request.form["description"],
            request.form["image"],
            request.form["blog"],
        )
        db.session.add(project)
        db.session.commit()
        log_blog_change(request.remote_addr, "created", project.id, True)
        return redirect(f"/projects/{project.id}")
    log_blog_change(request.remote_addr, "created", -1, False)
    return redirect("/projects/newproject")


@app.route("/projects/<int:project_id>/delete")
@login_required
def delete_project_page(project_id: int):
    return render_template(
        "editproject.html",
        action=f"/projects/{project_id}/deleting",
        title="Delete",
        delete=True,
    )


@app.route("/projects/<int:project_id>/deleting", methods=["POST"])
@login_required
def delete_project(project_id: int):
    correct_password = check_password_hash(password, request.form["password"])
    log_blog_change(request.remote_addr, "deleted", project_id, correct_password)
    # deletes project if password is correct
    if correct_password:
        project = Projects.query.filter_by(id=project_id).first()
        db.session.delete(project)
        db.session.commit()
        return redirect("/projects")
    return redirect(f"/projects/{project_id}")


def log_blog_change(ip: str, action: str, project_id: int, success: bool):
    # higher order functions++
    log_func = info if success else warning
    log_func(
        f"{ip} {action} blog for project {project_id} {'' if success else 'un'}successfully"
    )


LOGIN_URL = "/" + getenv("LOGIN_URL")
LOGGINGIN_URL = "/" + getenv("LOGGINGIN_URL")
PHOTO_URL = "/" + getenv("PHOTO_URL")
DOG_URL = "/dog/" + getenv("PHOTO_URL")


@app.route(LOGIN_URL)
def login():
    warning(f"{request.remote_addr} accessed the login page")
    # because all you need for the login page is password box and submit, can reuse editproject.html (kinda cursed ngl)
    return render_template(
        "editproject.html", action=LOGGINGIN_URL, title="Logging In", delete=True
    )


@app.route(LOGGINGIN_URL, methods=["POST"])
@limiter.limit("50/hour")  # limits the amount of requests per hour
def logging_in():
    if check_password_hash(password, request.form["password"]):
        session["logged_in"] = True
        info(f"{request.remote_addr} logged in")
        return redirect("/")
    else:
        warning(
            f"{request.remote_addr} failed to log in with password {request.form['password']}"
        )
    return redirect(LOGIN_URL)


@app.route(PHOTO_URL, methods=["GET", "POST"])
@login_required
def upload_photo():
    if request.method == "POST":
        return add_photo(request, app.config["UPLOAD_FOLDER"])
    return render_template("uploadphoto.html", action=PHOTO_URL)


def add_photo(
    request: Request,
    upload_folder: str,
    dog: bool = False,
):
    if (
        # pre=checks
        check_password_hash(password, request.form["password"])
        and "photo" in request.files
        and request.files["photo"].filename != ""
    ):
        photo = request.files["photo"]

        # only allow png, jpg, jpeg files
        if not photo.filename.endswith((".png", ".jpg", ".jpeg")):
            return "<h1>Invalid file type</h1>"

        # get filename and extension
        file_name, ext = path.splitext(secure_filename(photo.filename))
        if dog:
            file_name = "bear"

        # split path
        base_path = path.join(getcwd(), upload_folder[1:], file_name)
        file_path = base_path + ext

        # create directory if it doesn't exist
        if not path.exists(path.dirname(file_path)):
            makedirs(path.dirname(file_path))

        # stop duplicate file names
        i = 1
        while path.exists(file_path) or (dog and i == 1):
            file_path = f"{base_path}{i}{ext}"
            i += 1

        # save photo
        photo.save(file_path)

        info(f"{request.remote_addr} uploaded photo {file_name} to {file_path}")
        return f"""
        <h1>Photo uploaded successfully to {file_path}</h1>
        <h1><a href='/'>Home</a></h1>
        <img src='{upload_folder}{file_name}{ext}' alt='uploaded photo'>"""
    return "<h1>Invalid request</h1>"


@app.route("/dog/")
def dog():
    # serve random dog image
    dog_images = listdir(app.config["UPLOAD_FOLDER"] + "dog")
    dog_image = dog_images[randint(0, len(dog_images) - 1)]
    return send_from_directory(app.config["UPLOAD_FOLDER"] + "dog", dog_image)


@app.route(DOG_URL, methods=["GET", "POST"])
@login_required
def add_dog():
    # add a dog
    if request.method == "POST":
        return add_photo(request, f"{app.config['UPLOAD_FOLDER']}dog/", True)
    return render_template("uploadphoto.html", action=DOG_URL)
