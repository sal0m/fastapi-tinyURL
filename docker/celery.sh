#!/bin/bash

cd src

if [[ "${1}" == "celery" ]]; then
  celery --app=celery_app:celery_app worker -l INFO
elif [[ "${1}" == "beat" ]]; then
  celery --app=celery_app:celery_app beat -l INFO
fi
