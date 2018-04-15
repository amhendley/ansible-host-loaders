
# Ansible Dynamic Inventory Schema

Reference: http://docs.ansible.com/ansible/latest/dev_guide/developing_inventory.html#developing-inventory

```json
{
    "group001": {
        "hosts": ["host001", "" "host002"],
        "vars": {
            "var1": true
        },
        "children": ["group002"]
    },
    "group002": {
        "hosts": ["host003","host004"],
        "vars": {
            "var2": 500
        },
        "children":[]
    }
    "_meta": {
        "hostvars": {
            "host001": {
                "var001" : "value"
            },
            "host002": {
                "var002": "value"
            }
        }
    }
}
```
