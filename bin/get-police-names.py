#!/usr/bin/env python

# This script is used to download the full names of police forces and
# neighbourhoods in England and Wales from the police API, which are required by
# import_police.py.

# For this to work, you need to have a username and password for the police API,
# and you should put them in ~/.police_api_credentials.json, as in this example:
#
# { "username": "fakeusername", "password": "fakepassword" }

# Police API documentation: http://policeapi2.rkh.co.uk/api/docs/

import datetime
import json
import os
import urllib2

api_credentials_path = os.path.join(os.environ['HOME'],
                                    '.police_api_credentials.json')

base_url = 'http://policeapi2.rkh.co.uk/api/'
forces_url = os.path.join(base_url, 'forces')

date_string = datetime.date.today().isoformat()
save_path = '../data/Police-Names_'+date_string+'/'

with open(api_credentials_path) as f:
    credentials = json.load(f)
    username = credentials['username']
    password = credentials['password']

# The following is mostly from http://www.voidspace.org.uk/python/articles/authentication.shtml

# This creates a password manager:
passman = urllib2.HTTPPasswordMgrWithDefaultRealm()

# Because we have put None for the realm at the start it will always use this
# username/password combination for urls:
passman.add_password(None, forces_url, username, password)

# Create the AuthHandler:
authhandler = urllib2.HTTPBasicAuthHandler(passman)

opener = urllib2.build_opener(authhandler)
urllib2.install_opener(opener)
# All calls to urllib2.urlopen will now use our handler.

# Authentication is now handled automatically for us:
forces = urllib2.urlopen(forces_url).read()

os.mkdir(save_path)

with open(os.path.join(save_path, 'forces.json'), 'w') as f:
    print "Getting forces"
    f.write(forces)

forces = json.loads(forces)

for force in forces:
    force_id = force['id']
    print "Getting neighbourhoods for %s" % (force_id)
    nbhs_url = os.path.join(base_url, force_id, 'neighbourhoods')
    passman.add_password(None, nbhs_url, username, password)
    nbhs = urllib2.urlopen(nbhs_url).read()
    with open(os.path.join(save_path, force_id+'_neighbourhoods.json'), 'w') as f:
        f.write(nbhs)

