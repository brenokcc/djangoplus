# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import datetime

from django.core.management.base import BaseCommand

from fabric.api import *
from fabric.contrib.files import exists, append, contains

from django.conf import settings

username = 'root'
project_dir = os.getcwd()
project_name = project_dir.split('/')[-1]
remote_project_dir = '/var/opt/{}'.format(project_name)

env.user = username
env.connection_attempts = 10


class Command(BaseCommand):
    VERBOSE = False

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--push', action='store_true', dest='push', default=False, help='Syncronize files only')
        parser.add_argument('--update', action='store_true', dest='update', default=False, help='Syncronize files and update the requirements')
        parser.add_argument('--deploy', action='store_true', dest='deploy', default=False, help='Deploy the application.')
        parser.add_argument('--create', action='store_true', dest='create', default=False, help='Creates a new droplet and deploy the application.')

        parser.add_argument('--verbose', action='store_true', dest='verbose', default=False, help='Verbose the output')

    def handle(self, *args, **options):
        if 'help' not in options:
            if settings.DIGITAL_OCEAN_TOKEN:
                execute_task = deploy

                Command.VERBOSE = options.get('verbose', False)
                output['running'] = Command.VERBOSE
                output['warnings'] = Command.VERBOSE
                output['stdout'] = Command.VERBOSE
                output['stderr'] = Command.VERBOSE

                if options.get('push'):
                    execute_task = push
                elif options.get('update'):
                    execute_task = update
                if options.get('create') or settings.DIGITAL_OCEAN_SERVER:
                    if options.get('create'):
                        host = _create_droplet()
                        if host:
                            env.hosts = [host]
                            execute(execute_task, host=host)
                        else:
                            print('Sorry! The droplet could not be created.')
                    else:
                        host = _check_droplet()
                        if host:
                            env.hosts = [host]
                            execute(execute_task, host=host)
                        else:
                            print('Sorry! The droplet {} could not be found'.format(settings.DIGITAL_OCEAN_SERVER))
                else:
                    print('Please, set the DIGITAL_OCEAN_SERVER variable in settings.py or execute the'
                          ' command with --create parameter to create a new droplet.')
            else:
                print('Please, set the DIGITAL_OCEAN_TOKEN variable in settings.py')


GIT_INGORE_FILE_CONTENT = '''*.pyc
.svn
.DS_Store
.DS_Store?
._*
.idea/*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
.project
.pydevproject
.settings/*
sqlite.db
media/*
mail/*
fabfile.pyc
'''
NGINEX_FILE_CONTENT = '''server {{
    client_max_body_size 100M;
    listen {port};
    server_name {server_name};
    access_log /var/opt/{project_name}/logs/nginx_access.log;
    error_log /var/opt/{project_name}/logs/nginx_error.log;
    location /static {{
        alias /var/opt/{project_name}/static;
    }}
    location /media {{
        alias /var/opt/{project_name}/media;
    }}
    location / {{
        proxy_pass_header Server;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_set_header X-Real_IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        proxy_pass http://localhost:{local_port}/;
    }}
}}
'''
SUPERVISOR_FILE_CONTENT = '''[program:{project_name}]
directory = /var/opt/{project_name}
user = www-data
command = /var/opt/{project_name}/gunicorn_start.sh
stdout_logfile = /var/opt/{project_name}/logs/supervisor_out.log
stderr_logfile = /var/opt/{project_name}/logs/supervisor_err.log
'''
GUNICORN_FILE_CONTENT = '''#!/bin/bash
set -e
source /var/opt/.virtualenvs/{project_name}/bin/activate
mkdir -p /var/opt/{project_name}/logs
cd /var/opt/{project_name}
exec gunicorn {project_name}.wsgi:application -w 1 -b 127.0.0.1:{port} --timeout=600 --user=www-data --group=www-data --log-level=_debug --log-file=/var/opt/{project_name}/logs/gunicorn.log 2>>/var/opt/{project_name}/logs/gunicorn.log
'''
LIMITS_FILE_CONTENT = '''
*               soft     nofile           65536
*               hard     nofile           65536
root            soft     nofile           65536
root            hard     nofile           65536
'''
BASHRC_FILE_CONTENT = '''
export WORKON_HOME=/var/opt/.virtualenvs
mkdir -p $WORKON_HOME
source /usr/local/bin/virtualenvwrapper.sh
'''


def _debug(s):
    if Command.VERBOSE:
        print('[{}] {}\n'.format(datetime.datetime.now(), s))


def _available_port():
    nginex_dir = '/etc/nginx/sites-enabled'
    port = 8000
    with cd(nginex_dir):
        files = run('ls').split()
        files.remove('default')
        if project_name in files:
            files = [project_name]
        if files:
            command = "grep  localhost {} | grep -o '[0-9]*'".format(' '.join(files))
            ports = run(command).split()
            ports.sort()
            port = ports[-1]
            if project_name not in files:
                port = int(port) + 1
    _debug('Returning port {}!'.format(port))
    return int(port)


def _check_local_keys():
    local_home_dir = local('echo $HOME', capture=True)
    local_ssh_dir = os.path.join(local_home_dir, '.ssh')
    local_public_key_path = os.path.join(local_ssh_dir, 'id_rsa.pub')
    if not os.path.exists(local_ssh_dir):
        _debug('Creating dir {}...'.format(local_ssh_dir))
        local('mkdir {}'.format(local_ssh_dir))
        if not os.path.exists(local_public_key_path):
            local("ssh-keygen -f {}/id_rsa -t rsa -N ''".format(local_ssh_dir))

    key = open(local_public_key_path, 'r').read().strip()
    _debug('Checking if private key was uploaded to digital ocean...')
    url = 'https://api.digitalocean.com/v2/account/keys'
    command = '''curl -X GET -H 'Content-Type: application/json' -H 'Authorization: Bearer {}' "{}"'''.format(settings.DIGITAL_OCEAN_TOKEN, url)
    response = local(command, capture=True)
    # print response
    if key not in response:
        _debug('Uploading private key to digital ocean...')
        command = '''curl -X POST -H 'Content-Type: application/json' -H 'Authorization: Bearer {}' -d '{{"name":"{}","public_key":"{}"}}' "{}"'''.format(settings.DIGITAL_OCEAN_TOKEN, 'Default', key, url)
        response = local(command, capture=True)
        # print response


def _check_remote_keys():
    local_home_dir = local('echo $HOME', capture=True)
    local_ssh_dir = os.path.join(local_home_dir, '.ssh')
    local_public_key_path = os.path.join(local_ssh_dir, 'id_rsa.pub')
    local_private_key_path = os.path.join(local_ssh_dir, 'id_rsa')

    remote_home_dir = run('echo $HOME')
    remote_ssh_dir = os.path.join(remote_home_dir, '.ssh')
    remote_public_key_path = os.path.join(remote_ssh_dir, 'id_rsa.pub')
    remote_private_key_path = os.path.join(remote_ssh_dir, 'id_rsa')
    remote_private_known_hosts_path = os.path.join(remote_ssh_dir, 'known_hosts')
    if not exists(remote_ssh_dir):
        _debug('Creading remote dir {}...'.format(remote_ssh_dir))
        run('mkdir -p {}'.format(remote_ssh_dir))
        _debug('Creating empty file {}...'.format(remote_private_known_hosts_path))
        run('touch {}'.format(remote_private_known_hosts_path))

    with cd(remote_ssh_dir):
        public_key = open(local_public_key_path, 'r').read()
        private_key = open(local_private_key_path, 'r').read()
        _debug('Checking if public key is in file {}...'.format(remote_public_key_path))
        if not contains(remote_public_key_path, public_key):
            _debug('Appending public key in file {}...'.format(remote_public_key_path))
            append(remote_public_key_path, public_key)
        _debug('Checking if private key is in file {}...'.format(remote_private_key_path))
        if not contains(remote_private_key_path, private_key):
            _debug('Appending private key in file {}...'.format(remote_private_key_path))
            append(remote_private_key_path, private_key)
        run('chmod 644 {}'.format(remote_public_key_path))
        run('chmod 600 {}'.format(remote_private_key_path))
        _debug('Checking if {} is in file {}...'.format(env.hosts[0], remote_private_known_hosts_path))
        if not contains(remote_private_known_hosts_path, env.hosts[0]):
            _debug('Appending {} in file {}...'.format(env.hosts[0], remote_private_known_hosts_path))
            run('ssh-keyscan {} >> {}'.format(env.hosts[0], remote_private_known_hosts_path))


def _check_repository():
    with cd('/home'):
        git_dir = '/home/git'
        if not exists(git_dir):
            run('adduser --disabled-password --gecos "" git')
            run('mkdir /home/git/.ssh && chmod 700 /home/git/.ssh')
            run('touch /home/git/.ssh/authorized_keys && chmod 600 /home/git/.ssh/authorized_keys')
            run('cat /root/.ssh/authorized_keys >> /home/git/.ssh/authorized_keys')
            run('chown -R git.git /home/git/.ssh/')
        project_git_dir = '/home/git/{}.git'.format(project_name)
        if not exists(project_git_dir):
            run('mkdir {}'.format(project_git_dir))
            run('cd {} && git init --bare'.format(project_git_dir))
            run('chown -R git.git {}'.format(project_git_dir))
    return 'git@{}:{}.git'.format(env.hosts[0], project_name)


def _setup_local_repository():
    _debug('Checking if local project is a git project...')
    if not os.path.exists(os.path.join(project_dir, '.git')):
        with cd(project_dir):
            _debug('Making local project a git project...')
            repository_url = _check_repository()
            local('git init')
            local('git remote add origin "{}"'.format(repository_url))
            local('echo "..." > README.md')
            local('echo "{}" > .gitignore'.format(GIT_INGORE_FILE_CONTENT))
            local('git config --global user.email "user@domain.com"')
            local('git config --global user.name "user"')


def _setup_remote_repository():
    _debug('Checking if the project was cloned in remote server...')
    if not exists(remote_project_dir):
        with cd('/var/opt'):
            _debug('Cloning project in remote server...')
            repository_url = _check_repository()
            run('git clone {} {}'.format(repository_url, project_name))
            run('chown -R www-data.www-data {}'.format(project_name))
    _debug('Updating project in remote server...')
    with cd(remote_project_dir):
        run('git pull origin master')


def _push_local_changes():
    _debug('Checking if project has local changes...')
    now = datetime.datetime.now().strftime("%Y%m%d %H:%M:%S")
    with cd(project_dir):
        if 'nothing to commit' not in local('git status', capture=True):
            _debug('Comminting local changes...')
            files = []
            for file_name in local('ls', capture=True).split():
                if file_name not in GIT_INGORE_FILE_CONTENT or file_name == 'fabfile.py':
                    files.append(file_name)
            files.append('.gitignore')
            for pattern in NGINEX_FILE_CONTENT.split():
                if pattern in files:
                    files.remove(pattern)
            local('git add {}'.format(' '.join(files)))
            local("git commit -m '{}'".format(now))
        _debug('Uploading local changes...')
        local('git push origin master')


def _setup_remote_env():
    _debug('Checking if the virtualenv dir was created in remote server...')
    virtual_env_dir = '/var/opt/.virtualenvs'
    if not exists(virtual_env_dir):
        _debug('Creating dir {}'.format(virtual_env_dir))
        run('mkdir -p {}'.format(virtual_env_dir))
    project_env_dir = os.path.join(virtual_env_dir, project_name)
    _debug('Checking if virtualenv for the project was created...')
    if not exists(project_env_dir):
        with shell_env(WORKON_HOME=virtual_env_dir):
            _debug('Creating virtual env {}'.format(project_name))
            run('source /usr/local/bin/virtualenvwrapper.sh && mkvirtualenv --python=/usr/bin/python3 {}'.format(project_name))


def _setup_remote_project():
    with cd(remote_project_dir):
        _debug('Checking project requirements..')
        if exists('requirements.txt'):
            virtual_env_dir = '/var/opt/.virtualenvs'
            with shell_env(WORKON_HOME=virtual_env_dir):
                _debug('Installing/Updating project requirements...')
                run('source /usr/local/bin/virtualenvwrapper.sh && workon {} && pip3 install "djangoplus[production]"'.format(project_name))
                run('source /usr/local/bin/virtualenvwrapper.sh && workon {} && pip3 install --upgrade pip'.format(project_name))
                run('source /usr/local/bin/virtualenvwrapper.sh && workon {} && pip3 install -U -r requirements.txt'.format(project_name))
        _debug('Checking if necessary dirs (logs, media and static) were created...')
        run('mkdir -p logs')
        run('mkdir -p static')
        run('mkdir -p media')
        _debug('Granting access to www-data...')
        run('chown -R www-data.www-data .')


def _check_domain():
    if settings.DIGITAL_OCEAN_DOMAIN:

        url = 'https://api.digitalocean.com/v2/domains'
        command = '''curl -X GET -H 'Content-Type: application/json' -H 'Authorization: Bearer {}' "{}/{}"'''.format(settings.DIGITAL_OCEAN_TOKEN, url, settings.DIGITAL_OCEAN_DOMAIN)
        _debug('Checking if domain {} was created...'.format(settings.DIGITAL_OCEAN_DOMAIN))
        data = json.loads(local(command, capture=True))
        if data.get('id', None) == 'not_found':
            _debug('Creating domain {}...'.format(settings.DIGITAL_OCEAN_DOMAIN))
            ip_address = env.hosts[0]
            command = '''curl -X POST -H 'Content-Type: application/json' -H 'Authorization: Bearer {}' -d '{{"name":"{}","ip_address":"{}"}}' "{}"'''.format(settings.DIGITAL_OCEAN_TOKEN, settings.DIGITAL_OCEAN_DOMAIN, ip_address, url)
            data = json.loads(local(command, capture=True))

        ip_address = None

        try:
            ip_address = local('dig {} a +short'.format(settings.DIGITAL_OCEAN_DOMAIN), capture=True).strip()
        except Exception as e:
            print(e)

        if ip_address != env.hosts[0]:
            _debug('The domain is not activated yet. The ip {} is going to be used for the deploy.'.format(env.hosts[0]))
            return None

    return settings.DIGITAL_OCEAN_DOMAIN


def _print_remote_url():
    file_path = '/etc/nginx/sites-enabled/{}'.format(project_name)
    local_file_path = '/tmp/nginx.tmp'
    get(file_path, local_file_path)
    file_content = open(local_file_path).read()
    server_name = None
    port = None
    for line in file_content.split('\n'):
        if 'server_name ' in line:
            server_name = line.strip().split()[1].replace(';', '')
        elif 'listen ' in line:
            port = line.strip().split()[1].replace(';', '')
    url = 'http://{}'.format(server_name)
    if int(port) != 80:
        url = '{}:{}'.format(url, port)
    print(('\n\n\nURL: {}\n\n'.format(url)))


def _setup_nginx_file():
    file_path = '/etc/nginx/sites-enabled/{}'.format(project_name)
    _debug('Checking nginx file {}...'.format(file_path))
    checked_domain = _check_domain()
    if exists(file_path):
        local_file_path = '/tmp/nginx.tmp'
        get(file_path, local_file_path)
        file_content = open(local_file_path, 'r').read()
        if checked_domain and checked_domain not in file_content:
            content = []
            for line in file_content.split('\n'):
                if 'server_name ' in line:
                    line = line.replace('server_name', 'server_name {}'.format(checked_domain))
                elif 'listen ' in line:
                    line = '    listen 80;'
                content.append(line)
            file_descriptor = open('/tmp/nginx.tmp', 'w')
            file_descriptor.write('\n'.join(content))
            put(file_descriptor, file_path)
            _debug('Restarting nginx...')
            run('/etc/init.d/nginx restart')
    else:
        _debug('Creating nginx file {}...'.format(file_path))
        local_port = _available_port()
        if checked_domain:
            port = 80
            server_name = checked_domain
        else:
            port = local_port + 1000
            server_name = env.hosts[0]
        text = NGINEX_FILE_CONTENT.format(project_name=project_name, server_name=server_name, port=port, local_port=local_port)
        append(file_path, text)
        _debug('Nginx configured with {}:{}'.format(server_name, port))
        _debug('Restarting nginx...')
        run('/etc/init.d/nginx restart')


def _setup_supervisor_file():
    file_path = '/etc/supervisor/conf.d/{}.conf '.format(project_name)
    _debug('Checking supervisor file {}...'.format(file_path))
    if not exists(file_path):
        _debug('Creating supervisor file {}...'.format(file_path))
        text = SUPERVISOR_FILE_CONTENT.format(project_name=project_name)
        append(file_path, text)
        _debug('Reloading supervisorctl...')
        run('supervisorctl reload')


def _setup_gunicorn_file():
    file_path = '/var/opt/{}/gunicorn_start.sh '.format(project_name)
    _debug('Checking gunicorn file {}...'.format(file_path))
    if not exists(file_path):
        _debug('Creating gunicorn file {}'.format(file_path))
        port = _available_port()
        text = GUNICORN_FILE_CONTENT.format(project_name=project_name, port=port)
        append(file_path, text)
        run('chmod a+x {}'.format(file_path))


def _setup_remote_webserver():
    _setup_nginx_file()
    _setup_supervisor_file()
    _setup_gunicorn_file()


def _reload_remote_application():
    _debug('Updating project in remote server...')
    with cd(remote_project_dir):
        virtual_env_dir = '/var/opt/.virtualenvs'
        with shell_env(WORKON_HOME=virtual_env_dir):
            run('source /usr/local/bin/virtualenvwrapper.sh && workon {} && python manage.py sync'.format(project_name))
            run('chown -R www-data.www-data .')
            run('chmod a+w *.db')
            run('ls -l')
            _debug('Restarting supervisorctl...')
            run('supervisorctl restart {}'.format(project_name))


def _delete_remote_project():
    _debug('Deleting remove project...')
    if exists(remote_project_dir):
        run('rm -r {}'.format(remote_project_dir))


def _delete_remote_env():
    _debug('Deleting remote env...')
    run('source /usr/local/bin/virtualenvwrapper.sh && rmvirtualenv {}'.format(project_name))


def _delete_domain():
    url = 'https://api.digitalocean.com/v2/domains'
    if settings.DIGITAL_OCEAN_DOMAIN:
        _debug('Deleting domain {}...'.format(settings.DIGITAL_OCEAN_DOMAIN))
        command = '''curl -X DELETE -H 'Content-Type: application/json' -H 'Authorization: Bearer {}' "{}/{}"'''.format(settings.DIGITAL_OCEAN_TOKEN, url, settings.DIGITAL_OCEAN_DOMAIN)
        local(command)


def _delete_repository():
    project_git_dir = '/home/git/{}.git'.format(project_name)
    if exists(project_git_dir):
        run('rm -r {}'.format(project_git_dir))


def _delete_local_repository():
    _debug('Deleting local repository...')
    with cd(project_dir):
        local('rm -rf .git')


def _delete_nginx_file():
    _debug('Deleting nginx file...')
    file_path = '/etc/nginx/sites-enabled/{} '.format(project_name)
    if exists(file_path):
        run('rm {}'.format(file_path))


def _delete_supervisor_file():
    _debug('Deleting supervisor file..')
    file_path = '/etc/supervisor/conf.d/{}.conf'.format(project_name)
    if exists(file_path):
        run('rm {}'.format(file_path))


def _reload_remote_webserver():
    _debug('Reloading supervisorctl...')
    run('supervisorctl reload')
    _debug('Reloading nginx...')
    run('/etc/init.d/nginx restart')
    _debug('Starting supervisor...')
    run('service supervisor start')


def _configure_crontab():
    _debug('Configuring crontab...')
    output = run("crontab -l")
    line = '0 * * * * /var/opt/.virtualenvs/{}/bin/python /var/opt/{}/manage.py backup >/tmp/cron.log 2>&1'.format(
    project_name, project_name)
    if line not in output:
        run('crontab -l | { cat; echo "{}"; } | crontab -'.format(line))


def _check_droplet():
    _check_local_keys()

    url = 'https://api.digitalocean.com/v2/droplets/'
    command = '''curl -X GET -H 'Content-Type: application/json' -H 'Authorization: Bearer {}' "{}"'''.format(settings.DIGITAL_OCEAN_TOKEN, url)
    _debug('Checking if droplet exists...')
    response = json.loads(local(command, capture=True))

    for droplet in response['droplets']:
        ip_address = droplet['networks']['v4'][0]['ip_address']
        if droplet['name'] == project_name or ip_address == settings.DIGITAL_OCEAN_SERVER:
            _debug('Droplet found with IP {}'.format(ip_address))
            local_home_dir = local('echo $HOME', capture=True)
            local_known_hosts_path = os.path.join(local_home_dir, '.ssh/known_hosts')
            _debug('Checking if file {} exists...'.format(local_known_hosts_path))
            if not os.path.exists(local_known_hosts_path):
                _debug('Creating empty file {}...'.format(local_known_hosts_path))
                local('touch {}'.format(local_known_hosts_path))
            local_known_hosts_file_content = open(local_known_hosts_path, 'r').read()
            if ip_address not in local_known_hosts_file_content:
                _debug('Registering {} as known host...'.format(ip_address))
                time.sleep(5)
                local('ssh-keyscan -T 15 {} >> {}'.format(ip_address, local_known_hosts_path))
                if settings.DIGITAL_OCEAN_SERVER not in local_known_hosts_file_content:
                    _debug('Registering {} as known host...'.format(settings.DIGITAL_OCEAN_SERVER))
                    local('ssh-keyscan {} >> {}'.format(settings.DIGITAL_OCEAN_SERVER, local_known_hosts_path))
            return ip_address

    _debug('No droplet cound be found for the project')


def _create_droplet():
    # curl -X GET --silent "https://api.digitalocean.com/v2/images?per_page=999" -H "Authorization: Bearer XXXXXXX"
    _check_local_keys()
    if settings.DIGITAL_OCEAN_TOKEN:
        url = 'https://api.digitalocean.com/v2/account/keys'
        _debug('Getting installed keys at digital ocean...')
        command = '''curl -X GET -H 'Content-Type: application/json' -H 'Authorization: Bearer {}' "{}"'''.format(settings.DIGITAL_OCEAN_TOKEN, url)
        response = json.loads(local(command, capture=True))
        # print response
        ssh_keys = []
        for ssh_key in response['ssh_keys']:
            ssh_keys.append(ssh_key['id'])

        _debug('Creating droplet...')
        url = 'https://api.digitalocean.com/v2/droplets/'
        command = '''curl -X POST -H 'Content-Type: application/json' -H 'Authorization: Bearer {}' -d '{{"name":"{}","region":"{}","size":"{}","image":"{}", "ssh_keys":{}}}' "{}"'''.format(settings.DIGITAL_OCEAN_TOKEN, project_name, 'nyc3', '512mb', 'debian-9-x64', ssh_keys, url)
        response = json.loads(local(command, capture=True))
        droplet_id = response['droplet']['id']

        time.sleep(10)

        url = 'https://api.digitalocean.com/v2/droplets/{}/'.format(droplet_id)
        command = '''curl -X GET -H 'Content-Type: application/json' -H 'Authorization: Bearer {}' "{}"'''.format(settings.DIGITAL_OCEAN_TOKEN, url)
        response = json.loads(local(command, capture=True))
        ip_address = response['droplet']['networks']['v4'][0]['ip_address']
        _debug('Droplet created with IP {}!'.format(ip_address))
        _update_settings_file(ip_address)
        return _check_droplet()

    _debug('Please, set the DIGITAL_OCEAN_TOKEN value in settings.py file')
    sys.exit()


def _execute_aptget():
    with cd('/'):
        if not exists('/swap.img'):
            run('apt-get update')

            run('apt-get -y install python-pip')
            run('pip install virtualenv virtualenvwrapper')

            run('apt-get -y install python3 python3-pip build-essential python3-dev git nginx supervisor libncurses5-dev')
            run('apt-get -y install vim')
            run('apt-get -y install libjpeg62-turbo-dev libfreetype6-dev libtiff5-dev liblcms2-dev libwebp-dev tk8.6-dev libjpeg-dev')
            run('apt-get -y install htop')

            if not contains('/etc/security/limits.conf', '65536'):
                # print LIMITS_FILE_CONTENT
                append('/etc/security/limits.conf', LIMITS_FILE_CONTENT)

            run('pip3 install --upgrade pip')

            if not contains('/root/.bashrc', 'WORKON_HOME'):
                # print BASHRC_FILE_CONTENT
                append('/root/.bashrc', BASHRC_FILE_CONTENT)

            if not exists('/swap.img'):
                run('lsb_release -a')
                run('dd if=/dev/zero of=/swap.img bs=1024k count=2000')
                run('mkswap /swap.img')
                run('swapon /swap.img')
                run('echo "/swap.img    none    swap    sw    0    0" >> /etc/fstab')


def _update_settings_file(ip):
    _debug('Updating settings.py file with {} for DIGITAL_OCEAN_SERVER'.format(ip))
    settings_file_path = os.path.join(settings.BASE_DIR, '{}/settings.py'.format(project_name))
    content = []
    settings_file = open(settings_file_path)
    lines = settings_file.read().split('\n')
    settings_file.close()
    for line in lines:
        if 'DIGITAL_OCEAN_SERVER' in line:
            line = 'DIGITAL_OCEAN_SERVER = \'{}\''.format(ip)
        content.append(line)
    content_str = '\n'.join(content)
    print(content_str)
    settings_file = open(settings_file_path, 'w')
    settings_file.write(content_str)
    settings_file.close()


def backupdb():
    local_home_dir = local('echo $HOME', capture=True)
    backup_dir = os.path.join(local_home_dir, 'backup')
    if not os.path.exists(backup_dir):
        local('mkdir -p {}'.format(backup_dir))
    with cd('/var/opt'):
        for entry in run('ls').split():
            file_name = '/var/opt/{}/sqlite.db'.format(entry)
            bakcup_file_name = os.path.join(backup_dir, '{}.db'.format(entry))
            if exists(file_name):
                command = 'scp {}@{}:{} {}'.format(username, env.hosts[0], file_name, bakcup_file_name)
                local(command)


def deploy():
    _execute_aptget()
    _check_remote_keys()
    _setup_local_repository()
    _push_local_changes()
    _setup_remote_env()
    _setup_remote_repository()
    _setup_remote_project()
    _setup_remote_webserver()
    _reload_remote_application()
    _print_remote_url()


def update():
    _push_local_changes()
    _setup_remote_repository()
    _setup_remote_project()
    _reload_remote_application()
    _setup_nginx_file()
    _print_remote_url()


def push():
    _push_local_changes()
    _setup_remote_repository()
    _reload_remote_application()
    _print_remote_url()


def undeploy():
    _delete_remote_project()
    _delete_domain()
    _delete_repository()
    _delete_local_repository()
    _delete_nginx_file()
    _delete_supervisor_file()
    _reload_remote_webserver()
    _delete_remote_env()


