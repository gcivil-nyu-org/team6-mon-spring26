# To run locally
```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

# If installing a new package
```
pip install packagename
pip freeze > requirements.txt
```
Then commit changes

# Before requesting a PR
```
black .
flake8 .
python manage.py test
coverage run --source=accounts manage.py test
```

Fix all errors and warnings, then request a PR. Verify that that all Travis Checks pass. If not, edit your code until it works.