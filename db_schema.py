from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Projects(db.Model):
    __tablename__ = "projects"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    image = db.Column(db.String, nullable=False)
    blog = db.Column(db.String, nullable=False)

    def __init__(self, title, description, image, blog):
        self.title = title
        self.description = description
        self.image = image
        self.blog = blog