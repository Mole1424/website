FROM python:3.10
RUN pip install pipenv
WORKDIR /app
COPY . .
RUN pipenv install --system
RUN pipenv run flask run