#!/usr/bin/env python3
import logging
import sys
import yaml
from jinja2 import Environment, FileSystemLoader
from napalm import get_network_driver
from netaddr import IPNetwork, IPAddress


def menu(title):
    """Small function to make  titles stand out

    Args:
        title (str): String to be made into a title, less than 30 char is ideal
    """
    title = ' ' + title + ' '
    print('{s:{c}^{n}}'.format(s='', n=30, c='#'))
    print('{s:{c}^{n}}'.format(s=title, n=30, c='#'))
    print('{s:{c}^{n}}'.format(s='', n=30, c='#'))


def extractYAML(yaml_file):
    """This function extracts YAML vars from a YAML file.

    Args:
        yaml_file (string): String containing the path to YAML file.

    Returns:
        dictionary: Returns a dictionary with all values parsed from YAML file.
    """
    try:
        with open(yaml_file) as var_file:
            yaml_output = yaml.load(var_file, Loader=yaml.FullLoader)
        return (yaml_output)
    except:
        print('Extracting YAML encountered an error')


def renderJinja2(template, vars_to_render=None, templates_path='./templates'):
    """Function to render Jinja2 template specified, optionally use dictionary key:val pair inside j2.

    Args:
        template (string): String specifying filename of template to be used.
        vars_to_render (dict, optional): Dictionary passed containing key:val pairs for j2 render. Defaults to None.
        templates_path (str, optional): Path to directory with j2 templates. Defaults to './templates'.

    Returns:
        string: String rendered from j2 template.
    """
    file_loader = FileSystemLoader(templates_path)
    env = Environment(loader=file_loader)
    template = env.get_template(template)
    config = vars_to_render
    logging.info('Returning rendered config')
    return template.render(config)


def configDevice(device_hostname, device_config, commit=False):
    """Function to configure ios devices using NAPALM

    Args:
        device_hostname (str): Hostname associated with the device, used to connect to the device.
        device_config (str): Configuration to be deployed to the device.
        commit (bool, optional): Boolean to commit config, False will not commit. Defaults to False.
    """
    logging.info('Set NAPALM driver to ios')
    driver = get_network_driver("ios")
    logging.info(f'Connecting to host {device_hostname}')
    # I have hardcoded the user/pass, other options would be collecting creds from a secured source/vault or collecting from user on script run
    device = driver(
                hostname = device_hostname,
                username = 'cisco',
                password = 'cisco123'
                )
    device.open()
    logging.info(f'Loading config to {device_hostname}')
    device.load_merge_candidate(config=device_config)
    menu(f'{device_hostname} Diff')
    print(device.compare_config())
    if commit:
        logging.info(f'Committing config to {device_hostname}')
        device.commit_config()
    logging.info(f'Close connection with {device_hostname}')
    device.close()


def validatePing(device_hostname, neighbor):
    """Function to ping test connected neighbor based on configured interface.
    Checks to determine which interface is within the same subnet.

    Args:
        device_hostname (str): Hostname associated with the device, used to connect to the device.
        neighbor (str): IP address of neighbor directly connected.

    Returns:
        string: 'success' or 'fail' is returned based on ping response 3+ echo  is success
    """
    logging.info('Set NAPALM driver to ios')
    driver = get_network_driver("ios")
    logging.info(f'Connecting to host {device_hostname}')
    # I have hardcoded the user/pass, other options would be collecting creds from a secured source/vault or collecting from user on script run
    device = driver(
                hostname = device_hostname,
                username = 'cisco',
                password = 'cisco123'
                )
    device.open()
    logging.info('Get device interface IPs using NAPALM get_interfaces_ip getter')
    output = device.get_interfaces_ip()
    for interface in output:
        for key in output[interface]['ipv4'].keys():
            cidr = output[interface]['ipv4'][key]['prefix_length']
            logging.info(f'Check if {key}/{cidr} contains neighbor {neighbor}')
            if neighbor in IPNetwork(f'{key}/{cidr}'):
                ping_result = device.ping(neighbor, source=key)
                # Choosing 2 because the first few packets can be dropped
                if ping_result['success']['packet_loss'] > 2:
                    logging.warning(f'{device_hostname}: neighbor {neighbor}, ping fail')
                    return 'fail'
                else:
                    logging.info(f'{device_hostname}: neighbor {key}, ping success')
                    return 'success'
    logging.info(f'Close connection with {device_hostname}')
    device.close()


def validateBGP(device_hostname):
    """Function to validate if bgp neighbors are Up/Down

    Args:
        device_hostname (str): Hostname associated with the device, used to connect to the device.

    Returns:
        dict: Dictionary containing neighbors with Up/Down flag.
            Example: {'UP': ['x.x.x.x'], 'DOWN': ['x.x.x.x']}
    """
    driver = get_network_driver("ios")
    logging.info('Set NAPALM driver to ios')
    driver = get_network_driver("ios")
    logging.info(f'Connecting to host {device_hostname}')
    # I have hardcoded the user/pass, other options would be collecting creds from a secured source/vault or collecting from user on script run
    device = driver(
                hostname = device_hostname,
                username = 'cisco',
                password = 'cisco123'
                )
    device.open()
    logging.info('Get BGP neighbors using NAPALM get_bgp_neighbors getter')
    output = device.get_bgp_neighbors()
    logging.info('Initialize bgp validation dictionary')
    bgp_validation = {'UP': [], 'DOWN': []}
    for peer in output['global']['peers']:
        if peer.startswith('10'):
            peer_ip = peer
            is_up = output['global']['peers'][peer_ip]['is_up']
            if is_up:
                logging.info(f'{device_hostname}: peer {peer_ip} is Up')
                bgp_validation['UP'].append(peer_ip)
            else:
                logging.warning(f'{device_hostname}: peer {peer_ip} is Down')
                bgp_validation['DOWN'].append(peer_ip)
    logging.info(f'Close connection with {device_hostname}')
    device.close()
    return bgp_validation


def main():
    """Main Function, this is where everything is tied together to configure interfaces and bgp.
    """
    logging.basicConfig(level=logging.INFO)
    data = extractYAML('./input/config.yaml')

    menu('Configure Interfaces')
    for host in data:
        logging.info(f'Render interface config from YAML vars for {host}')
        interface_config = renderJinja2('interfaces.j2', data[host])
        logging.info(f'Configure interfaces on {host}')
        configDevice(host, interface_config, commit=True)


    menu('Validate L2')
    for host in data:
        for item in data[host]['bgp']['neighbors']:
            neighbor_addr = item['ipaddr']
            logging.info(f'Validate connectivity based on neighbor {neighbor_addr}')
            if validatePing(host, neighbor_addr) == 'fail':
                logging.warning(f'{host} failed to ping {neighbor_addr}, halting run')
                sys.exit()


    menu('Configure BGP')
    for host in data:
        logging.info(f'Render BGP config from YAML vars for {host}')
        bgp_config = renderJinja2('bgp.j2', data[host]['bgp'])
        logging.info(f'Configure BGP on {host}')
        configDevice(host, bgp_config, commit=True)


    menu('Validate BGP')
    for host in data:
        print(validateBGP(host))

if __name__ == "__main__":
    main()
