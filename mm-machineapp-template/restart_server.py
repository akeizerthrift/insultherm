#/usr/bin/python3
import logging
import subprocess
import http.client

def run():
    # Restarts the server if it is running
    logging.info('Restarting the server')
    conn = http.client.HTTPConnection("192.168.7.2:3011")
    conn.request("GET", "/kill")

if __name__ == "__main__":
    run()