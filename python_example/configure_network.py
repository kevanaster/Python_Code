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


def validateLLDP(device_hostname):
    """Function to validate interface configuration based on lldp validation file

    Args:
        device_hostname (str): Hostname associated with the device, used to connect to the device.

    Returns:
        bool: Returns a bool True for validation pass, False for validation fail
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
    logging.info('Get compliance report for interfaces LLDP')
    compliance = device.compliance_report(f'templates/validation/{device_hostname}_interfaces.yaml')
    device.close()
    logging.info(f'Verify interface compliance for {device_hostname}')
    if compliance['get_lldp_neighbors']['complies']:
        logging.info(f'{device_hostname} interfaces in compliance')
        return True
    else:
        logging.warning(f'{device_hostname} interfaces out of compliance')
        return False


def validateBGP(device_hostname):
    """Function to validate BGP configuration based on bgp validation file

    Args:
        device_hostname (str): Hostname associated with the device, used to connect to the device.

    Returns:
        bool: Returns a bool True for validation pass, False for validation fail
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
    logging.info('Get compliance report for interfaces BGP')
    compliance = device.compliance_report(f'templates/validation/{device_hostname}_bgp.yaml')
    device.close()
    logging.info(f'Verify bgp compliance for {device_hostname}')
    if compliance['get_bgp_neighbors']['complies']:
        logging.info(f'{device_hostname} bgp in compliance')
        return True
    else:
        logging.warning(f'{device_hostname} bgp out of compliance')
        return False


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

    menu('Validate Interfaces')
    for host in data:
        if validateLLDP(host):
            logging.info(f'{host} interface validation passed')
        else:
            logging.warning(f'{host} failed interface validation, halting run')
            sys.exit()


    menu('Configure BGP')
    for host in data:
        logging.info(f'Render BGP config from YAML vars for {host}')
        bgp_config = renderJinja2('bgp.j2', data[host]['bgp'])
        logging.info(f'Configure BGP on {host}')
        configDevice(host, bgp_config, commit=True)


    menu('Validate BGP')
    for host in data:
        if validateBGP(host):
            logging.info(f'{host} bgp validation passed')
        else:
            logging.warning(f'{host} failed bgp validation, halting run')
            sys.exit()

if __name__ == "__main__":
    main()
