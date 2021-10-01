# NExtSEEK
 Extending SEEK for active management of scientific metadata
 
## License
Copyright (c) 2021, BioMicro Center & Bioinformatics Core, Massachusetts Institute of Technology: 

[BSD 3-clause](LICENSE)

## About NExtSEEK
NExtSEEK is a modified wrapper around the [SEEK](https://github.com/seek4science/seek) platform
that allows active data management by establishing more discrete sample types which are mutable to permit the expansion of the types of
metadata, allowing researchers to track additional information. The use of discrete
nodes also converts assays from nodes to edges, creating a network model of the
study,   and  more   accurately   representing  the   experimental   process.   With  these
changes   to   SEEK,   users   are   able   to   collect   and   organize   the   information   that
researchers need to improve reusability and reproducibility as well as to make data
and metadata available to the scientific community through public repositories.

## Dependencies
NExtSEEK is implemented on top of [Mezzanine 4.2.3](http://mezzanine.jupo.org/), which is a Django CMS based on Django 1.10.7 and python 2.7. 
NExtSEEK also requires the following packages to be installed in a virtual environment:

* BeautifulSoup==3.2.1
* beautifulsoup4==4.6.0
* bleach==2.0.0
* bunch==1.0.1
* certifi==2017.4.17
* chardet==3.0.4
* deepmerge==0.2.1
* Django==1.10.7
* django-contrib-comments==1.8.0
* django-crontab==0.7.1
* django-realtime==1.1
* django-rest-framework==0.1.0
* django-widget-tweaks==1.4.3
* djangorestframework==3.9.4
* et-xmlfile==1.0.1
* filebrowser-safe==0.4.7
* fpdf==1.7.2
* future==0.16.0
* grappelli-safe==0.4.6
* h5py==2.9.0
* html5lib==0.999999999
* idna==2.5
* immpload==1.1.2
* inflection==0.3.1
* isodate==0.6.0
* jdcal==1.4
* joblib==0.14.1
* lxml==4.2.5
* Markdown==3.1.1
* Mezzanine==4.2.3
* mysqlclient==1.4.4
* numpy==1.14.5
* oauthlib==2.0.2
* olefile==0.44
* openpyxl==2.5.4
* pandas==0.23.3
* parse==1.12.1
* pathlib==1.0.1
* Pillow==4.2.1
* PyMySQL==0.8.1
* pyparsing==2.4.2
* python-dateutil==2.7.3
* python-docx==0.8.7
* pytz==2017.2
* PyYAML==5.4.1
* rdflib==4.2.2
* reportlab==3.5.0
* requests==2.18.1
* requests-oauthlib==0.8.0
* simplejson==3.15.0
* six==1.10.0
* SPARQLWrapper==1.8.4
* tzlocal==1.4
* Unidecode==1.0.22
* urllib3==1.21.1
* webencodings==0.5.1
* xlwt==1.3.0

Further upgrade of NExtSEEK from python2.7 to python3 will rely on the availability of the latest version of Mezzanine in python3. 

## Installation

We recommend installing NExtSEEK on Ubuntu.
#### Get NExtSEEK

```bash
mkdir NExtSEEK
cd NExtSEEK
git clone https://github.com/BMCBCC/NExtSEEK
```
#### Install dependencies
It is recommened to install NExtSEEK in a virtual environment,

```bash
sudo apt install virtualenv
virtualenv -p /usr/bin/python2.7 ../venv_django_1.10
source ../venv_django_1.10/bin/activate
pip install -r requirements.txt
```

#### Create the project
With the virtual environment activated, create the project,

```bash
cd ../NExtSEEK
mezzanine-project NExtSEEK
```

## Configuration

In our local installation of NExtSEEK, we have applied a theme called SmartAdmin, which can be downloaded from [SmartAdmin - Responsive WebApp](https://wrapbootstrap.com/theme/smartadmin-responsive-webapp-WB0573SK0) with an expense.
Unzip the package of SmartAdmin theme into the subfolder: NExtSEEK/themes/SmartAdmin.

#### Change SEEK configuration

Open settings.py in the NExtSEEK folder and set the following variables:

```bash

INSTALLED_APPS = (
    "seek",
    'themes.SmartAdmin',
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.redirects",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.sitemaps",
    "django.contrib.staticfiles",
    "mezzanine.boot",
    "mezzanine.conf",
    "mezzanine.core",
    "mezzanine.generic",
    "mezzanine.pages",
    "mezzanine.blog",
    "mezzanine.forms",
    "mezzanine.galleries",
    "mezzanine.twitter",
    "mezzanine.accounts",
    "mezzanine.mobile",
    
    'widget_tweaks',
    'django_crontab',
)

SEEK_URL = "http://127.0.0.1:3000"
DATABASE_ROUTERS = ['seek.dbrouters.CustomRouter']



```

which refers to a Seek instance installed locally on the same computer. Change the IP address of the Seek server accordingly.




#### Run NExtSEEK

```bash
python manage.py runserver 0.0.0.0:8080
```
## References

NExtSEEK: Extending SEEK for active management of scientific metadata, Dikshant Pradhan, Huiming Ding, Jingzhi Zhu, Bevin P. Engelward, and Stuart S.
Levin, MIT BioMicro Center, Department of Biology, Massachusetts Institute of Technology, Cambridge, MA, USA

## Contact Us
For question in setting up the system or reporting bugs, please visit [BioMicro Center, MIT](https://biology.mit.edu/tile/biomicro-center/).



