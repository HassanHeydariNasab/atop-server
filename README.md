Initialize a Postgresql database according to `db.py` file.

`pipenv --python 3.9`

`pipenv install`

`pipenv shell`

`gunicorn app:app -b 127.0.0.1:5000 --access-logfile -` in root directory or `flask run` in atop directory
