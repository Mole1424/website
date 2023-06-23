from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/aboutme")
def about_me():
    return render_template("aboutmepage.html")

@app.route("/projects")
def projects():
    return "Coming soon(tm)...."