# NExtSEEK
 Extending SEEK for active management of scientific metadata
 
## License
Copyright (c) 2021, BioMicro Center & Bioinformatics Core, Massachusetts Institute of Technology: [MIT license](LICENSE)

## About NExtSEEK
NExtSEEK is a modified wrapper around the [SEEK](https://github.com/seek4science/seek) platform
that allows active data management by establishing more discrete sample types which are mutable to permit the expansion of the types of metadata, allowing researchers to track additional information. The use of discrete nodes also converts assays from nodes to edges, creating a network model of the study, and more accurately representing the experimental process. With these changes to SEEK, users are able to collect and organize the information that researchers need to improve reusability and reproducibility as well as to make data and metadata available to the scientific community through public repositories.

## Release notes

### Version 1.1.0
Release date: *12 February 2023*

This release includes the implementation of two major functionalities.

#### Advanced search
The advanced search on sample metadata is implemented with the following features:
- a pubMed style text search builder;
- any combination of multiple AND/OR/NOT queries;
- user-friendly metadata display
- filtering of search output;
- filtering of sample attributes;
- bulk search/download by sample UIDs.

#### Separation of the creator and submitter in asset uploading for samples, SOPs and data files
During the process of assets uploading for samples, SOPs or data files, the login user is regarded as the creator of assets by default, which is usually true if lab users take care their own asset uploading. However, sometimes, a lab manager or a project admin may upload assets on behalf of the creator of assets. To correctly assign assets to the right creator, instead of under the name of the login user by default, additional options are provided on the sample or SOP/data file uploading page, for selecting the lab and the lab user, who substitutes the login user as the right creator of assets, while the login user is stored as the submitter or contributor of the corresponding assets.
 
The current release covers the revision on the user interfaces for uploading assay sheet and SOP/data files, as well as on the server side code to deal with the asset creator and submitter.

## Dependencies

NExtSEEK is implemented on top of [Mezzanine](http://mezzanine.jupo.org/), a Django CMS. NExtSEEK also requires the packages enumerated in the `requirements.txt` file.

## Installation

We recommend installing NExtSEEK on Ubuntu.

If you attempt to install NExtSEEK on RHEL 9> and you encounter issues installing the `mysqlclient` Python package, install `mariadb-connector-c-devel` using your system's package manager. For example:

```bash
sudo yum install mariadb-connector-c-devel
```

### Get NExtSEEK

```bash
git clone https://github.com/asoberan/NExtSEEK
```

### Install dependencies
It is recommended to install NExtSEEK in a virtual environment.

```bash
python3 -m venv ../venv_nextseek
source ../venv_nextseek/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

## Configuration

In our local installation of NExtSEEK, we have applied a theme called SmartAdmin, which can be downloaded from [SmartAdmin - Responsive WebApp](https://wrapbootstrap.com/theme/smartadmin-responsive-webapp-WB0573SK0) with an expense.
Unzip the package of SmartAdmin theme into the subfolder: `themes/SmartAdmin`.

### Change SEEK configuration

Open settings.py in the `dmac` folder and set the following variables:

```bash
SEEK_URL = "http://127.0.0.1:3000"
```

which refers to a Seek instance installed locally on the same computer. Change the IP address of the Seek server accordingly.

With the configuration done, run the following for Django to initialize the database;

```bash
python3 manage.py makemigrations
python3 manage.py migrate
```

## Run NExtSEEK

### Development Server

```bash
python3 manage.py runserver 0.0.0.0:8080
```

Open http://localhost:8080 in your browser.

### Production Gunicorn Server

Gunicorn does not serve static files, it only runs the Django app. Static files should ideally be served by a web server, such as nginx or Apache. Django has a built-in way of collecting all static files and placing them in `STATIC_ROOT` set in `dmac/settings.py`. Then, you point your web server to this directory.

```bash
# Collect your static files and place them in STATIC_ROOT
python3 manage.py collectstatic

# Run the gunicorn server
gunicorn --bind 0.0.0.0:8080 \
         --timeout 600 \
         --workers 4 \
         dmac.wsgi
```

Gunicorn should also not be used as the main server. Instead, your web server should proxy requests from `http://your_domain.com` to the address Gunicorn is running at.

An example Apache configuration would look like this, assuming you have `mod_proxy` installed and loaded in Apache:

```Apache
<VirtualHost *:80>
  ServerName    your_domain.com
  ErrorLog      /var/log/httpd/nextseek.error.log
  CustomLog     /var/log/httpd/nextseek.custom.log combined

  # Proxy requests to http://your_domain.com
  # to the internal Gunicorn server at
  # http://127.0.0.1:8080
  
  ProxyPreserveHost     On
  ProxyPass     / http://127.0.0.1:8080/ Keepalive=On timeout=600
  ProxyPassReverse / http://127.0.0.1:8080/
    
  # Do not proxy requests to
  # https://your_domain.com/<value of STATIC_URL in your dmac/settings.py>
  # to the Gunicorn server since it doesn't
  # handle serving those files
  ProxyPass     <STATIC_URL value> !
    
  # Any requests to http://nextseek.your_domain.com/<value of STATIC_URL in your dmac/settings.py>
  # should instead be an alias to the files located at
  # whatever STATIC_ROOT is set to in dmac/settings.py
  Alias <STATIC_URL value>       <STATIC_ROOT value>

  # Give apache permissions to access the static files
  <Directory <STATIC_ROOT value> >
    Require all granted
  </Directory>
</VirtualHost>
```

**It's best to set the timeout value on the "ProxyPass" line to something high and equal to the timeout set in Gunicorn.**

After starting your web server, you should be able to go to http://your_domain.com and NExtSEEK will be running. It's advised that you add TLS encryption to your domain so that users' passwords aren't sent to the server in plaintext. The simplest way of doing this is using [certbot](https://certbot.eff.org/).

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
