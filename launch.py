import os
import sys
import time
import socket
import threading
import webbrowser
import subprocess

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def free_port(port):
    if not is_port_in_use(port):
        return
    print('[i] Port ' + str(port) + ' is occupied. Clearing previous session...')
    try:
        out = subprocess.check_output('netstat -ano | findstr :' + str(port), shell=True).decode()
        for line in out.strip().splitlines():
            parts = line.strip().split()
            if len(parts) >= 5 and 'LISTENING' in parts:
                pid = parts[-1]
                print('[i] Terminating stale process PID ' + str(pid) + '...')
                subprocess.call('taskkill /F /PID ' + str(pid), shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
    except Exception as e:
        print('[!] Note on port clearing: ' + str(e))

def open_browser():
    for _ in range(30):
        time.sleep(0.5)
        if is_port_in_use(8000):
            print('[+] Server ready! Opening dashboard in browser...')
            webbrowser.open('http://127.0.0.1:8000/')
            return
    webbrowser.open('http://127.0.0.1:8000/')

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print('=' * 79)
    print('           COGNITIVE CANSAT MISSION CONTROL - SYSTEM LAUNCHER')
    print('=' * 79)
    print()
    print('[1/3] Checking ground station network ports...')
    free_port(8000)

    print('[2/3] Scheduling browser launch for http://127.0.0.1:8000/ ...')
    t = threading.Thread(target=open_browser, daemon=True)
    t.start()

    print('[3/3] Starting FastAPI & Machine Learning server on port 8000...')
    print('      Ground Station Dashboard : http://127.0.0.1:8000/')
    print('      WebSocket Serial Bridge  : ws://127.0.0.1:8000/ws/serial')
    print('      Machine Learning API     : http://127.0.0.1:8000/api/predict')
    print()
    print('      TO STOP: Press Ctrl + C anytime.')
    print('-' * 79)
    print()

    import uvicorn
    uvicorn.run('backend.app:app', host='127.0.0.1', port=8000, log_level='info')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n[i] Mission Control server safely shut down. Goodbye!')
