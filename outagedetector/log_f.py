import pytz
from pathlib import Path
def separate_log_file(current_timestamp, internet_connected, just_booted):
    now = current_timestamp.now(pytz.timezone('America/New_York'))

    file_name = current_timestamp.strftime("%Y-%m-%d")
    log_line_date = current_timestamp.strftime("%H:%M:%S")
    l = f"Script has run at {log_line_date}. Internet connected: {internet_connected}. Just booted: {just_booted}.\n"
    file = Path.home().joinpath(f'.config/outagedetector/{file_name}.log')
    # print(f"Writing to {file}")
    with open(file, 'a+') as f:
        f.writelines(l)
        f.close()