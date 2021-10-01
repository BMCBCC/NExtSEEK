from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^remote/', views.remote, name='remote'),
    
    #url(r'^samples/', views.samples, name='samples'),
    
    url(r'^samples/upload/', views.sampleUpload, name='sampleUpload'),
    url(r'^samples/query/', views.sampleQuery, name='sampleQuery'),
    url(r'^samples/search/', views.sampleSearch, name='sampleSearch'),
    url(r'^samples/searching/', views.sampleSearching, name='sampleSearching'),
    url(r'^retrieve/samples/', views.retrieveSamples, name='retrieveSamples'),
    
    url(r'^samples/attributes/', views.sampleAttributes, name='sampleAttributes'),
    url(r'^samples/retrieveType/', views.getSampleType, name='getSampleType'),
    
    # retrieve same tree either by sample id or sample uid
    url(r'^sample/id=(?P<id>\d+)/$', views.sample, name='sample'),
    url(r'^sampletree/uid=(?P<uid>[\w.-]{0,256})/$', views.sampleTree, name='sampleTree'),
    
    url(r'^samples/download/', views.sampleDownload, name='sampleDownload'),
    url(r'^samples/export/', views.sampleExport, name='sampleExport'),
    url(r'^samples/delete/', views.sampleDelete, name='sampleDelete'),
    url(r'^samples/publish/', views.samplePublish, name='samplePublish'),
    
    url(r'^samplefind/', views.sampleFindAjax, name='sampleFindAjax'),
    
    #url(r'^samples/publishlist/slist=(?P<sampleids>\w+)/$',views.publish_samples, name='publish_samples'),
    #url(r'^samples/publishlist/slist=(?P<sampleids>[\w-]+)/$',views.publish_samples, name='publish_samples'),
    url(r'^samples/publishlist/(?P<sampleids>\d+(,\d+)*)/$',views.publish_samples, name='publish_samples'),
    
    url(r'^document/id=(?P<id>\d+)/$', views.document, name='document'),

    # equal to Seek("/sample_types/29/")
    url(r'^attributes/id=(?P<id>\d+)/$', views.getAttributes, name='getAttributes'),
    url(r'^attribute/save/', views.sampleAttributeSave, name='sampleAttributeSave'), 
    url(r'^attribute/delete/', views.sampleAttributeDelete, name='sampleAttributeDelete'),
    url(r'^operators/$', views.getOperators, name='getOperators'),
    
    url(r'^sample_types/id=(?P<id>\d+)/$', views.sample_type, name='sample_type'),
    url(r'^sampleupload/', views.sampleUploadAjax, name='sampleUploadAjax'),
    
    #url(r'^url=(?P<url>\d+)/$', views.seek, name='seek'),
    url(r'^url/(?P<url>[\w-]+)/$', views.seek, name='seek'),
    
    # get to the upload page of data files to server and to Seek
    url(r'^data/upload/', views.datafileUpload, name='datafileUpload'),
    # perform the batch upload of files
    url(r'^datafiles/batchupload/', views.filesBatchUpload, name='filesBatchUpload'),
    # perform the batch upload of files into Seek
    url(r'^datafiles/uploadtoseek/', views.uploadToSeek, name='uploadtoseek'),
    # get UIDs for the batch upload of files
    url(r'^datafiles/getuids/', views.filesGetUIDs, name='filesGetUIDs'),

    # get to the query page of data files
    url(r'^datafile/query/', views.datafileQuery, name='datafileQuery'),
    url(r'^datafiles/publish/(?P<dfids>\d+(,\d+)*)/$',views.publish_datafiles, name='publish_datafiles'),

    url(r'^datafile/uid=(?P<uid>[\w.-]{0,256})/$', views.datafileDownload, name='datafileDownload'),

    #url(r'^sop/uid=(?P<uid>[\w-]+)/$', views.sopDownload, name='sopDownload'),
    url(r'^sop/uid=(?P<uid>[\w.-]{0,256})/$', views.sopDownload, name='sopDownload'),
    url(r'^sops/publish/(?P<sopids>\d+(,\d+)*)/$',views.publish_sops, name='publish_sops'),
    
    url(r'^sop/query/', views.sopQuery, name='sopQuery'),
    url(r'^retrieve/datafiles/', views.retrieveDatafiles, name='retrieveDatafiles'),
    url(r'^retrieve/sops/', views.retrieveSops, name='retrieveSops'),
    url(r'^batchdownload/datafiles/', views.batchdownloadDatafiles, name='batchdownloadDatafiles'),
    url(r'^batchdownload/sops/', views.batchdownloadSops, name='batchdownloadSops'),
    url(r'^batchpublish/datafiles/', views.batchpublishDatafiles, name='batchpublishDatafiles'),
    url(r'^batchpublish/sops/', views.batchpublishSops, name='batchpublishSops'),
    
    url(r'^dropbox/path/', views.getDropboxPath, name='getDropboxPath'),
    url(r'^dropbox/status/', views.getDropboxStatus, name='getDropboxStatus'),
    
    # publish page, 
    url(r'^publish/', views.publish, name='publish'),
    
    # given an investigation id, retrieve the list of studies in the investigation, called in templates/pages/pulish_search.embed.html
    url(r'^investigations/id=(?P<id>\d+)/$', views.getStudiesOptions, name='getStudiesOptions'),
    
    # given a study id, retrieve a list of assays in the study, called in templates/pages/pulish_search.embed.html
    url(r'^studies/id=(?P<id>\d+)/$', views.getAssaysOptions, name='getAssaysOptions'),

    # called in templates/pages/pulish_search.embed.html
    url(r'^searchAssets/', views.publishSearching, name='publishSearching'),
    
    # called in templates/pages/pulish_stable.embed.html
    url(r'^publishAssets/', views.publishAssets, name='publishAssets'),
    
]
