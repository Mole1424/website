from flask import Flask, render_template, redirect, url_for, request
from db_schema import db, Projects
from markdown import markdown
from werkzeug.security import generate_password_hash, check_password_hash
import yaml

app = Flask(__name__)

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f).get("config")

app.config['SQLALCHEMY_DATABASE_URI'] = config.get("database_uri")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
resetdb = False
if resetdb:
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.commit()

@app.route("/")
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
    markdown_html = markdown(project.blog)
    return render_template("projectpage.html", project=project, markdown_html=markdown_html)

@app.route("/projects/<int:project_id>/edit")
def edit_project(project_id):
    project = Projects.query.filter_by(id=project_id).first()
    return render_template("editproject.html", action=f"/projects/{project.id}/editing", title=project.title, description=project.description, image=project.image, blog=project.blog, delete=False)

@app.route("/projects/<int:project_id>/editing", methods=["POST"])
def editing_project(project_id):
    if check_password_hash(config.get("password"), request.form['password']):
        project = Projects.query.filter_by(id=project_id).first()
        project.title = request.form['title']
        project.description = request.form['description']
        project.image = request.form['image']
        project.blog = request.form['blog']
        db.session.commit()
        return redirect(f"/projects/{project_id}")
    return redirect(f"/projects/{project_id}/edit")

@app.route("/projects/newproject")
def new_project():
    return render_template("editproject.html", action="/projects/creatingnewproject", title="New Project", description="", image="", blog="", delete=False)

@app.route("/projects/creatingnewproject", methods=["POST"])
def creating_new_project():
    if check_password_hash(config.get("password"), request.form['password']):
        project = Projects(request.form['title'], request.form['description'], request.form['image'], request.form['blog'])
        db.session.add(project)
        db.session.commit()
        return redirect(f"/projects/{project.id}")
    return redirect("/projects/newproject")

@app.route("/projects/<int:project_id>/delete")
def delete_project_page(project_id):
    return render_template("editproject.html", action=f"/projects/{project_id}/deleting", title="Delete", delete=True)

@app.route("/projects/<int:project_id>/deleting", methods=["POST"])
def delete_project(project_id):
    if check_password_hash(config.get("password"), request.form['password']):
        project = Projects.query.filter_by(id=project_id).first()
        db.session.delete(project)
        db.session.commit()
        return redirect("/projects")
    return redirect(f"/projects/{project_id}")