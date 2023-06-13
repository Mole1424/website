FROM python:3.10
RUN pip install pipenv
WORKDIR /app
COPY . .
RUN pipenv install --system
CMD gunicord app:app -b 0.0.0.0:8080