web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && python -m gunicorn constr_store.wsgi:application --bind 0.0.0.0:$PORT
