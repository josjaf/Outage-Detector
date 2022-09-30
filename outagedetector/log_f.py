import pytz
from pathlib import Path
def separate_log_file(current_timestamp, internet_connected, just_booted, ping_time):
    if just_booted:
        just_booted_message = "YES"
    else:
        just_booted_message = "NO"
    now = current_timestamp.now(pytz.timezone('America/New_York'))

    file_name = now.strftime("%Y-%m-%d")
    log_line_date = now.strftime("%H:%M:%S")
    l = f"Script has run at {log_line_date}. Internet connected: {internet_connected}. Just booted: {just_booted_message}. Ping Time: {ping_time}\n"
    dir = Path.home().joinpath(f'.config/outagedetector/')
    Path.mkdir(dir,exist_ok=True)
    file = dir.joinpath(f'{file_name}.log')
    file.touch(exist_ok=True)
    # print(f"Writing to {file}")
    with open(file, 'a+') as f:
        f.writelines(l)
        f.close()