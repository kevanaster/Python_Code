import radius
from getpass import getpass

radius_secret = "REDCATED"
radius_server = "REDCATED"
radius_port = 1812
user = input('Username:')
password = getpass()

r = radius.Radius(radius_secret, host=radius_server, port=radius_port)
print('success' if r.authenticate(user, password) else 'failure')
