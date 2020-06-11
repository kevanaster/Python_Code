import csv
import time
import netmiko
from Queue import Queue
from threading import Thread, RLock
from getpass import getpass
from netmiko.ssh_exception import NetMikoTimeoutException
from netmiko.ssh_exception import NetMikoAuthenticationException

# Set max threads
max_threads = 100
working_queue = Queue()
print_lock = RLock()
# NOTE: raw input and getpass don't work in IDE
username = raw_input('Username:')
password = getpass()
conffile_csv = '/Users/master.csv'
error_list = []

# SSH Function called by threads, pulls host from Queue


def ssh_session(thread_num, work_queue):
    while True:
        queued_host = work_queue.get()
        with print_lock:
            print '{}: Working on "{}"'.format(thread_num, queued_host)
        try:
            router = {'device_type': 'aruba_os',
                      'ip': queued_host,
                      'username': username,
                      'password': password,
                      'verbose': False}
            ssh_session = netmiko.ConnectHandler(**router)
            ssh_session.send_command('write mem')

            ssh_session.disconnect()
        except Exception, e:
            error_list.append([queued_host, e])

        work_queue.task_done()

# Used to test credentials against localhost


def ssh_test():
    while True:
        try:
            test_device = {'device_type': 'linux', 'ip': 'localhost',
                           'username': username, 'password': password}
            ssh_session = netmiko.ConnectHandler(**test_device)
            ssh_session.disconnect()
            return True
        except (NetMikoAuthenticationException):
            print('Username or Password Error')
            return False
        except (NetMikoTimeoutException):
            print('Localhost timeout')
            return False


startTime = time.time()

print '*** Testing SSH Creds ***'
# Test User Creds
if ssh_test() != True:
    exit()
print '*** SSH Creds Success! ***'

# Build Threads
for thread_num in range(max_threads):
    worker = Thread(target=ssh_session, args=(
        thread_num, working_queue))
    worker.setDaemon(True)
    worker.start()

# Build Queue from hostfile
with open(conffile_csv) as devices:
    deviceDict = csv.DictReader(devices)
    for row in deviceDict:
        with print_lock:
            print 'Putting {} in queue'.format(row['hostname'])
        # Put device hostname in queue
        working_queue.put(row['hostname'])


# Waiting for the Queue to empty
with print_lock:
    print '*** Waiting for all threads to complete ***'
working_queue.join()
print '*** Finished SSH Sessions ***'

if len(error_list) > 0:
    print '*** Errors Encountered ***'
    for i in error_list:
        print '{}, {}'.format(i[0], i[1])


# Printing time in seconds, rounding to 2 decimals
print '*** Finished Script - {} seconds ***'.format(str(round((time.time() - startTime), 2)))
