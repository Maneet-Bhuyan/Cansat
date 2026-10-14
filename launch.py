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
                print('[i] Terminating stale process tree PID ' + str(pid) + '...')
                subprocess.call('taskkill /F /T /PID ' + str(pid), shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(10):
            if not is_port_in_use(port):
                break
            time.sleep(0.3)
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
    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root_dir)
    print('=' * 79)
    print('           COGNITIVE CANSAT MISSION CONTROL - SYSTEM LAUNCHER')
    print('=' * 79)
    print()
    print('[1/3] Checking ground station network ports...')
    free_port(8000)

    print('[2/3] Scheduling browser launch for http://127.0.0.1:8000/ ...')
    t = threading.Thread(target=open_browser, daemon=True)
    t.start()

    print('[3/3] Checking Telemetry Data Lakehouse pipeline...')
    candidates = [
        os.path.join(root_dir, 'pipeline'),
        os.path.abspath(os.path.join(root_dir, '..', 'cansat-telemetry-pipeline'))
    ]
    pipeline_dir = next((p for p in candidates if os.path.exists(p)), candidates[0])
    worker_script = os.path.join(pipeline_dir, 'stream_processing', 'stream_worker.py')
    redpanda_online = is_port_in_use(19092) or is_port_in_use(9092)
    timescale_online = is_port_in_use(5432)
    grafana_online = is_port_in_use(3000)

    worker_proc = None
    if redpanda_online and timescale_online and os.path.exists(worker_script):
        print('      [+] Telemetry Data Lakehouse detected ONLINE!')
        print('          Redpanda Broker : localhost:19092')
        print('          TimescaleDB     : localhost:5432')
        if grafana_online:
            print('          Grafana Avionics: http://localhost:3000/')
        print('      [i] Starting Stream Processing Worker...')
        try:
            worker_proc = subprocess.Popen(
                [sys.executable, worker_script],
                cwd=pipeline_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as we:
            print('      [!] Note on stream worker: ' + str(we))
    else:
        print('      [i] Pipeline Standby: Docker services offline or not started.')
        print('          CanSat Mission Control will run with full telemetry HUD & internal bridge.')
        print('          (To activate TimescaleDB & Grafana, run START_INTEGRATED_MISSION_CONTROL.bat)')

    print()
    print('[4/4] Starting FastAPI & Machine Learning server on port 8000...')
    print('      Ground Station Dashboard : http://127.0.0.1:8000/')
    print('      WebSocket Serial Bridge  : ws://127.0.0.1:8000/ws/serial')
    print('      Machine Learning API     : http://127.0.0.1:8000/api/predict')
    print('      Database Operations API  : http://127.0.0.1:8000/api/db/missions')
    print('      Pipeline Integration API : http://127.0.0.1:8000/api/pipeline/status')
    print()
    print('      TO STOP: Press Ctrl + C anytime.')
    print('-' * 79)
    print()

    import uvicorn
    try:
        uvicorn.run('backend.app:app', host='127.0.0.1', port=8000, log_level='info', reload=True, reload_dirs=[root_dir])
    finally:
        if worker_proc:
            try:
                worker_proc.terminate()
            except Exception:
                pass


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n[i] Mission Control server safely shut down. Goodbye!')
