from functools import wraps
from os import getenv

from flask import Flask, redirect, render_template, request, session
from markdown import markdown
from markupsafe import escape
from werkzeug.security import check_password_hash

from db_schema import Projects, db

app = Flask(__name__)

password = getenv("DB_PASSWORD")

app.config["SQLALCHEMY_DATABASE_URI"] = getenv("DB_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # sets up databases
db.init_app(app)

app.secret_key = getenv("SECRET_KEY")


def login_required(func):  # decorator to restrict access to certain pages
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "logged_in" in session:
            if session["logged_in"]:
                return func(*args, **kwargs)
        return redirect("/")

    wrapper.__name__ = func.__name__
    return wrapper


@app.route("/")
@app.route("/home")
def home():
    projects = Projects.query.all()
    return render_template("home.html", homepage=True, projects=projects)


@app.route("/aboutme")
def about_me():
    return render_template("aboutmepage.html", homepage=False)


@app.route("/projects")
def projects():
    projects = Projects.query.all()
    return render_template("projectspage.html", projects=projects)


@app.route("/projects/<int:project_id>")
def project(project_id):
    project = Projects.query.filter_by(id=project_id).first()
    if project is None:  # protect against invalid project ids which caused 500 errors
        return render_template("noproject.html")
    markdown_html = markdown(project.blog)  # converts markdown to html for blog
    return render_template(
        "projectpage.html", project=project, markdown_html=markdown_html
    )


@app.route("/projects/<int:project_id>/edit")
@login_required
def edit_project(project_id):
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
def editing_project(project_id):
    # edits project if password is correct
    if check_password_hash(password, request.form["password"]):
        project = Projects.query.filter_by(id=project_id).first()
        project.title = request.form["title"]
        project.description = request.form["description"]
        project.image = request.form["image"]
        project.blog = escape(request.form["blog"])
        db.session.commit()
        return redirect(f"/projects/{project_id}")
    return redirect(f"/projects/{project_id}/edit")


@app.route("/projects/newproject")
@login_required
def new_project():
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
    if check_password_hash(password, request.form["password"]):
        # creates new project if password is correct
        project = Projects(
            request.form["title"],
            request.form["description"],
            request.form["image"],
            escape(request.form["blog"]),  # escape() prevents XSS
        )
        db.session.add(project)
        db.session.commit()
        return redirect(f"/projects/{project.id}")
    return redirect("/projects/newproject")


@app.route("/projects/<int:project_id>/delete")
@login_required
def delete_project_page(project_id):
    return render_template(
        "editproject.html",
        action=f"/projects/{project_id}/deleting",
        title="Delete",
        delete=True,
    )


@app.route("/projects/<int:project_id>/deleting", methods=["POST"])
@login_required
def delete_project(project_id):
    if check_password_hash(password, request.form["password"]):
        project = Projects.query.filter_by(id=project_id).first()
        db.session.delete(project)
        db.session.commit()
        return redirect("/projects")
    return redirect(f"/projects/{project_id}")


LOGIN_URL = "/" + getenv("LOGIN_URL")
LOGGINGIN_URL = "/" + getenv("LOGGINGIN_URL")


@app.route(LOGIN_URL)
def login():
    # because all you need for the login page is password box and submit, can reuse editproject.html (kinda cursed ngl)
    return render_template(
        "editproject.html", action="/loggingin", title="Logging In", delete=True
    )


@app.route(LOGGINGIN_URL, methods=["POST"])
def logging_in():
    if check_password_hash(password, request.form["password"]):
        session["logged_in"] = True
    return redirect("/")
