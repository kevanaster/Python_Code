import re
from netaddr import IPNetwork, IPAddress
from Queue import Queue
from threading import Thread, RLock
from getpass import getpass
from netmiko import ConnectHandler
from netmiko.ssh_exception import NetMikoTimeoutException
from netmiko.ssh_exception import NetMikoAuthenticationException

max_threads = 30
working_queue = Queue()
print_lock = RLock()
output_dict = {}
username = raw_input('Username:')
password = getpass()
outlist = []
error_list = []


def ssh_session(thread_num, work_queue):
    while True:
        device_data = work_queue.get()
        queued_device = device_data[0]
        with print_lock:
            print '{}: Working on "{}"'.format(thread_num, queued_device)
        try:
            router = {'device_type': 'aruba_os',
                      'ip': queued_device,
                      'username': username,
                      'password': password,
                      'verbose': False}
            ssh_session = ConnectHandler(**router)
            output = ssh_session.send_command("show user essid REDACTED | include 10.")
            output1 = '1'
            for line in output.splitlines():
                ip = re.findall( r'[0-9]+(?:\.[0-9]+){3}', line)
                if IPAddress(ip[0]) in IPNetwork(device_data[1] + "/23"):
                    output1 = '0'
                    break
            ssh_session.disconnect()
            if output1 == '0':
                # Put output into a dictionary to reference later
                output_dict[queued_device] = True
            else:
                output_dict[queued_device] = device_data[1]
        except Exception, e:
            error_list.append([queued_device, e])

        work_queue.task_done()



devices = [['arubalab1', '10.0.0.1'],
            ['arubalab2', '10.0.0.2']]


for thread_num in range(max_threads):
    worker = Thread(target=ssh_session, args=(
        thread_num, working_queue))
    worker.setDaemon(True)
    worker.start()

for device in devices:
    working_queue.put(device)

working_queue.join()

site_good = []
retry_list = []

for device_name, output_info in output_dict.items():
    if output_info == True:
        sites_good.append([device_name, 'Vlan active'])
    else:
        retry_list.append([device_name, output_info])

print('\n\n\n*** Sites with at least 1 device in subnet ***')
for item in sites_good:
    print(item)

print('\n\n\n*** Sites to retry ***')
for item in retry_list:
    print(item)

complete = len(sites_good)
incomplete = len(retry_list)
device_total = len(devices)
complete_pct = 100 * float(complete)/float(device_total)
incomplete_pct = 100 * float(incomplete)/float(device_total)

print('\n\n*** Valid locations {0}/{1} = {2}%  ***\n\n\n'.format(complete, device_total, complete_pct))

print('\n\n*** Invalid locations {0}/{1} = {2}%  ***\n\n\n'.format(incomplete, device_total, incomplete_pct))

print '\n\n*** Errors Encountered ***'
for i in error_list:
    print '{}, {}'.format(i[0], i[1])

