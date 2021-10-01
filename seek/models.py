from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User

from mezzanine.pages.models import Page
from dmac.conversion import dateconversion, toDate
from datetime import date

from django.conf import settings
SEEK_DATABASE = settings.SEEK_DATABASE

class Users(models.Model):
    # tell which database to use
    _DATABASE = SEEK_DATABASE
    
    login = models.CharField(max_length=255, default=None)
    crypted_password = models.CharField(max_length=255, default=None)
    salt = models.CharField(max_length=255, default=None)
    created_at = models.DateTimeField(null=False)
    updated_at = models.DateTimeField(null=False)
    remember_token = models.CharField(max_length=255, default=None)
    remember_token_expires_at = models.DateTimeField(null=False)
    activation_code = models.CharField(max_length=255, default=None)
    activated_at = models.DateTimeField(null=False)
    person_id = models.IntegerField(default=None)
    reset_password_code = models.CharField(max_length=255, default=None)
    reset_password_code_until = models.DateTimeField(null=False)
    posts_count = models.IntegerField(default=None)
    last_seen_at = models.DateTimeField(null=False)
    uuid = models.CharField(max_length=255, default=None)
    
    def __unicode__(self):
        return self.login
    
    class Meta:
        # define the custom database table name, different from the default name.
        db_table = "users"

class People(models.Model):
    # tell which database to use
    _DATABASE = SEEK_DATABASE
    
    created_at = models.DateTimeField(null=False)
    updated_at = models.DateTimeField(null=False)
    first_name = models.CharField(max_length=255, default=None)
    last_name = models.CharField(max_length=255, default=None)
    email = models.CharField(max_length=255, default=None)
    phone = models.CharField(max_length=255, default=None)
    skype_name = models.CharField(max_length=255, default=None)
    web_page = models.CharField(max_length=255, default=None)
    description = models.TextField(default=None)
    avatar_id = models.IntegerField(default=None)
    status_id = models.IntegerField(default=None)
    first_letter = models.CharField(max_length=1, default=None)
    uuid = models.CharField(max_length=255, default=None)
    roles_mask = models.IntegerField(default=None)
    orcid = models.CharField(max_length=255, default=None)
    
    def __unicode__(self):
        return self.email
    
    class Meta:
        # define the custom database table name, different from the default name.
        db_table = "people"


# Custom mezzanine User Profile table, which is an one-to-one extension of the default auth_user table.
# Refer to http://mezzanine.jupo.org/docs/user-accounts.html
# This table replaces data_user and data_user_role tables below, which will be deleted in future release.
PROJECT_CHOICES = (
    ("Undefined", "Undefined"),
    ("IMPAcTb", "IMPAcTb"),
    ("MIT_SRP", "MIT_SRP")
)

class User_profile(models.Model):
    user = models.OneToOneField("auth.User", on_delete=models.CASCADE)
    project = models.CharField(max_length=255, choices=PROJECT_CHOICES, editable = True)
    #institute = models.CharField(max_length=255)
    laboratory = models.TextField()
    
    def loginname(self):
        return self.user.username
    
    def fullname(self):
        name = self.user.first_name + ' ' + self.user.last_name
        return name

    def __unicode__(self):
        return self.fullname()

class Sample_types(models.Model):
    # tell which database to use
    _DATABASE = SEEK_DATABASE
    
    title = models.CharField(max_length=255, default=None)
    uuid = models.CharField(max_length=255, default=None)
    created_at = models.DateTimeField(null=False)
    updated_at = models.DateTimeField(null=False)
    first_letter = models.CharField(max_length=1, default=None)
    description = models.TextField(default=None)
    uploaded_template = models.BooleanField(default=0)
    contributor_id = models.IntegerField(default=None)
    deleted_contributor = models.CharField(max_length=255, default=None)
    
    def __unicode__(self):
        return self.uuid
    
    class Meta:
        # define the custom database table name, different from the default name.
        db_table = "sample_types"
        
class Sample_attributes(models.Model):
    # tell which database to use
    _DATABASE = SEEK_DATABASE
    
    #id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255, default=None)
    #sample_attribute_type_id = models.IntegerField(default=None, primary_key=True)
    sample_attribute_type_id = models.IntegerField()
    required = models.BooleanField(default=0)
    created_at = models.DateTimeField(null=False)
    updated_at = models.DateTimeField(null=False)
    
    pos = models.IntegerField(default=None)
    #sample_type_id = models.IntegerField(default=None, primary_key=True)
    sample_type_id = models.IntegerField()
    unit_id = models.IntegerField(default=None)
    is_title = models.BooleanField(default=0)
    template_column_index = models.IntegerField(default=None)
    accessor_name = models.CharField(max_length=255, default=None)
    sample_controlled_vocab_id = models.IntegerField(default=None)
    linked_sample_type_id = models.IntegerField(default=None)
    
    def __unicode__(self):
        return self.title
    
    class Meta:
        # define the custom database table name, different from the default name.
        db_table = "sample_attributes"        


class Sample_attribute_types(models.Model):
    # tell which database to use
    _DATABASE = SEEK_DATABASE
    
    title = models.CharField(max_length=255, default=None)
    base_type = models.CharField(max_length=255, default=None)
    regexp = models.CharField(max_length=255, default=None)
    
    created_at = models.DateTimeField(null=False)
    updated_at = models.DateTimeField(null=False)
    
    placeholder = models.CharField(max_length=255, default=None)
    description = models.CharField(max_length=255, default=None)
    resolution = models.CharField(max_length=255, default=None)
    
    def __unicode__(self):
        return self.title
    
    class Meta:
        # define the custom database table name, different from the default name.
        db_table = "sample_attribute_types"           
        
class Samples(models.Model):
    # tell which database to use
    _DATABASE = SEEK_DATABASE
    
    title = models.CharField(max_length=255, default=None)
    #sample_type_id = models.IntegerField(default=None, primary_key=True)
    sample_type_id = models.IntegerField()
    json_metadata = models.TextField(default=None)
    uuid = models.CharField(max_length=255, default=None)
    contributor_id = models.IntegerField(default=None)
    policy_id = models.IntegerField(default=None)
    created_at = models.DateTimeField(null=False)
    updated_at = models.DateTimeField(null=False)
    first_letter = models.CharField(max_length=1, default=None)
    other_creators = models.TextField(default=None)
    originating_data_file_id = models.IntegerField(default=None)
    deleted_contributor = models.CharField(max_length=255, default=None)
    
    def __unicode__(self):
        return self.uuid
    
    class Meta:
        # define the custom database table name, different from the default name.
        db_table = "samples"

class Projects_samples(models.Model):
    ''' Refer to https://stackoverflow.com/questions/28516086/can-i-create-model-in-django-without-automatic-id
    This table does not have a primary key field
    
    '''
    # tell which database to use
    _DATABASE = SEEK_DATABASE
    
    project_id = models.IntegerField(default=None, primary_key=True)
    sample_id = models.IntegerField(default=None, primary_key=True)
    
    def __unicode__(self):
        uuid = str(self.project_id) + '-' + str(self.sample_id)
        return uuid
    
    class Meta:
        # define the custom database table name, different from the default name.
        db_table = "projects_samples"
        unique_together = ('project_id', 'sample_id')
        
        
class Documents(models.Model):
    # tell which database to use
    _DATABASE = SEEK_DATABASE
    
    title = models.CharField(max_length=255, default=None)
    description = models.TextField(default=None)
    contributor_id = models.IntegerField(default=None)
    version = models.IntegerField(default=1)
    first_letter = models.CharField(max_length=1, default=None)
    uuid = models.CharField(max_length=255, default=None)
    policy_id = models.IntegerField(default=None)
    doi = models.CharField(max_length=255, default=None)
    license = models.CharField(max_length=255, default=None)
    last_used_at = models.DateTimeField(null=False)
    created_at = models.DateTimeField(null=False)
    updated_at = models.DateTimeField(null=False)
    other_creators = models.TextField(default=None)
    deleted_contributor = models.CharField(max_length=255, default=None)
    
    def __unicode__(self):
        return self.uuid
    
    class Meta:
        # define the custom database table name, different from the default name.
        db_table = "documents"        
        
        
class Data_files(models.Model):
    # tell which database to use
    _DATABASE = SEEK_DATABASE
    
    contributor_id = models.IntegerField(default=None)
    title = models.CharField(max_length=255, default=None)
    description = models.TextField(default=None)
    template_id = models.IntegerField(default=None)
    last_used_at = models.DateTimeField(null=False)
    created_at = models.DateTimeField(null=False)
    updated_at = models.DateTimeField(null=False)
    version = models.IntegerField(default=1)
    first_letter = models.CharField(max_length=1, default=None)
    other_creators = models.TextField(default=None)
    uuid = models.CharField(max_length=255, default=None)
    policy_id = models.IntegerField(default=None)
    doi = models.CharField(max_length=255, default=None)
    license = models.CharField(max_length=255, default=None)
    simulation_data = models.BooleanField(default=0)
    deleted_contributor = models.CharField(max_length=255, default=None)
    
    def __unicode__(self):
        return self.uuid
    
    class Meta:
        # define the custom database table name, different from the default name.
        db_table = "data_files"
        
class Content_blobs(models.Model):
    # tell which database to use
    _DATABASE = SEEK_DATABASE
    
    md5sum = models.CharField(max_length=255, default=None)
    url = models.TextField(default=None)
    uuid = models.CharField(max_length=255, default=None)
    original_filename = models.CharField(max_length=255, default=None)
    content_type = models.CharField(max_length=255, default=None)
    asset_id = models.IntegerField(default=None)
    asset_type = models.CharField(max_length=255, default=None)
    asset_version = models.IntegerField(default=1)
    is_webpage = models.BooleanField(default=0)
    external_link = models.BooleanField(default=None)
    sha1sum = models.CharField(max_length=255, default=None)
    file_size = models.BigIntegerField(default=None)
    created_at = models.DateTimeField(default=None)
    updated_at = models.DateTimeField(default=None)
    
    def __unicode__(self):
        return self.uuid
    
    class Meta:
        # define the custom database table name, different from the default name.
        db_table = "content_blobs"
        
class Assay_assets(models.Model):
    # tell which database to use
    _DATABASE = SEEK_DATABASE
    
    assay_id = models.IntegerField(default=None)
    asset_id = models.IntegerField(default=None)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(default=None)
    updated_at = models.DateTimeField(default=None)
    relationship_type_id = models.IntegerField(default=None)
    asset_type = models.CharField(max_length=255, default=None)
    direction = models.IntegerField(default=None)
    
    def __unicode__(self):
        return self.assay_id
    
    class Meta:
        # define the custom database table name, different from the default name.
        db_table = "assay_assets"
                
class Policies(models.Model):
    # tell which database to use
    _DATABASE = SEEK_DATABASE
    
    name = models.CharField(max_length=255, default=None)
    sharing_scope = models.IntegerField(default=None)
    access_type = models.IntegerField(default=0)
    use_whitelist = models.BooleanField(default=None)
    use_blacklist = models.BooleanField(default=None)
    created_at = models.DateTimeField(null=False)
    updated_at = models.DateTimeField(null=False)
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        # define the custom database table name, different from the default name.
        db_table = "policies"                

class Permissions(models.Model):
    # tell which database to use
    _DATABASE = SEEK_DATABASE
    
    contributor_type = models.CharField(max_length=255, default=None)
    contributor_id = models.IntegerField(default=None)
    policy_id = models.IntegerField(default=None)
    access_type = models.IntegerField(default=0)
    created_at = models.DateTimeField(null=False)
    updated_at = models.DateTimeField(null=False)
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        # define the custom database table name, different from the default name.
        db_table = "permissions"                

class Sops(models.Model):
    # tell which database to use
    _DATABASE = SEEK_DATABASE
    
    contributor_id = models.IntegerField(default=None)
    title = models.CharField(max_length=255, default=None)
    description = models.TextField(default=None)
    created_at = models.DateTimeField(null=False)
    updated_at = models.DateTimeField(null=False)
    last_used_at = models.DateTimeField(null=False)
    version = models.IntegerField(default=1)
    first_letter = models.CharField(max_length=1, default=None)
    other_creators = models.TextField(default=None)
    uuid = models.CharField(max_length=255, default=None)
    policy_id = models.IntegerField(default=None)
    doi = models.CharField(max_length=255, default=None)
    license = models.CharField(max_length=255, default=None)
    deleted_contributor = models.CharField(max_length=255, default=None)
    
    def __unicode__(self):
        return self.uuid
    
    class Meta:
        # define the custom database table name, different from the default name.
        db_table = "sops"
        
class Assets_creators(models.Model):
    # tell which database to use
    _DATABASE = SEEK_DATABASE
    
    asset_id = models.IntegerField(default=None)
    creator_id = models.IntegerField(default=None)
    asset_type = models.CharField(max_length=255, default=None)
    created_at = models.DateTimeField(default=None)
    updated_at = models.DateTimeField(default=None)
    
    def __unicode__(self):
        return self.asset_id
    
    class Meta:
        # define the custom database table name, different from the default name.
        db_table = "assets_creators"