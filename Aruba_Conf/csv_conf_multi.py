import csv
from netmiko import ConnectHandler
from Queue import Queue
from threading import Thread, RLock
from getpass import getpass


max_threads = 100
working_queue = Queue()
print_lock = RLock()
error_list = []
deviceList = []
output_dict = {}
write_mem = True


def menu(title):
    title = ' ' + title + ' '
    print '{s:{c}^{n}}'.format(s='', n=30, c='#')
    print '{s:{c}^{n}}'.format(s=title, n=30, c='#')
    print '{s:{c}^{n}}'.format(s='', n=30, c='#')


def ssh_session(thread_num, work_queue):
    while True:
        queued_device = work_queue.get()
        with print_lock:
            print '{}: Working on "{}"'.format(thread_num, queued_device[0])

        try:
            router = {'device_type': 'aruba_os',
                      'ip': queued_device[0],
                      'username': username,
                      'password': password,
                      'verbose': False}
            ssh = ConnectHandler(**router)

            ssh.send_config_set(queued_device[1])

            if write_mem:
                ssh.send_command('write mem')

            ssh.disconnect()
        except Exception, e:
            error_list.append([queued_device, e])

        work_queue.task_done()


menu('Multiple CSV Config')

username = raw_input('Username: ')
password = getpass()


for thread_num in range(max_threads):
    worker = Thread(target=ssh_session, args=(
        thread_num, working_queue))
    worker.setDaemon(True)
    worker.start()

menu('Building Queue')
current_key = ''
new_output = []
# Datafile setup as hostname,conf lines with each command entry per line (with host specified)
data_file = '/Users/tacacs_conf.csv'
conf_dict = {}

with open(data_file) as file:
    deviceDict = csv.DictReader(file)
    for row in deviceDict:
        if row['hostname'] in conf_dict:
            conf_dict[row['hostname']].append(row['conf'])
        else:
            conf_dict[row['hostname']] = [row['conf']]

for key in conf_dict:
    with print_lock:
        print 'Putting {} in queue'.format(key)
    working_queue.put([key, conf_dict[key]])

with print_lock:
    menu('Queue loaded')
working_queue.join()

menu('Task Complete')


if error_list:
    menu('Errors')
    for i in error_list:
        print '{}, {}'.format(i[0], i[1])

