#!/usr/bin/python

import argparse
import json
import os
import sys

from psycopg2 import connect

from ansible.utils.shlex import shlex_split
from ansible.plugins.inventory.ini import InventoryModule


pg_host = os.getenv('PG_HOST', 'localhost')
pg_port = os.getenv('PG_PORT', '5432')
pg_database = os.getenv('PG_DATABASE')
pg_username = os.getenv('PG_USERNAME')
pg_passwd = os.getenv('PG_PASSWD')

parser = argparse.ArgumentParser(prog=os.path.basename(__file__),
                                 description='Ansible dynamic hosts loader from PostgreSQL source')

try:
    parser.add_argument('-s', '--source', required=False, help='PostgreSQL host name. Default is localhost')
    parser.add_argument('-p', '--port', required=False, help='PostgreSQL port. Default is 5432')
    parser.add_argument('-d', '--database', required=False, help='PostgreSQL source database')
    parser.add_argument('-u', '--username', required=False, help='PostgreSQL login name')
    parser.add_argument('-w', '--password', required=False, help='PostgreSQL login password')
    parser.add_argument('-l', '--list', required=False, action='store_true', help='Ansible inventory list arg')

    args = parser.parse_args()
except:
    sys.exit()

if args.source:
    pg_host = args.source

if args.port:
    pg_port = args.port

if args.database:
    pg_database = args.database

if args.username:
    pg_username = args.username

if args.password:
    pg_passwd = args.password


class MyInventoryParser(InventoryModule):
    def __init__(self):
        pass


def msg(_type, text, exit=0):
    sys.stderr.write("%s: %s\n" % (_type, text))
    sys.exit(exit)


data = {}
mip = MyInventoryParser()

conn = connect(host=pg_host,  port=pg_port, database=pg_database, user=pg_username, password=pg_passwd)

cursor = conn.cursor()
cursor.execute('''select h.name,h.address,hg.name as hostgroup 
from hosts h, hostgroups hg, hostgroup_host hh 
where h.host_id=hh.host_id 
and hg.hostgroup_id=hh.hostgroup_id 
and  hg.name not like '%_poller_group' 
and hg.name not like 'Auto-Registration' 
order by h.name''')

rows = cursor.fetchall()
for row in rows:
    # print("host: %s, address: %s, group: %s" % (row[0], row[1], row[2]))

    section = row[2]

    if ':' in section:
        group, state = section.split(':')
    else:
        group = section
        state = 'hosts'

    # Added this condition to ensure prior population is not wiped out.
    if group not in data:
        data[group] = {}

    if state not in data[group]:
        if state == 'vars':
            data[group][state] = {}
        else:
            data[group][state] = []

    # Parse hosts or group members/vars
    try:
        tokens = shlex_split(row[0], comments=True)
    except ValueError as e:
        msg('E', "Error parsing host definition '%s': %s" % (row, e))

    (hostnames, port) = mip._expand_hostpattern(tokens[0])

    # Create 'all' group if no group was defined yet
    if group is None:
        group = 'all'
        state = 'hosts'
        data['all'] = {
            'hosts': []
        }

    tok = []

    if state == 'hosts':
        tok = tokens[1:]
    elif state == 'vars':
        tok = tokens

    variables = {}

    for t in tok:
        if '=' not in t:
            msg(
                'E',
                "Expected key=value host variable assignment, "
                "got: %s" % (t))

        (k, v) = t.split('=', 1)
        variables[k] = mip._parse_value(v)

    if state == 'vars':
        for key, val in variables.items():
            data[group][state][key] = val
    else:
        for host in hostnames:
            data[group][state].append(host)

            if state == 'hosts' and len(variables):
                if '_meta' not in data:
                    data['_meta'] = {
                        'hostvars': {}
                    }

                # Added this condition to ensure prior population is not wiped out.
                if host not in data['_meta']['hostvars']:
                    data['_meta']['hostvars'][host] = {}

                for key, val in variables.items():
                    data['_meta']['hostvars'][host][key] = val

cursor.close()
conn.close()

print(json.dumps(data, indent=4, sort_keys=True))
