#!/usr/bin/env python

'''****************************************************************************
*   Program - A class for running sparql queries.
*   Author - Huiming Ding: huiming@mit.edu

*  This program is a trial software: you can redistribute it and/or modify
*  it under the terms of the MIT License. 
*  Due to the nature of the on-going research, the redistribution is limited to authorized users 
*  in the current phase of the study. 
 
* The above copyright notice and this permission notice shall be included in all
* copies or substantial portions of the Software.

* THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
* IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
* FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
* AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
* LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
* OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
* SOFTWARE.

****************************************************************************'''

'''****************************************************************************

*   To run the program
*   For example - python 

*   Logic - 

****************************************************************************'''
import rdflib
#from myFAIR import settings

from dmac import settings

class Sparql(object):
    ''' The class is used to run Seek operations, regardless the underlayer query approach. 
    
    Typical usage of the class
    
        sparql = Sparql()
    '''
    def __init__(self):
        ''' We do not need the username and password for accessing the Sparql API, which is
            defined in settings.py.
        '''
        self.__store = self.__open_sparql_store()
            
    def __open_sparql_store(self):
        """Opening the SEEK SPARQL end-point.

        Returns:
            The SPARQL end-point.
        """
        g = rdflib.ConjunctiveGraph('SPARQLStore')
        g.open(settings.VIRTUOSO_URL)
        return g
    
    def query(self, sparql_query):
        ''' Run sparql query and return results in list.
        '''
        return self.__store.query(sparql_query)
    
    def runQuery(self, sparql_query, stripStr=''):
        """Run SPARQL query.
    
        Arguments:
            sparql_query: A SPARQL query,
            stripStr,a string used for strip away from the result set.

        Returns:
            Dictionary with results, such as
                {'2': rdflib.term.Literal('Breast Cancer'), '1': rdflib.term.Literal('Default Project')}
            
        Example:
            sparql_query:
                "prefix jerm: <http://jermontology.org/ontology/JERMOntology#>select distinct ?projectid ?projects where {?projectid jerm:title ?projects;rdf:type jerm:Project}"
            rows = g.query(sparql_query):
                (rdflib.term.URIRef('http://localhost:3000/projects/2'), rdflib.term.Literal('Breast Cancer'))
                (rdflib.term.URIRef('http://localhost:3000/projects/1'), rdflib.term.Literal('Default Project'))
                (rdflib.term.URIRef('http://dmac.mit.edu:3000/projects/1'), rdflib.term.Literal('Default Project'))
                (rdflib.term.URIRef('http://dmac.mit.edu:3000/projects/2'), rdflib.term.Literal('Breast Cancer'))
            resultDic:
                {'2': rdflib.term.Literal('Breast Cancer'), '1': rdflib.term.Literal('Default Project')}
        """
        resultDic = {}
        for row in self.query(sparql_query):
            resultDic[row[0].strip(stripStr).split("/")[-1]] = row[1]
            
        #print (sparql_query)
        #print(resultDic)
        return resultDic

        
    def getProjects(self):
        """Run SPARQL query to find all available project on the SEEK server.

        Returns:
            Dictionary with all project in SEEK.
            
        Example:
            {'2': rdflib.term.Literal('Breast Cancer'), '1': rdflib.term.Literal('Default Project')}
        """
        p_sparql_query = (
            "prefix jerm: <http://jermontology.org/ontology/JERMOntology#>" +
            "select distinct ?projectid ?projects where {" +
            "?projectid jerm:title ?projects;" +
            "rdf:type jerm:Project" +
            "}"
        )
        return self.runQuery(p_sparql_query)    
        
    def getInvestigations(self, selected_project_name):
        """Run SPARQL query to find all investigations on the SEEK server
        based on a project name.
    
        Arguments:
            selected_project_name: The name of the selected project 
            in the upload form.

        Returns:
            Dictionary with all investigations belonging to the selected project.
            
        Example:    
            return {'1': rdflib.term.Literal('investigation2'), '2': rdflib.term.Literal('investigation1')}
            
        Modified from getSPARQLinvestigations()
        """
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
        """Run SPARQL query to find all studies on the SEEK server 
        based on an investigation name.
    
        Arguments:
            selected_investigation_name: The name of the selected investigation 
            in the upload form.

        Returns:
            Dictionary with all studies belonging to the selected investigation.
        """
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
        """Run SPARQL query to find all assays on the SEEK server 
        based on a study name.
    
        Arguments:
            selected_study_name: The name of the selected study 
            in the upload form.
    
        Returns:
            Dictionary with all assays belonging to the selected study.
        """
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
        """Run SPARQL query to find all samples on the SEEK server 
        that are linked to an assay.
    
        Arguments:
            selected_assay_name: The name of the selected assay 
            in the upload form.

        Returns:
            Dictionary with all samples linked to the selected assay.
            
        Example:
            s_sparql_query:
                prefix jerm: <http://jermontology.org/ontology/JERMOntology#>select distinct ?sampleid ?sample where {?a jerm:title ?assay .FILTER regex(?assay, 'library prep assay', 'i')?a jerm:hasPart ?sampleid.FILTER regex(?sampleid, 'samples', 'i')?sampleid jerm:title ?sample}
            returns:
                {}
        """
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
        #print(s_sparql_query)
        return self.runQuery(s_sparql_query, "rdflib.term.URIRef")    
        
        