import os
import json
import sys
import csv


from ansible.utils.shlex import shlex_split
from ansible.plugins.inventory.ini import InventoryModule


class MyInventoryParser(InventoryModule):
    def __init__(self):
        pass


def msg(_type, text, exit=0):
    sys.stderr.write("%s: %s\n" % (_type, text))
    sys.exit(exit)


data = {}
mip = MyInventoryParser()

filename = os.getenv('filename')

with open(filename, 'r') as f:
    reader = csv.DictReader(f)
    first_row = True

    for line in reader:
        section = line['group']

        print('Section : %s' % section)

        if ':' in section:
            group, state = section.split(':')
        else:
            group = section
            state = 'hosts'

        data[group] = {}

        if state not in data[group]:
            if state == 'vars':
                data[group][state] = {}
            else:
                data[group][state] = []


        # Parse hosts or group members/vars
        try:
            combined_values = "%s %s" % (line['host'], line['variables'])
            tokens = shlex_split(combined_values, comments=True)
        except ValueError as e:
            msg('E', "Error parsing host definition '%s': %s" % (line, e))

        print('tokens: %s' % tokens)
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


print('---')
print(json.dumps(data, indent=4, sort_keys=True))