pyinstaller -F -n ursa.exe --collect-submodules celery --collect-submodules eventlet --collect-submodules dns --hidden-import celery.fixups --add-data=mq;. -y main.py
