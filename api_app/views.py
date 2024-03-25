# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .serializers import SamplesSerializer, DatafilesSerializer
from seek.models import Samples, Data_files
from seek.dbtable_sample import DBtable_sample
from seek.dbtable_data_files import DBtable_data_files
from seek.seekdb import SeekDB

from rest_framework import mixins
from rest_framework import generics
from rest_framework import filters
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User

def get_user_by_token(request, useToken=True, whetherFullInfo=False):
    if useToken:
        user_id = Token.objects.get(key=request.auth.key).user_id
        user = User.objects.get(pk=user_id)
        seekdb = SeekDB(None, user.username, user.password)
        user_seek = seekdb.getSeekLogin(None, True)
        user_seek['username'] = user.username
        user_seek['password'] = user.password
        user_seek['user_id'] = user_id
        
        if whetherFullInfo:
            userInfo, status, msg = seekdb.getUserInfo(user_id)
            user_seek['userInfo'] = userInfo
        
    else:
        user = request.user
        context = {"user": user}
        seekdb = SeekDB(None, None, None)
        user_seek = seekdb.getSeekLogin(request, True)
        
    return user_seek
 

class SamplesViews(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    def get(self, request, id=None):
        if id:
            try:
                item = Samples.objects.get(id=id)
            except Samples.DoesNotExist:
                raise Http404

            serializer = SamplesSerializer(item)
            return Response({"status": "success", "sample_id": id, "data": serializer.data}, status=status.HTTP_200_OK)

        items = Samples.objects.all()
        serializer = SamplesSerializer(items, many=True)
        return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)
    
    def post(self, request, format=None):
        import json
        user_seek = get_user_by_token(request)
        msg = ''
        uid = ''
        if "file" in request.data:
            status0 = 'file in request'
            dataIn = request.data
            file_obj = request.data["file"]
            from pyexcel_xlsx import get_data
            data = get_data(file_obj)
            
            dbsample = DBtable_sample()
            msg, status0 = dbsample.apiUploadSamples(data, user_seek)
            
        elif request.data is not None:
            status0 = 'json dictionary in request'
            data = request.data
            dbsample = DBtable_sample()
            msg, status0, uid = dbsample.apiUploadSamples(data, user_seek)
            
        else:
            data = {}
            status0 = 'file not in request'
        
        data = json.dumps(data, default=str)
        return Response({"status":status0, "msg":msg, "UID":uid, "data":data}, status=status.HTTP_200_OK)
    
class SamplesListViews1(APIView):
    def get(self, request, format=None):
        samples = Samples.objects.all()
        serializer = SamplesSerializer(samples, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = SamplesSerializer(data=request.DATA)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class SamplesDetailViews1(APIView):
    def get_object(self, id):
        try:
            return Samples.objects.get(id=id)
        except Samples.DoesNotExist:
            raise Http404

    def get(self, request, id, format=None):
        Samples = self.get_object(id)
        serializer = SamplesSerializer(Samples)
        return Response(serializer.data)

    def put(self, request, id, format=None):
        Samples = self.get_object(id)
        serializer = SamplesSerializer(Samples, data=request.DATA)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id, format=None):
        Samples = self.get_object(id)
        Samples.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)       

class SamplesListViews2(mixins.ListModelMixin,
                  mixins.CreateModelMixin,
                  generics.GenericAPIView):

    queryset = Samples.objects.all()
    serializer_class = SamplesSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)
        
class SamplesDetailViews2(mixins.RetrieveModelMixin,
                    mixins.UpdateModelMixin,
                    mixins.DestroyModelMixin,
                    generics.GenericAPIView):

    queryset = Samples.objects.all()
    serializer_class = SamplesSerializer
           
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)
        
class SamplesListViews(generics.ListCreateAPIView):
    search_fields = ['json_metadata']
    filter_backends = (filters.SearchFilter,)
    
    queryset = Samples.objects.all()
    serializer_class = SamplesSerializer

class SamplesDetailViews(generics.RetrieveUpdateDestroyAPIView):
    queryset = Samples.objects.all()
    serializer_class = SamplesSerializer
    

class DatafilesListViews(generics.ListCreateAPIView):
    search_fields = ['title']
    filter_backends = (filters.SearchFilter,)
    
    queryset = Data_files.objects.all()
    serializer_class = DatafilesSerializer

class DatafilesDetailViews(generics.RetrieveUpdateDestroyAPIView):
    queryset = Data_files.objects.all()
    serializer_class = DatafilesSerializer
    
    
    
class DatafileViews(APIView):
    queryset = Data_files.objects.all()
    serializer_class = DatafilesSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request, format=None):
        user_seek = get_user_by_token(request)
        import json
        msg = ''
        if "file" in request.data:
            msg = 'file in request'
            status0 = 1
            file_obj = request.data["file"]
            msg = 'file received'
            data = {}
            
            dbsample = DBtable_sample()
            user_id = user_seek['user_id']
            filetype = "DATAFILE"
            sampleRecord, msg = dbsample.searchFileInSample(user_id, file_obj.name, filetype)
            if sampleRecord is None or sampleRecord['id']<=0:
                report = {}
                report['msg'] = msg
                report['status'] = 0
                status0 = 0
            else:
                sample_uid = sampleRecord['uuid']
                sample_info = dbsample.getSampleUIDInfo(sample_uid)
                dbdf = DBtable_data_files("DEFAULT")
                report = dbdf.apiUploadFile(user_seek, file_obj, sample_info)
                data = report
                status0 = 1
            
        elif request.data is not None:
            msg = 'json dictionary in request'
            status0 = 0
            data = request.data
        else:
            data = {}
            status0 = 'file not in request'
        data = json.dumps(data, default=str)
        return Response({"status":status0, "msg":msg, "data":data}, status=status.HTTP_200_OK)

    