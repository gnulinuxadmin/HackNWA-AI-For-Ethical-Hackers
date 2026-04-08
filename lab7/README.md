
ansible -m ping -i lab.yml -u student --become all
ansible-playbook -i lab.yml lab7_elk_wazuh_setup.yml -u student --become
