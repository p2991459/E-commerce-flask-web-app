(venv/bin/gunicorn --config gunicorn_config.py wsgi:app > out.log 2>&1 &) && sleep 3 && chown apache:apache routing-webapp.sock
