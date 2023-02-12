#!/usr/bin/env python
import rdflib
from dmac import settings

class Sparql(object):
    def __init__(self):
        self.__store = self.__open_sparql_store()
            
    def __open_sparql_store(self):
        g = rdflib.ConjunctiveGraph('SPARQLStore')
        g.open(settings.VIRTUOSO_URL)
        return g
    
    def query(self, sparql_query):
        return self.__store.query(sparql_query)
    
    def runQuery(self, sparql_query, stripStr=''):
        resultDic = {}
        for row in self.query(sparql_query):
            resultDic[row[0].strip(stripStr).split("/")[-1]] = row[1]
            
        return resultDic

        
    def getProjects(self):
        p_sparql_query = (
            "prefix jerm: <http://jermontology.org/ontology/JERMOntology#>" +
            "select distinct ?projectid ?projects where {" +
            "?projectid jerm:title ?projects;" +
            "rdf:type jerm:Project" +
            "}"
        )
        return self.runQuery(p_sparql_query)    
        
    def getInvestigations(self, selected_project_name):
        i_sparql_query = (
            "prefix jerm: <http://jermontology.org/ontology/JERMOntology#>" +
            "select distinct ?investigationid ?investigation where {" +
            "?p jerm:title ?project ." +
            "FILTER regex(?project, \'" + selected_project_name + "\', 'i')" +
            "?p jerm:hasItem ?investigationid." +
            "FILTER regex(?investigationid, 'investigations', 'i')" +
            "?investigationid jerm:title ?investigation" +
            "}"
        )
        return self.runQuery(i_sparql_query, "rdflib.term.URIRef")
        
    def getStudies(self, selected_investigation_name):
        s_sparql_query = (
            "prefix jerm: <http://jermontology.org/ontology/JERMOntology#>" +
            "select distinct ?studyid ?study where {" +
            "?i jerm:title ?investigation ." +
            "FILTER regex(?investigation, \'" + selected_investigation_name + "\', 'i')" +
            "?i jerm:hasPart ?studyid." +
            "FILTER regex(?studyid, 'studies', 'i')" +
            "?studyid jerm:title ?study" +
            "}"
        )
        return self.runQuery(s_sparql_query, "rdflib.term.URIRef")        

    def getAssays(self, selected_study_name):
        s_sparql_query = (
            "prefix jerm: <http://jermontology.org/ontology/JERMOntology#>" +
            "select distinct ?assayid ?assay where {" +
            "?s jerm:title ?study ." +
            "FILTER regex(?study, \'" + selected_study_name + "\', 'i')" +
            "?s jerm:hasPart ?assayid." +
            "FILTER regex(?assayid, 'assays', 'i')" +
            "FILTER (!regex(?assay, '__result__', 'i'))" +
            "?assayid jerm:title ?assay" +
            "}"
        )
        return self.runQuery(s_sparql_query, "rdflib.term.URIRef")
        
    def getSamples(self, selected_assay_name):
        s_sparql_query = (
            "prefix jerm: <http://jermontology.org/ontology/JERMOntology#>" +
            "select distinct ?sampleid ?sample where {" +
            "?a jerm:title ?assay ." +
            "FILTER regex(?assay, \'" + selected_assay_name + "\', 'i')" +
            "?a jerm:hasPart ?sampleid." +
            "FILTER regex(?sampleid, 'samples', 'i')" +
            "?sampleid jerm:title ?sample" +
            "}"
        )
        return self.runQuery(s_sparql_query, "rdflib.term.URIRef")    
        
        