# NExtSEEK
 Extending SEEK for active management of scientific metadata
 
## License
Copyright (c) 2021, BioMicro Center & Bioinformatics Core, Massachusetts Institute of Technology: [MIT license](LICENSE)

## About NExtSEEK
NExtSEEK is a modified wrapper around the [SEEK](https://github.com/seek4science/seek) platform
that allows active data management by establishing more discrete sample types which are mutable to permit the expansion of the types of
metadata, allowing researchers to track additional information. The use of discrete
nodes also converts assays from nodes to edges, creating a network model of the
study,   and  more   accurately   representing  the   experimental   process.   With  these
changes   to   SEEK,   users   are   able   to   collect   and   organize   the   information   that
researchers need to improve reusability and reproducibility as well as to make data
and metadata available to the scientific community through public repositories.


## Release notes

#### Version 1.1.0
Release date: *12 February 2023*

This release includes the implementation of the following functionalities.

##### Advanced search
A major implementation of the advanced search on sample metadata allows

    * a pubMed style text search builder;
    * any combination of multiple AND/OR/NOT queries;
    * user-friendly metadata display
    * filtering of search output;
    * filtering of sample attributes;
    * bulk search/download by sample UIDs.

##### Separation of the creator and submitter in asset uploading for samples, SOPs and data files

During the process of assets uploading for samples, SOPs or data files, the login user is regarded as the creator of assets by default, which is true if lab users take care their own asset uploading. However, it's not always the case. Sometimes, a lab manager or a project admin may upload assests on behlaf of the creator of assets. To correctly assign assests to the right creator, instead of under the name of the login user by default, additional options are provided on the sample or SOP/data file uploading page, for selecting the lab and the lab user, who substitutes the login user as the right creator of assets, while the login user is stored as the submitter or contributor of the corresponding assets. The current release covers the revision on the user interfaces for uploading assay sheet and SOP/data files, as well as on the server side code to deal with the asset creator and submitter.


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

## Checklist for Preparing to Use NExtSEEK
#### Identify key samples and data to deposit 
The NIH and journals will generally require:
* The rawest form of the generated data – i.e. the immediate output from the instruments used or direct observations and measurements from experiments
* Processed data which is central to the work – e.g. gene expression count matrices and spectra features 
* Unique materials integral to the work – e.g. unique chemical compounds, plasmids, or cell lines
* Code necessary for processing raw data into the interpreted dataset

#### Identify FAIR-compliant field-specific repositories for data and samples
Repositories should conform to the FAIR data standards and, where possible, be well utilized in their respective fields. Examples include GEO, PRIDE, MGI, etc. Lists of available repositories can be found at Nature (https://www.nature.com/sdata/policies/repositories) and FairSharing (fairsharing.org). Where field-specific repositories do not exist, researchers can deposit to general repositories such as FigShare (figshare.com), Dryad (datadryad.org), and Zenodo (zenodo.org).

#### Identify relevant ontologies for their field
When collecting metadata, users should use shared language for interoperability. Users should pull language from the most relevant ontology to their field. Researchers can search for ontologies through the EMBL-EBI (https://www.ebi.ac.uk/ols/index) and BioPortal (https://bioportal.bioontology.org/ontologies). Recommended ontologies to pull from are the NCI Thesaurus, Experimental Factor Ontology, and the BRENDA Tissue Ontology.

#### Identify key metadata required by the repository of choice 
These metadata will vary by endpoint, but the collected metadata should fulfill the following criteria to be FAIR compliant:
* Use a formal and shared language for knowledge representation, drawn from established ontologies where possible
* Include qualified references to other data and metadata where relevant
* Include detailed provenance, such as references to parent samples
* Include protocols and code which are open, free, and universally implementable
* Metadata should be richly described with accurate and relevant attributes

#### Identify additional critical metadata 
To maximize impact and reusability, researchers should try to collect the following information: 
* Experimental groups and cohorts
* Variables and parameters that change between experiments
* Known potential covariates
* Scientists responsible for samples and experiments
* Tools and instruments (including model and software versions)
* Reagents (including manufacturers and lot numbers)
* Treatments
* Target analytes, antibodies, stains, reporters, etc.

## Contact Us
For question in setting up the system or reporting bugs, please visit [BioMicro Center, MIT](https://biology.mit.edu/tile/biomicro-center/).



