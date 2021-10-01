#!/usr/bin/env python

'''****************************************************************************
*   Program - A class for running Galaxy API queries.
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
#from bioblend.galaxy import GalaxyInstance
#from bioblend.galaxy.client import ConnectionError
from datetime import datetime, timedelta

import subprocess
import json
from subprocess import call

class GalaxyAPI(object):
    ''' The class is used to run Seek operations, regardless the underlayer query approach. 
    
    Typical usage of the class
    
        galaxyapi = GalaxyAPI()
    '''
    def __init__(self, url, email, password):
        ''' We do need the username and password for accessing the Seek API. 
        '''
        self.__url = url
        self.__email = email
        self.__password = password
        print(url, email, password)
        self.__gi = GalaxyInstance(
            url=url,
            email=email,
            password=password)
            

    def get_galaxy_info(self):
        """Gets the Galaxy information from the logged in user.

        Arguments:
            url : The Galaxy server URL.
            email: The users email address for the Galaxy server.
            password: The Galaxy server password.

        Returns:
            The Galaxy username of the logged in user. Available Galaxy 
            workflows. A List of Galaxy histories from the user's account and 
            a list of available dbkeys.
        """
        gusername = ""
        user = self.__gi.users.get_current_user()
        print("user:", user)
        gusername = user['username']
        workflows = self.__gi.workflows.get_workflows
        history = self.__gi.histories.get_histories()
        hist = json.dumps(history)
        his = json.loads(hist)
        genomes = self.__gi.genomes.get_genomes()
        dbkeys = []
        ftp = self.__gi.config.get_config()["ftp_upload_site"]
        if "bioinf-galaxian" in ftp:
            ftp = "ftp://bioinf-galaxian.erasmusmc.nl:23"
        for gene in genomes:
            for g in gene:
                if "(" not in g:
                    dbkeys.append(g)
        return gusername, workflows, his, dbkeys


    def get_history_id(self):
        """Get the current Galaxy history ID

        Arguments:
            gi: Galaxy instance.

        Returns:
            The current Galaxy history ID from the logged in user.
        """
        # gi = GalaxyInstance(url=server, email=galaxyemail, password=galaxypass)
        cur_hist = self.__gi.histories.get_current_history()
        current = json.dumps(cur_hist)
        current_hist = json.loads(current)
        history_id = current_hist['id']
        return history_id


    def get_input_data(self):
        """Get input data based on the selected history.
        Find the number of uploaded files and return the id's of the files.

        Arguments:
            gi: Galaxy instance.

        Returns:
            A list of input files from the Galaxy history and 
            the amount of input datasets in the history.
        """
        # gi = GalaxyInstance(url=server, email=galaxyemail, password=galaxypass)
        history_id = self.get_history_id()
        hist_contents = self.__gi.histories.show_history(history_id, contents=True)
        inputs = {}
        datacount = 0
        datasets = [dataset for dataset in hist_contents if not dataset['deleted']]
        for dataset in datasets:
            inputs[dataset['name']] = dataset['id']
            datacount += 1
        return inputs, datacount
    
    def create_new_hist(self, workflowid, files, new_hist):
        """Create a new history if there are any files selected.

        Arguments:
            gi: The Galaxy Instance.
            galaxyemail: The Galaxy email address.
            galaxypass: The Galaxy password.
            server: The Galaxy server URL.
            workflowid: The Galaxy workflow ID.
            files: A List of files to upload.
            new_hist: The new history name.

        Returns:
            A new Galaxy history ID.
        """
        date = format(datetime.now() + timedelta(hours=2))
        if workflowid != "0":
            if len(list(filter(None, files))) >= 0:
                workflow = self.__gi.workflows.show_workflow(workflowid)
                if new_hist is None or new_hist == "":
                    new_hist_name = (workflow['name'] + "_" + date)
                else:
                    new_hist_name = new_hist
                self.__gi.histories.create_history(name=new_hist_name)
                history_id = self.get_history_id()
            else:
                pass
        else:
            if len(list(filter(None, files))) >= 0:
                if new_hist is None or new_hist == "":
                    new_hist_name = ("Use_Galaxy_" + date)
                else:
                    new_hist_name = new_hist
                self.__gi.histories.create_history(name=new_hist_name)
                history_id = self.get_history_id()
            else:
                pass
        return history_id
    
    def get_output(self):
        """Get all inputs and outputs from the Galaxy workflow.
        This information will be used to store the files in the storage location.

        Arguments:
            galaxyemail: The Galaxy email address.
            galaxypass: The Galaxy password.
            server: The Galaxy server URL.

        Returns:
            Lists with Galaxy inputfile URLs, inputfile names, 
            outputfile URLs and outputfile names.
        """
        historyid = self.get_history_id()
        inputs = []
        input_ids = []
        outputs = []
        time.sleep(30)
        hist = self.__gi.histories.show_history(historyid)
        state = hist['state_ids']
        dump = json.dumps(state)
        status = json.loads(dump)
        # Stop process after workflow is done
        while (
            status['running'] or
            status['queued'] or
            status['new'] or
            status['upload']
        ):
            time.sleep(90)
            hist = self.__gi.histories.show_history(historyid)
            state = hist['state_ids']
            dump = json.dumps(state)
            status = json.loads(dump)
            if (
                    not status['running'] and
                    not status['queued'] and
                    not status['new'] and
                    not status['upload']
            ):
                break
        files = status['ok']
        for o in files:
            oug = self.__gi.datasets.show_dataset(o, deleted=False, hda_ldda='hda')
            if "input_" in oug['name']:
                inputs.append(oug['id'])
            else:
                outputs.append(oug)
        for i in inputs:
            iug = self.__gi.datasets.show_dataset(i, deleted=False, hda_ldda='hda')
            input_ids.append(iug)
        in_url = []
        in_name = []
        out_url = []
        out_name = []
        for input_id in input_ids:
            in_name.append(input_id["name"])
            in_url.append(input_id["download_url"])
        for out in outputs:
            if out['visible']:
                out_name.append(out["name"])
                out_url.append(out["download_url"])
        return in_url, in_name, out_url, out_name
    
    def create_history(self, resultid):
        ''' used before calling rerun_analysis()
        '''
        ftp = self.__gi.config.get_config()["ftp_upload_site"]
        if "bioinf-galaxian" in ftp:
            ftp = "ftp://bioinf-galaxian.erasmusmc.nl:23"
        self.__gi.histories.create_history(name=resultid)
        return ftp
    
    def rerun_owncloud_workflow(self, gafile, history_id):
        """Start a Galaxy workflow when using owncloud/nextcloud as a 
        storage location when rerunning a previous analysis.

        Arguments:
            gi: Galaxy Instance of the current logged in user.
            gafile: The Galaxy workflow file to import into the Galaxy server

        Raises:
            IndexError: An error occurred searching for the input names
            in the Galaxy workflow file.
        """
        self.__gi.workflows.import_workflow_from_local_path(gafile.name)
        workflows = self.__gi.workflows.get_workflows(name="TEMP_WORKFLOW")
        for workflow in workflows:
            newworkflowid = workflow["id"]
        datamap = dict()
        mydict = {}
        jsonwf = self.__gi.workflows.export_workflow_json(newworkflowid)
        for i in range(len(jsonwf["steps"])):
            if jsonwf["steps"][str(i)]["name"] == "Input dataset":
                try:
                    label = jsonwf["steps"][str(i)]["inputs"][0]["name"]
                except IndexError:
                    label = jsonwf["steps"][str(i)]["label"]
                mydict[label] = self.__gi.workflows.get_workflow_inputs(
                    newworkflowid, label=label)[0]
        for k, v in mydict.items():
            datasets = self.get_input_data()[0]
            for dname, did in datasets.items():
                if k in dname:
                    datamap[v] = {'src': "hda", 'id': did}
        self.__gi.workflows.run_workflow(
            newworkflowid,
            datamap,
            history_id=history_id
        )
        self.__gi.workflows.delete_workflow(newworkflowid)
        
    
    
    def rerun_seek_workflow(self, username, workflowid, history_id, gacont):
        """Start the Galaxy workflow after uploading the data files to the 
        Galaxy server. 

        Arguments:
            gi: Galaxy instance of the logged in user.
            username: SEEK username.
            workflowid: ID of the workflow used in this analysis.
            history_id: ID of the new Galaxy history.
            gacont: JSON content of the workflow used in the analysis.

        Raises:
            IndexError: An error occurred when searching ffor the input name labels
            in the Galaxy workflow file.
        """
        with open(username + "/workflow.ga", 'w') as gafile:
            json_ga = json.loads(gacont)
            for i, dummyj in json_ga.items():
                if i == 'name':
                    json_ga[i] = 'TEMP_WORKFLOW'
            json.dump(json_ga, gafile, indent=2)
        if workflowid != "0":
            self.__gi.workflows.import_workflow_from_local_path(gafile.name)
            workflows = self.__gi.workflows.get_workflows(name="TEMP_WORKFLOW")
            for workflow in workflows:
                newworkflowid = workflow["id"]
            datamap = dict()
            mydict = {}
            jsonwf = self.__gi.workflows.export_workflow_json(newworkflowid)
            for i in range(len(jsonwf["steps"])):
                if jsonwf["steps"][str(i)]["name"] == "Input dataset":
                    try:
                        label = jsonwf["steps"][str(i)]["inputs"][0]["name"]
                    except IndexError:
                        label = jsonwf["steps"][str(i)]["label"]
                    mydict[label] = self.__gi.workflows.get_workflow_inputs(
                        newworkflowid, label=label)[0]
            for k, v in mydict.items():
                datasets = self.get_input_data()[0]
                for dname, did in datasets.items():
                    if k in dname:
                        datamap[v] = {'src': "hda", 'id': did}
            self.__gi.workflows.run_workflow(
                newworkflowid, datamap, history_id=history_id)
            self.__gi.workflows.delete_workflow(newworkflowid)
            