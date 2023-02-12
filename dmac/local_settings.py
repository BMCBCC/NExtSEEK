DEBUG = True

SECRET_KEY = "your_own_key from Django"
NEVERCACHE_KEY = "your_own_key_from Django"

DATABASES = {
    # this is the NExtSEEK database
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "NExtSEEK",
        "USER": "username",
        "PASSWORD": "password",
        "HOST": "localhost",
        "PORT": "3306",
    },
    # This is the SEEK database
    "seek": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "seek_production",
        "USER": "username",
        "PASSWORD": "password",
        "HOST": "localhost",
        "PORT": "3306",
    }
}

###################
# DEPLOY SETTINGS #
###################

# Domains for public site
# ALLOWED_HOSTS = [""]

# These settings are used by the default fabfile.py provided.
# Check fabfile.py for defaults.

# FABRIC = {
#     "DEPLOY_TOOL": "rsync",  # Deploy with "git", "hg", or "rsync"
#     "SSH_USER": "",  # VPS SSH username
#     "HOSTS": [""],  # The IP address of your VPS
#     "DOMAINS": ALLOWED_HOSTS,  # Edit domains in ALLOWED_HOSTS
#     "REQUIREMENTS_PATH": "requirements.txt",  # Project's pip requirements
#     "LOCALE": "en_US.UTF-8",  # Should end with ".UTF-8"
#     "DB_PASS": "",  # Live database password
#     "ADMIN_PASS": "",  # Live admin user password
#     "SECRET_KEY": SECRET_KEY,
#     "NEVERCACHE_KEY": NEVERCACHE_KEY,
# }
