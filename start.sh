#!/bin/bash
cd /home/tserver/hr_system
pkill -f 'manage.py runserver 0.0.0.0:8000' || true
sleep 1
nohup /home/tserver/hr_env/bin/python manage.py runserver 0.0.0.0:8000 >> /home/tserver/hr_system/runserver.log 2>&1 &
echo 'HR System server launched on 0.0.0.0:8000'
