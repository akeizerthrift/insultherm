cd /var/lib/cloud9/mm-machineapp-template/server
while true; do `python3 app.py`; echo "[`date`] MachineApp server exited with code $exit_code" >> /var/log/mm_services_errors.log; done;